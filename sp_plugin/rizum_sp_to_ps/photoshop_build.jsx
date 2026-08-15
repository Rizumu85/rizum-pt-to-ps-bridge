#target photoshop

(function () {
    var exportListPath = __RIZUM_EXPORT_LIST_PATH__;
    var resultPath = File(exportListPath).parent.fsName + "/_photoshop_build_result.json";
    var result = {
        built: [],
        errors: []
    };
    var previousDialogs = app.displayDialogs;
    var previousRulerUnits = app.preferences.rulerUnits;

    app.displayDialogs = DialogModes.NO;
    app.preferences.rulerUnits = Units.PIXELS;
    app.bringToFront();

    try {
        var exportList = readJson(exportListPath);
        var requestPaths = buildRequestPaths(exportList);
        for (var index = 0; index < requestPaths.length; index += 1) {
            var requestPath = requestPaths[index];
            try {
                var request = readJson(requestPath);
                buildRequest(request);
                result.built.push(request.psd_file);
            } catch (error) {
                result.errors.push({
                    request: requestPath,
                    message: errorMessage(error)
                });
            }
        }
    } catch (error) {
        result.errors.push({
            request: exportListPath,
            message: errorMessage(error)
        });
    } finally {
        app.displayDialogs = previousDialogs;
        app.preferences.rulerUnits = previousRulerUnits;
        writeResult(resultPath, exportListPath, result);
    }

    if (result.errors.length > 0) {
        alert(
            "Rizum PT-to-PS built " + result.built.length +
            " document(s), with " + result.errors.length +
            " error(s).\n\nDetails: " + resultPath
        );
    }

    function buildRequest(request) {
        validateRequest(request);
        var resolution = request.uv_tile.resolution;
        var documentName = fileStem(request.psd_file);
        var document = app.documents.add(
            UnitValue(Number(resolution.width), "px"),
            UnitValue(Number(resolution.height), "px"),
            72,
            documentName,
            NewDocumentMode.RGB,
            DocumentFill.TRANSPARENT
        );
        var defaultLayer = document.activeLayer;

        try {
            placeNodes(
                request.layers || [],
                document,
                document,
                request.channel
            );

            // Hold the original layer object instead of deleting by name;
            // Painter layers are allowed to be named "Layer 1" too.
            if (document.layers.length > 1) {
                defaultLayer.remove();
            }

            savePsd(document, request.psd_file);
        } catch (error) {
            try {
                document.close(SaveOptions.DONOTSAVECHANGES);
            } catch (ignored) {}
            throw error;
        }
    }

    function placeNodes(nodes, document, parent, channel) {
        for (var index = nodes.length - 1; index >= 0; index -= 1) {
            placeNode(nodes[index], document, parent, channel);
        }
    }

    function placeNode(node, document, parent, channel) {
        if (!node) {
            return null;
        }

        var placed = null;
        if (node.asset && node.asset.path) {
            placed = duplicatePngLayer(node.asset.path, document, parent);
        } else if (hasBuildableChildren(node)) {
            placed = parent.layerSets.add();
            placeNodes(node.children || [], document, placed, channel);
        } else {
            return null;
        }

        applyNodeProperties(placed, node, channel);
        if (node.mask_asset && node.mask_asset.path) {
            try {
                applyMask(document, placed, node.mask_asset.path);
            } catch (error) {
                throw new Error(
                    "Could not apply mask for " + placed.name + ": " +
                    errorMessage(error)
                );
            }
        }
        return placed;
    }

    function hasBuildableChildren(node) {
        var children = node && node.children ? node.children : [];
        for (var index = 0; index < children.length; index += 1) {
            var child = children[index];
            if ((child.asset && child.asset.path) || hasBuildableChildren(child)) {
                return true;
            }
        }
        return false;
    }

    function duplicatePngLayer(path, targetDocument, parent) {
        var file = File(path);
        if (!file.exists) {
            throw new Error("PNG asset does not exist: " + path);
        }

        var sourceDocument = app.open(file);
        try {
            var sourceLayer = sourceDocument.activeLayer;
            if (!sourceLayer) {
                throw new Error("PNG has no layer: " + path);
            }
            var duplicate = sourceLayer.duplicate(
                parent,
                ElementPlacement.PLACEATBEGINNING
            );
            sourceDocument.close(SaveOptions.DONOTSAVECHANGES);
            app.activeDocument = targetDocument;
            return duplicate;
        } catch (error) {
            try {
                sourceDocument.close(SaveOptions.DONOTSAVECHANGES);
            } catch (ignored) {}
            throw error;
        }
    }

    function applyNodeProperties(layer, node, channel) {
        selectLayer(layer);
        selectCompositeChannel();
        layer.name = String(node.name || node.kind || "Painter Layer");
        layer.visible = node.visible !== false;

        var opacity = opacityPercent(node.opacity, channel);
        if (opacity !== null && Math.abs(opacity - 100) > 0.0001) {
            layer.opacity = opacity;
        }

        var blendMode = photoshopBlendMode(node, channel, layer.typename === "LayerSet");
        if (blendMode !== null) {
            try {
                layer.blendMode = blendMode;
            } catch (ignored) {}
        }
    }

    function opacityPercent(opacity, channel) {
        var raw = opacity;
        if (opacity !== null && typeof opacity === "object") {
            raw = opacity[channel];
            if (typeof raw === "undefined") {
                raw = opacity.mask;
            }
        }
        if (raw === null || typeof raw === "undefined" || isNaN(Number(raw))) {
            return null;
        }
        var value = Number(raw);
        if (value >= 0 && value <= 1) {
            value *= 100;
        }
        return Math.max(0, Math.min(100, value));
    }

    function photoshopBlendMode(node, channel, allowPassThrough) {
        var mode = null;
        if (node.blend_decisions && node.blend_decisions[channel]) {
            mode = node.blend_decisions[channel].ps_blend_mode;
        }
        if (!mode) {
            mode = node.ps_blend_mode;
        }
        mode = String(mode || "").toUpperCase();

        switch (mode) {
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
        var file = File(path);
        if (!file.exists) {
            throw new Error("Mask asset does not exist: " + path);
        }

        var maskDocument = app.open(file);
        var maskLayer = null;
        try {
            maskLayer = maskDocument.activeLayer.duplicate(
                targetLayer,
                ElementPlacement.PLACEBEFORE
            );
            maskDocument.close(SaveOptions.DONOTSAVECHANGES);
        } catch (error) {
            try {
                maskDocument.close(SaveOptions.DONOTSAVECHANGES);
            } catch (ignored) {}
            throw error;
        }

        // Copy inside the target document. Photoshop can invalidate pixels
        // copied from a PNG as soon as that temporary source document closes.
        app.activeDocument = targetDocument;
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

        var targetReference = new ActionReference();
        targetReference.putEnumerated(
            charIDToTypeID("Chnl"),
            charIDToTypeID("Chnl"),
            charIDToTypeID("Msk ")
        );
        descriptor.putReference(charIDToTypeID("At  "), targetReference);
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
        descriptor.putBoolean(charIDToTypeID("MkVs"), true);
        executeAction(charIDToTypeID("slct"), descriptor, DialogModes.NO);
    }

    function pasteMaskPixels() {
        var descriptor = new ActionDescriptor();
        descriptor.putEnumerated(
            charIDToTypeID("AntA"),
            charIDToTypeID("Annt"),
            charIDToTypeID("Anno")
        );
        executeAction(charIDToTypeID("past"), descriptor, DialogModes.NO);
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

    function selectLayer(layer) {
        if (!layer || typeof layer.id === "undefined") {
            app.activeDocument.activeLayer = layer;
            return;
        }
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putIdentifier(charIDToTypeID("Lyr "), layer.id);
        descriptor.putReference(charIDToTypeID("null"), reference);
        descriptor.putBoolean(charIDToTypeID("MkVs"), false);
        executeAction(charIDToTypeID("slct"), descriptor, DialogModes.NO);
    }

    function savePsd(document, path) {
        var options = new PhotoshopSaveOptions();
        options.layers = true;
        options.embedColorProfile = true;
        document.saveAs(File(path), options, false, Extension.LOWERCASE);
    }

    function validateRequest(request) {
        if (!request || request.request_type !== "build") {
            throw new Error("Expected a Painter build request");
        }
        if (!request.psd_file) {
            throw new Error("Build request has no psd_file");
        }
        if (!request.uv_tile || !request.uv_tile.resolution) {
            throw new Error("Build request has no UV tile resolution");
        }
    }

    function buildRequestPaths(exportList) {
        if (!exportList || exportList.request_type !== "build_list") {
            throw new Error("Expected a Painter build-list file");
        }
        var entries = exportList.build_requests || [];
        var paths = [];
        for (var index = 0; index < entries.length; index += 1) {
            var entry = entries[index];
            var path = typeof entry === "string" ? entry : entry.path;
            if (path) {
                paths.push(path);
            }
        }
        return paths;
    }

    function readJson(path) {
        var file = File(path);
        if (!file.exists || !file.open("r")) {
            throw new Error("Could not open JSON file: " + path);
        }
        file.encoding = "UTF8";
        var text = file.read();
        file.close();
        if (typeof JSON !== "undefined" && JSON.parse) {
            return JSON.parse(text);
        }
        return eval("(" + text + ")");
    }

    function writeResult(path, sourcePath, state) {
        var file = File(path);
        if (!file.open("w")) {
            return;
        }
        file.encoding = "UTF8";
        var built = [];
        var errors = [];
        var index;
        for (index = 0; index < state.built.length; index += 1) {
            built.push(jsonQuote(state.built[index]));
        }
        for (index = 0; index < state.errors.length; index += 1) {
            errors.push(
                "{\"request\":" + jsonQuote(state.errors[index].request) +
                ",\"message\":" + jsonQuote(state.errors[index].message) + "}"
            );
        }
        file.write(
            "{\n" +
            "  \"schema_version\": 1,\n" +
            "  \"export_list\": " + jsonQuote(sourcePath) + ",\n" +
            "  \"built\": [" + built.join(",") + "],\n" +
            "  \"errors\": [" + errors.join(",") + "]\n" +
            "}\n"
        );
        file.close();
    }

    function jsonQuote(value) {
        return "\"" + String(value)
            .replace(/\\/g, "\\\\")
            .replace(/\"/g, "\\\"")
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n") + "\"";
    }

    function fileStem(path) {
        var name = File(path).name;
        return name.replace(/\.[^.]+$/, "");
    }

    function errorMessage(error) {
        var message = error && error.message ? error.message : String(error);
        if (error && error.line) {
            message += " (line " + error.line + ")";
        }
        return message;
    }
}());
