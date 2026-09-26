(function () {
    __RIZUM_JSON_RUNTIME__
__RIZUM_MASK_RUNTIME__
    var requestPath = __RIZUM_TRANSFER_REQUEST_PATH__;
    var resultPath = File(requestPath).parent.fsName + "/photoshop_transfer_result.json";
    var progressPath = File(requestPath).parent.fsName + "/photoshop_transfer_progress.json";
    var result = { success: false, inserted: [], errors: [], warnings: [], saved: false };
    // Where Place put a canvas-sized image; every placed PNG moves back by it.
    var placeOffset = { x: 0, y: 0 };
    var previousDialogs = app.displayDialogs;
    var previousRulerUnits = app.preferences.rulerUnits;

    app.displayDialogs = DialogModes.NO;
    app.preferences.rulerUnits = Units.PIXELS;
    app.bringToFront();

    try {
        publishProgress("reading_request", 0, 0);
        var request = readJson(requestPath);
        validateRequest(request);
        publishProgress("opening_document", 0, request.layers.length);
        var document = resolveDocument(request.document || {});
        app.activeDocument = document;
        var targets = [];
        // Validate every destination before inserting anything. A stale mapping
        // must not leave a half-applied batch that a retry would duplicate.
        for (var targetIndex = 0; targetIndex < request.layers.length; targetIndex += 1) {
            var mapped = request.layers[targetIndex];
            var destination = findTarget(document, mapped);
            if (mapped.insertion !== "before" && mapped.insertion !== "after" && mapped.insertion !== "inside") {
                throw new Error("Unsupported insertion: " + mapped.insertion);
            }
            if (mapped.insertion === "inside" && destination.typename !== "LayerSet") {
                throw new Error("Mapped inside target is no longer a Photoshop group");
            }
            requireAssets(mapped);
            targets.push(destination);
        }
        if (request.placement_probe) {
            placeOffset = measurePlaceOffset(document, request.placement_probe);
        }
        // Progress counts every layer a folder brings, so a large folder
        // advances the bar instead of holding it on one step.
        var progress = { done: 0, total: countLayers(request.layers) };
        publishProgress("transferring_layers", 0, progress.total);

        for (var index = 0; index < request.layers.length; index += 1) {
            var item = request.layers[index];
            try {
                var target = targets[index];
                // A folder dropped inside a group is created in it: Photoshop
                // cannot move a folder into a folder.
                var parent = isGroup(item) && item.insertion === "inside" ? target : document;
                var placed = createLayer(document, parent, item, progress);
                step(item, "moving it to its mapped place", function () { moveMappedLayer(placed, target, item); });
                // A mapped Painter folder stays a folder: its layers are placed
                // only after the folder sits at its destination.
                placeChildren(document, placed, item.children, progress);
                if (item.mask_png) {
                    step(item, "applying its mask", function () { applyMask(document, placed, item.mask_png); });
                }
                result.inserted.push(placed.name);
            } catch (itemError) {
                result.errors.push({
                    name: String(item.name || "Painter Layer"),
                    message: errorMessage(itemError)
                });
            }
        }
        publishProgress("transferring_layers", progress.total, progress.total);

        if (result.errors.length === 0) {
            result.success = true;
            try {
                publishProgress("saving_document", request.layers.length, request.layers.length);
                document.fullName;
                document.save();
                result.saved = true;
            } catch (saveError) {
                result.warnings.push("Imported layers are open but the Photoshop document could not be saved: " + errorMessage(saveError));
            }
        }
    } catch (error) {
        result.errors.push({ name: requestPath, message: errorMessage(error) });
    } finally {
        app.displayDialogs = previousDialogs;
        app.preferences.rulerUnits = previousRulerUnits;
        writeJsonAtomic(resultPath, result);
    }

    function publishProgress(phase, completed, total) {
        writeJsonAtomic(progressPath, { phase: phase, completed: completed, total: total });
    }

    function validateRequest(request) {
        if (!request || request.request_type !== "painter_to_photoshop_transfer") {
            throw new Error("Expected a Painter-to-Photoshop transfer request");
        }
        if (!request.layers || request.layers.length === 0) {
            throw new Error("Transfer request contains no mapped layers");
        }
    }

    function resolveDocument(descriptor) {
        var targetId = Number(descriptor.id);
        var targetPath = String(descriptor.path || "");
        var index;

        for (index = 0; index < app.documents.length; index += 1) {
            var candidate = app.documents[index];
            // Native IDs are session-local and can be reused after Photoshop
            // restarts. A saved document's path is the authoritative identity.
            if (targetPath) {
                if (documentPath(candidate) === normalizedPath(targetPath)) return candidate;
            } else if (!isNaN(targetId) && Number(candidate.id) === targetId) {
                return candidate;
            }
        }
        if (targetPath && File(targetPath).exists) {
            return app.open(File(targetPath));
        }
        throw new Error("The Photoshop document used by Desktop Bridge is not open or available");
    }

    function documentPath(document) {
        try {
            return normalizedPath(document.fullName.fsName);
        } catch (ignored) {
            return "";
        }
    }

    function normalizedPath(path) {
        return String(path || "").replace(/\\/g, "/").toLowerCase();
    }

    function findTarget(document, mapped) {
        if (mapped.target_layer_id !== null && mapped.target_layer_id !== undefined) {
            var byId = findLayerById(document, Number(mapped.target_layer_id));
            if (!byId) {
                throw new Error("Photoshop target layer no longer exists: " + mapped.target_name);
            }
            return byId;
        }
        // PSDs without persistent layer ids are addressed by the position the
        // desktop mapper read from the saved file. The name check refuses an
        // insert when the open document no longer matches that file.
        var layer = null;
        var collection = document.layers;
        var path = mapped.target_index_path || [];
        for (var depth = 0; depth < path.length; depth += 1) {
            layer = collection && path[depth] < collection.length ? collection[path[depth]] : null;
            if (!layer) break;
            collection = layer.typename === "LayerSet" ? layer.layers : null;
        }
        if (!layer || String(layer.name) !== String(mapped.target_name)) {
            throw new Error(
                "Photoshop layers changed since Bridge read the PSD. Save it in Photoshop and reconnect: "
                + mapped.target_name
            );
        }
        return layer;
    }

    function findLayerById(parent, targetId) {
        var layers = parent.layers || [];
        for (var index = 0; index < layers.length; index += 1) {
            var layer = layers[index];
            if (Number(layer.id) === targetId) {
                return layer;
            }
            if (layer.typename === "LayerSet") {
                var child = findLayerById(layer, targetId);
                if (child) {
                    return child;
                }
            }
        }
        return null;
    }

    function placePngLayer(path, targetDocument) {
        var file = File(path);
        if (!file.exists) {
            throw new Error("PNG asset does not exist: " + path);
        }
        app.activeDocument = targetDocument;
        // Place replaces a selected empty raster layer in Photoshop. Give it an
        // owned placeholder so a user's empty layer or group child cannot vanish.
        var placeholder = targetDocument.artLayers.add();
        var placeholderId = Number(placeholder.id);
        var placed = null;
        try {
            placeEmbeddedFile(file);
            placed = targetDocument.activeLayer;
            if (!placed) throw new Error("Photoshop did not create a placed layer: " + path);
            if (placeOffset.x !== 0 || placeOffset.y !== 0) {
                placed.translate(-placeOffset.x, -placeOffset.y);
            }
        } finally {
            var remaining = findLayerById(targetDocument, placeholderId);
            if (remaining && (!placed || Number(placed.id) !== placeholderId)) remaining.remove();
        }
        return placed;
    }

    // Place centres an image in the visible part of the window, so a zoomed
    // or scrolled view moved every insert. An opaque probe the canvas's size
    // lands exactly where Place puts things; its corner is the offset.
    function measurePlaceOffset(targetDocument, probePath) {
        placeOffset = { x: 0, y: 0 };
        var probe = placePngLayer(probePath, targetDocument);
        var bounds = probe.bounds;
        var offset = { x: pixels(bounds[0]), y: pixels(bounds[1]) };
        probe.remove();
        return offset;
    }

    function pixels(value) {
        return typeof value === "number" ? value : Number(value.as("px"));
    }

    function placeEmbeddedFile(file) {
        var descriptor = new ActionDescriptor();
        descriptor.putPath(charIDToTypeID("null"), file);
        descriptor.putEnumerated(
            charIDToTypeID("FTcs"),
            charIDToTypeID("QCSt"),
            charIDToTypeID("Qcsa")
        );
        var offset = new ActionDescriptor();
        offset.putUnitDouble(charIDToTypeID("Hrzn"), charIDToTypeID("#Pxl"), 0);
        offset.putUnitDouble(charIDToTypeID("Vrtc"), charIDToTypeID("#Pxl"), 0);
        descriptor.putObject(charIDToTypeID("Ofst"), charIDToTypeID("Ofst"), offset);
        executeAction(charIDToTypeID("Plc "), descriptor, DialogModes.NO);
    }

    function isGroup(item) {
        return !!(item.children && item.children.length);
    }

    function requireAssets(item) {
        if (isGroup(item)) {
            for (var index = 0; index < item.children.length; index += 1) {
                requireAssets(item.children[index]);
            }
        } else if (!item.png || !File(item.png).exists) {
            throw new Error("Mapped PNG is missing: " + item.name);
        }
        if (item.mask_png && !File(item.mask_png).exists) {
            throw new Error("Mapped mask is missing: " + item.name);
        }
    }

    function countLayers(items) {
        var total = 0;
        for (var index = 0; index < (items || []).length; index += 1) {
            total += 1 + countLayers(items[index].children);
        }
        return total;
    }

    // Names the layer and the step in a failure, so a Photoshop error such as
    // "Set is not currently available" says which property it refused.
    function step(item, label, action) {
        try {
            return action();
        } catch (error) {
            throw new Error(String(item.name || "Painter Layer") + ": " + label + ": " + errorMessage(error));
        }
    }

    function createLayer(targetDocument, parent, item, progress) {
        var layer = step(item, "creating it", function () {
            return isGroup(item) ? parent.layerSets.add() : placePngLayer(item.png, targetDocument);
        });
        // As the PSD builder does: properties are set on the selected layer's
        // composite channel, opacity only when it differs, and a blend mode
        // Photoshop refuses (one this document's mode or depth lacks) is a
        // warning that keeps Normal instead of failing the whole folder.
        step(item, "selecting it", function () {
            selectLayer(layer);
            selectCompositeChannel();
        });
        step(item, "naming it", function () { layer.name = String(item.name || "Painter Layer"); });
        step(item, "setting its visibility", function () { layer.visible = item.visible !== false; });
        var opacity = opacityPercent(item.opacity);
        if (Math.abs(opacity - 100) > 0.0001) {
            step(item, "setting its opacity", function () { layer.opacity = opacity; });
        }
        var blendMode = photoshopBlendMode(item.blend_mode, isGroup(item));
        if (blendMode !== null && blendMode !== BlendMode.NORMAL) {
            try {
                layer.blendMode = blendMode;
            } catch (blendError) {
                result.warnings.push(
                    String(item.name || "Painter Layer") + ": Photoshop refused blend mode "
                    + String(item.blend_mode) + " here; Normal was kept."
                );
            }
        }
        if (!isGroup(item)) {
            step(item, "rasterizing it", function () { layer.rasterize(RasterizeType.ENTIRELAYER); });
        }
        progress.done += 1;
        publishProgress("transferring_layers", progress.done, progress.total);
        return layer;
    }

    function placeChildren(targetDocument, group, children, progress) {
        // Photoshop refuses to move a folder into a folder ("Illegal
        // Argument"), so, as the PSD builder does, a nested folder is created
        // inside its parent, where it opens at the top, and never moved.
        // Children arrive top to bottom and are placed bottom first, each at
        // the top of its folder, which keeps their order.
        for (var index = (children || []).length - 1; index >= 0; index -= 1) {
            var child = children[index];
            var layer = createLayer(targetDocument, group, child, progress);
            if (!isGroup(child)) {
                step(child, "moving it into its folder", function () { layer.move(group, ElementPlacement.PLACEATBEGINNING); });
            }
            placeChildren(targetDocument, layer, child.children, progress);
            if (child.mask_png) {
                step(child, "applying its mask", function () { applyMask(targetDocument, layer, child.mask_png); });
            }
        }
    }

    function moveMappedLayer(layer, target, item) {
        // Replay each drop exactly as the desktop preview: group drops append;
        // repeated drops on one layer insert right above or below that layer.
        if (item.insertion === "inside") {
            if (!isGroup(item)) {
                layer.move(target, ElementPlacement.PLACEATEND);
            } else if (target.layers.length > 1) {
                // Created at the top of the group; a move beside its last
                // layer is the one kind Photoshop allows a folder.
                layer.move(target.layers[target.layers.length - 1], ElementPlacement.PLACEAFTER);
            }
        } else if (item.insertion === "before") {
            layer.move(target, ElementPlacement.PLACEBEFORE);
        } else {
            layer.move(target, ElementPlacement.PLACEAFTER);
        }
    }

    function opacityPercent(value) {
        var opacity = Number(value);
        if (isNaN(opacity)) {
            return 100;
        }
        // The transfer contract uses percentages, including values below 1%.
        return Math.max(0, Math.min(100, opacity));
    }

    function photoshopBlendMode(value, allowPassThrough) {
        switch (String(value || "").toUpperCase()) {
        case "NORMAL": return BlendMode.NORMAL;
        case "PASSTHROUGH": return allowPassThrough ? BlendMode.PASSTHROUGH : BlendMode.NORMAL;
        case "MULTIPLY": return BlendMode.MULTIPLY;
        case "SCREEN": return BlendMode.SCREEN;
        case "OVERLAY": return BlendMode.OVERLAY;
        case "DARKEN": return BlendMode.DARKEN;
        case "LIGHTEN": return BlendMode.LIGHTEN;
        case "LINEARDODGE": return BlendMode.LINEARDODGE;
        case "LINEARBURN": return BlendMode.LINEARBURN;
        case "COLORBURN": return BlendMode.COLORBURN;
        case "COLORDODGE": return BlendMode.COLORDODGE;
        case "SOFTLIGHT": return BlendMode.SOFTLIGHT;
        case "HARDLIGHT": return BlendMode.HARDLIGHT;
        case "VIVIDLIGHT": return BlendMode.VIVIDLIGHT;
        case "LINEARLIGHT": return BlendMode.LINEARLIGHT;
        case "PINLIGHT": return BlendMode.PINLIGHT;
        case "DIFFERENCE": return BlendMode.DIFFERENCE;
        case "EXCLUSION": return BlendMode.EXCLUSION;
        case "SUBTRACT": return BlendMode.SUBTRACT;
        case "DIVIDE": return BlendMode.DIVIDE;
        case "HUE": return BlendMode.HUE;
        case "SATURATION": return BlendMode.SATURATION;
        case "COLOR": return BlendMode.COLORBLEND;
        case "LUMINOSITY": return BlendMode.LUMINOSITY;
        default: return null;
        }
    }

    function applyMask(targetDocument, targetLayer, path) {
        var maskLayer = placePngLayer(path, targetDocument);
        maskLayer.rasterize(RasterizeType.ENTIRELAYER);
        pasteLayerAsMask(targetDocument, targetLayer, maskLayer);
        selectLayer(targetLayer);
        selectCompositeChannel();
    }





    function selectLayer(layer) {
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putIdentifier(charIDToTypeID("Lyr "), Number(layer.id));
        descriptor.putReference(charIDToTypeID("null"), reference);
        descriptor.putBoolean(charIDToTypeID("MkVs"), false);
        executeAction(charIDToTypeID("slct"), descriptor, DialogModes.NO);
    }

    function readJson(path) {
        var file = File(path);
        file.encoding = "UTF8";
        if (!file.exists || !file.open("r")) {
            throw new Error("Could not open JSON file: " + path);
        }
        var text = file.read();
        file.close();
        return JSON.parse(text);
    }

    function writeJsonAtomic(path, state) {
        var target = File(path);
        var temporary = File(path + ".tmp");
        temporary.encoding = "UTF8";
        if (!temporary.open("w")) {
            throw new Error("Could not write Photoshop receipt: " + path);
        }
        temporary.write(JSON.stringify(state, null, 2));
        temporary.close();
        if (target.exists && !target.remove()) throw new Error("Could not replace receipt: " + path);
        if (!temporary.rename(target.name)) throw new Error("Could not publish receipt: " + path);
    }

    function errorMessage(error) {
        if (!error) {
            return "Unknown error";
        }
        return error.message ? String(error.message) : String(error);
    }
}());
