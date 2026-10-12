(function () {
    __RIZUM_JSON_RUNTIME__
__RIZUM_MASK_RUNTIME__
__RIZUM_TARGET_RUNTIME__
    var requestPath = __RIZUM_TRANSFER_REQUEST_PATH__;
    var resultPath = File(requestPath).parent.fsName + "/photoshop_transfer_result.json";
    var progressPath = File(requestPath).parent.fsName + "/photoshop_transfer_progress.json";
    var result = { success: false, inserted: [], replaced: [], errors: [], warnings: [], saved: false };
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
        var folded = foldedFolders();
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
                var placed = createLayer(document, document, item, progress);
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

        // The user switched these rows to replace the layer they landed
        // beside. It goes only when every insert succeeded, so a failed
        // Apply never costs a layer, and once per target however many rows
        // replace it.
        if (result.errors.length === 0) {
            var removed = {};
            for (var replaceIndex = 0; replaceIndex < request.layers.length; replaceIndex += 1) {
                var replaced = targets[replaceIndex];
                if (request.layers[replaceIndex].replace !== true || removed[Number(replaced.id)]) continue;
                removed[Number(replaced.id)] = true;
                var replacedName = String(replaced.name);
                try {
                    replaced.remove();
                    result.replaced.push(replacedName);
                } catch (removeError) {
                    result.warnings.push(replacedName + ": Photoshop could not delete the replaced layer: " + errorMessage(removeError));
                }
            }
        }

        foldAgain(folded);

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

    // Selecting a layer makes Photoshop open every folder above it, and the
    // mask steps cannot work without selecting, so folders the user keeps
    // folded came back open after an Apply. They are recorded before the
    // first insert and folded again after the last, before the save that
    // stores the state; a folder this Apply added stays as Photoshop opens it.
    function foldedFolders() {
        var folded = [];
        try {
            var count = new ActionReference();
            count.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("numberOfLayers"));
            count.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
            var total = executeActionGet(count).getInteger(stringIDToTypeID("numberOfLayers"));
            for (var index = 1; index <= total; index += 1) {
                var reference = new ActionReference();
                reference.putIndex(charIDToTypeID("Lyr "), index);
                var layer = executeActionGet(reference);
                if (isFoldedFolder(layer)) folded.push(layer.getInteger(stringIDToTypeID("layerID")));
            }
        } catch (ignored) {
            // A Photoshop that cannot report the state keeps its folders as they end up.
            return [];
        }
        return folded;
    }

    function isFoldedFolder(layer) {
        var expanded = stringIDToTypeID("layerSectionExpanded");
        return typeIDToStringID(layer.getEnumerationValue(stringIDToTypeID("layerSection"))) === "layerSectionStart"
            && layer.hasKey(expanded) && !layer.getBoolean(expanded);
    }

    function foldAgain(layerIds) {
        for (var index = 0; index < layerIds.length; index += 1) {
            try {
                var reference = new ActionReference();
                reference.putIdentifier(charIDToTypeID("Lyr "), layerIds[index]);
                if (isFoldedFolder(executeActionGet(reference))) continue;
                var property = new ActionReference();
                property.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("layerSectionExpanded"));
                property.putIdentifier(charIDToTypeID("Lyr "), layerIds[index]);
                var descriptor = new ActionDescriptor();
                descriptor.putReference(charIDToTypeID("null"), property);
                descriptor.putBoolean(charIDToTypeID("T   "), false);
                executeAction(charIDToTypeID("setd"), descriptor, DialogModes.NO);
            } catch (ignored) {
                // The folder is gone: this Apply replaced it.
            }
        }
    }

    function validateRequest(request) {
        if (!request || request.request_type !== "painter_to_photoshop_transfer") {
            throw new Error("Expected a Painter-to-Photoshop transfer request");
        }
        if (!request.layers || request.layers.length === 0) {
            throw new Error("Transfer request contains no mapped layers");
        }
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
        // Replay each drop exactly as the desktop preview: a drop into a
        // group lands at its top, as Photoshop's own drops do; repeated drops
        // on one layer insert right above or below that layer.
        if (item.insertion === "inside") {
            if (isGroup(item)) {
                prependFolder(layer, target);
            } else {
                layer.move(target, ElementPlacement.PLACEATBEGINNING);
            }
        } else if (item.insertion === "before") {
            layer.move(target, ElementPlacement.PLACEBEFORE);
        } else {
            layer.move(target, ElementPlacement.PLACEAFTER);
        }
    }

    // Photoshop refuses to move a folder into a folder, and a folder moved
    // beside a group's edge child can leave the group: a Painter folder
    // dropped into "Alpha" once landed after it. A layer can go to a group's
    // top, and a folder can go beside a layer, so a temporary layer at the
    // top holds the place the folder moves in front of.
    function prependFolder(folder, group) {
        var anchor = group.artLayers.add();
        try {
            anchor.move(group, ElementPlacement.PLACEATBEGINNING);
            folder.move(anchor, ElementPlacement.PLACEBEFORE);
        } finally {
            anchor.remove();
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

}());
