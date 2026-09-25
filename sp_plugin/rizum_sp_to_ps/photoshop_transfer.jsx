(function () {
    __RIZUM_JSON_RUNTIME__
    var requestPath = __RIZUM_TRANSFER_REQUEST_PATH__;
    var resultPath = File(requestPath).parent.fsName + "/photoshop_transfer_result.json";
    var progressPath = File(requestPath).parent.fsName + "/photoshop_transfer_progress.json";
    var result = { success: false, inserted: [], errors: [], warnings: [], saved: false };
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
            if (mapped.insertion !== "after" && mapped.insertion !== "inside") {
                throw new Error("Unsupported insertion: " + mapped.insertion);
            }
            if (mapped.insertion === "inside" && destination.typename !== "LayerSet") {
                throw new Error("Mapped inside target is no longer a Photoshop group");
            }
            requireAssets(mapped);
            targets.push(destination);
        }
        publishProgress("transferring_layers", 0, request.layers.length);

        for (var index = 0; index < request.layers.length; index += 1) {
            var item = request.layers[index];
            try {
                var target = targets[index];
                var placed = createLayer(document, document, item);
                moveMappedLayer(placed, target, item);
                // A mapped Painter folder stays a folder: its layers are placed
                // only after the folder sits at its destination.
                placeChildren(document, placed, item.children);
                if (item.mask_png) {
                    applyMask(document, placed, item.mask_png);
                }
                result.inserted.push(placed.name);
            } catch (itemError) {
                result.errors.push({
                    name: String(item.name || "Painter Layer"),
                    message: errorMessage(itemError)
                });
            }
            publishProgress("transferring_layers", index + 1, request.layers.length);
        }

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
        } finally {
            var remaining = findLayerById(targetDocument, placeholderId);
            if (remaining && (!placed || Number(placed.id) !== placeholderId)) remaining.remove();
        }
        return placed;
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

    function createLayer(targetDocument, parent, item) {
        var layer = isGroup(item) ? parent.layerSets.add() : placePngLayer(item.png, targetDocument);
        layer.name = String(item.name || "Painter Layer");
        layer.visible = item.visible !== false;
        layer.opacity = opacityPercent(item.opacity);
        var blendMode = photoshopBlendMode(item.blend_mode, isGroup(item));
        if (blendMode !== null) {
            layer.blendMode = blendMode;
        }
        if (!isGroup(item)) {
            layer.rasterize(RasterizeType.ENTIRELAYER);
        }
        return layer;
    }

    function placeChildren(targetDocument, group, children) {
        // Children arrive top to bottom; appending each keeps that order.
        for (var index = 0; index < (children || []).length; index += 1) {
            var child = children[index];
            var layer = createLayer(targetDocument, group, child);
            layer.move(group, ElementPlacement.PLACEATEND);
            placeChildren(targetDocument, layer, child.children);
            if (child.mask_png) {
                applyMask(targetDocument, layer, child.mask_png);
            }
        }
    }

    function moveMappedLayer(layer, target, item) {
        // Replay each drop exactly as the desktop preview: group drops append;
        // repeated drops on one layer insert immediately below that same layer.
        if (item.insertion === "inside") {
            layer.move(target, ElementPlacement.PLACEATEND);
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
        targetDocument.activeLayer = maskLayer;
        targetDocument.selection.selectAll();
        executeAction(charIDToTypeID("copy"), undefined, DialogModes.NO);
        maskLayer.remove();
        targetDocument.activeLayer = targetLayer;
        makeRevealAllMask();
        selectLayerMaskChannel();
        pasteMaskPixels();
        try {
            targetDocument.selection.deselect();
        } catch (ignored) {}
        selectLayer(targetLayer);
        selectCompositeChannel();
    }

    function makeRevealAllMask() {
        var descriptor = new ActionDescriptor();
        descriptor.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));
        var reference = new ActionReference();
        reference.putEnumerated(
            charIDToTypeID("Chnl"),
            charIDToTypeID("Chnl"),
            charIDToTypeID("Msk ")
        );
        descriptor.putReference(charIDToTypeID("At  "), reference);
        descriptor.putEnumerated(
            charIDToTypeID("Usng"),
            charIDToTypeID("UsrM"),
            charIDToTypeID("RvlA")
        );
        executeAction(charIDToTypeID("Mk  "), descriptor, DialogModes.NO);
    }

    function selectLayerMaskChannel() {
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putEnumerated(
            charIDToTypeID("Chnl"),
            charIDToTypeID("Chnl"),
            charIDToTypeID("Msk ")
        );
        descriptor.putReference(charIDToTypeID("null"), reference);
        executeAction(charIDToTypeID("slct"), descriptor, DialogModes.NO);
    }

    function selectCompositeChannel() {
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putEnumerated(
            charIDToTypeID("Chnl"),
            charIDToTypeID("Chnl"),
            charIDToTypeID("RGB ")
        );
        descriptor.putReference(charIDToTypeID("null"), reference);
        executeAction(charIDToTypeID("slct"), descriptor, DialogModes.NO);
    }

    function pasteMaskPixels() {
        executeAction(charIDToTypeID("past"), undefined, DialogModes.NO);
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
