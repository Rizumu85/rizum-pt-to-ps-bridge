#target photoshop

(function () {
    var exportListPath = __RIZUM_EXPORT_LIST_PATH__;
    var resultPath = File(exportListPath).parent.fsName + "/_photoshop_build_result.json";
    var result = {
        built: [],
        errors: [],
        timings: {
            import_ms: 0,
            save_ms: 0,
            total_ms: 0
        }
    };
    var runStartedAt = new Date().getTime();
    var previousDialogs = app.displayDialogs;
    var previousRulerUnits = app.preferences.rulerUnits;
    var progress = null;

    app.displayDialogs = DialogModes.NO;
    app.preferences.rulerUnits = Units.PIXELS;
    app.bringToFront();

    try {
        var exportList = readJson(exportListPath);
        var requestPaths = buildRequestPaths(exportList);
        var pendingSaves = [];
        progress = createImportProgress(requestPaths.length);
        var importStartedAt = new Date().getTime();
        for (var index = 0; index < requestPaths.length; index += 1) {
            var requestPath = requestPaths[index];
            progress.beginRequest(index, requestPath);
            try {
                var request = readJson(requestPath);
                var document = buildRequest(request, progress);
                pendingSaves.push({
                    requestPath: requestPath,
                    request: request,
                    document: document
                });
                progress.finishRequest(index, "Imported " + File(request.psd_file).name);
            } catch (error) {
                result.errors.push({
                    request: requestPath,
                    message: errorMessage(error)
                });
                progress.finishRequest(index, "Failed: " + errorMessage(error));
            }
        }
        result.timings.import_ms = new Date().getTime() - importStartedAt;

        var saveStartedAt = new Date().getTime();
        progress.beginSavePhase(pendingSaves.length);
        for (var saveIndex = 0; saveIndex < pendingSaves.length; saveIndex += 1) {
            var pending = pendingSaves[saveIndex];
            progress.beginSave(saveIndex, pending.request);
            try {
                app.activeDocument = pending.document;
                savePsd(pending.document, pending.request.psd_file);
                result.built.push(pending.request.psd_file);
                progress.finishSave(
                    saveIndex,
                    "Saved " + File(pending.request.psd_file).name
                );
            } catch (saveError) {
                result.errors.push({
                    request: pending.requestPath,
                    message: errorMessage(saveError)
                });
                progress.finishSave(saveIndex, "Save failed: " + errorMessage(saveError));
            }
        }
        result.timings.save_ms = new Date().getTime() - saveStartedAt;
    } catch (error) {
        result.errors.push({
            request: exportListPath,
            message: errorMessage(error)
        });
    } finally {
        result.timings.total_ms = new Date().getTime() - runStartedAt;
        if (progress) {
            progress.close();
        }
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

    function buildRequest(request, progress) {
        validateRequest(request);
        var resolution = request.uv_tile.resolution;
        var documentName = fileStem(request.psd_file);
        var hasUvMap = request.uv_map_asset && request.uv_map_asset.path;
        var progressState = {
            completed: 0,
            total: countImportUnits(request.layers || []) + 2 + (hasUvMap ? 1 : 0)
        };
        progress.configureRequest(request, progressState.total);
        var document = app.documents.add(
            UnitValue(Number(resolution.width), "px"),
            UnitValue(Number(resolution.height), "px"),
            72,
            documentName,
            NewDocumentMode.RGB,
            DocumentFill.TRANSPARENT
        );
        advanceImportProgress(progress, progressState, "Created " + documentName);
        var buildState = {
            placeholderName: "__rizum_placeholder_" + new Date().getTime() + "__",
            placeholderRemoved: false
        };
        document.activeLayer.name = buildState.placeholderName;

        try {
            placeNodes(
                request.layers || [],
                document,
                document,
                request.channel,
                progress,
                progressState,
                buildState
            );

            if (hasUvMap) {
                // Import this after the Painter tree because PLACEATBEGINNING
                // guarantees the optional reference wireframe stays topmost.
                var uvMapLayer = placePngLayer(
                    request.uv_map_asset.path,
                    document,
                    document
                );
                uvMapLayer.name = String(request.uv_map_asset.label || "UV Map");
                uvMapLayer.visible = true;
                advanceImportProgress(progress, progressState, "Imported UV Map");
            }

            if (!buildState.placeholderRemoved) {
                throw new Error("Photoshop build did not replace its initial layer");
            }
            // Placed PNGs stay as smart objects during assembly so Photoshop
            // performs one rasterization pass instead of one pass per asset.
            progress.describe("Finalizing " + documentName);
            document.rasterizeAllLayers();
            advanceImportProgress(
                progress,
                progressState,
                "Finalized " + documentName
            );
            return document;
        } catch (error) {
            try {
                document.close(SaveOptions.DONOTSAVECHANGES);
            } catch (ignored) {}
            throw error;
        }
    }

    function placeNodes(
        nodes,
        document,
        parent,
        channel,
        progress,
        progressState,
        buildState
    ) {
        for (var index = nodes.length - 1; index >= 0; index -= 1) {
            placeNode(
                nodes[index],
                document,
                parent,
                channel,
                progress,
                progressState,
                buildState
            );
        }
    }

    function placeNode(
        node,
        document,
        parent,
        channel,
        progress,
        progressState,
        buildState
    ) {
        if (!node) {
            return null;
        }

        var placed = null;
        if (node.asset && node.asset.path) {
            placed = placePngLayer(node.asset.path, document, parent);
            removeBuildPlaceholder(document, buildState);
            advanceImportProgress(
                progress,
                progressState,
                "Imported " + nodeDisplayName(node)
            );
        } else if (hasBuildableChildren(node)) {
            placed = parent.layerSets.add();
            removeBuildPlaceholder(document, buildState);
            placeNodes(
                node.children || [],
                document,
                placed,
                channel,
                progress,
                progressState,
                buildState
            );
        } else {
            return null;
        }

        applyNodeProperties(placed, node, channel);
        if (node.mask_asset && node.mask_asset.path) {
            try {
                applyMask(document, placed, node.mask_asset.path);
                advanceImportProgress(
                    progress,
                    progressState,
                    "Applied mask: " + nodeDisplayName(node)
                );
            } catch (error) {
                throw new Error(
                    "Could not apply mask for " + placed.name + ": " +
                    errorMessage(error)
                );
            }
        }
        return placed;
    }

    function countImportUnits(nodes) {
        var total = 0;
        for (var index = 0; index < nodes.length; index += 1) {
            var node = nodes[index];
            if (!node) {
                continue;
            }

            var buildable = false;
            if (node.asset && node.asset.path) {
                total += 1;
                buildable = true;
            } else if (hasBuildableChildren(node)) {
                total += countImportUnits(node.children || []);
                buildable = true;
            }

            if (buildable && node.mask_asset && node.mask_asset.path) {
                total += 1;
            }
        }
        return total;
    }

    function advanceImportProgress(progress, state, detail) {
        state.completed += 1;
        progress.updateRequest(state.completed, state.total, detail);
    }

    function nodeDisplayName(node) {
        return String(node.name || node.kind || "Painter Layer");
    }

    function createImportProgress(requestCount) {
        var requestTotal = Math.max(1, requestCount);

        // The automatic path runs as ExtendScript without requiring the UXP
        // panel to be open, so progress must live in Photoshop's own ScriptUI.
        var win = new Window(
            "palette",
            "Rizum PT-to-PS Bridge",
            undefined,
            {
                closeButton: false,
                maximizeButton: false,
                minimizeButton: false
            }
        );
        win.orientation = "column";
        win.alignChildren = ["fill", "top"];
        win.status = win.add("statictext", undefined, "Preparing Photoshop import...");
        win.detail = win.add("statictext", undefined, "Reading Painter export list");
        win.bar = win.add("progressbar", undefined, 0, requestTotal * 100);
        win.status.preferredSize = [420, 20];
        win.detail.preferredSize = [420, 20];
        win.bar.preferredSize = [420, 18];
        win.requestIndex = 0;
        win.requestLabel = "Painter export";
        win.requestSteps = 1;
        win.phaseLabel = "Importing";
        win.phaseTotal = requestTotal;

        win.renderProgress = function (value, detail) {
            var maximum = Math.max(1, win.phaseTotal) * 100;
            var clamped = Math.max(0, Math.min(maximum, value));
            var percent = Math.round((clamped / maximum) * 100);
            win.bar.value = clamped;
            win.status.text =
                win.phaseLabel + " " + (win.requestIndex + 1) + " of " +
                win.phaseTotal +
                " - " + percent + "%";
            win.detail.text = detail || win.requestLabel;
            win.update();
            win.show();
        };

        win.beginRequest = function (index, requestPath) {
            win.phaseLabel = "Importing";
            win.phaseTotal = requestTotal;
            win.requestIndex = index;
            win.requestLabel = File(requestPath).name;
            win.requestSteps = 1;
            win.renderProgress(index * 100, "Reading " + win.requestLabel);
        };

        win.configureRequest = function (request, totalSteps) {
            win.requestLabel = requestDisplayName(request);
            win.requestSteps = Math.max(1, totalSteps);
            win.renderProgress(win.requestIndex * 100, win.requestLabel);
        };

        win.describe = function (detail) {
            var value = win.requestIndex * 100;
            win.renderProgress(value + win.bar.value % 100, detail);
        };

        win.updateRequest = function (completed, totalSteps, detail) {
            var stepTotal = Math.max(1, totalSteps || win.requestSteps);
            var fraction = Math.max(0, Math.min(1, completed / stepTotal));
            win.renderProgress(win.requestIndex * 100 + fraction * 100, detail);
        };

        win.finishRequest = function (index, detail) {
            win.requestIndex = index;
            win.renderProgress((index + 1) * 100, detail);
        };

        win.beginSavePhase = function (saveCount) {
            win.phaseLabel = "Saving";
            win.phaseTotal = Math.max(1, saveCount);
            win.bar.maxvalue = win.phaseTotal * 100;
            win.bar.value = 0;
        };

        win.beginSave = function (index, request) {
            win.requestIndex = index;
            win.requestLabel = requestDisplayName(request);
            win.renderProgress(index * 100, "Saving " + File(request.psd_file).name);
        };

        win.finishSave = function (index, detail) {
            win.requestIndex = index;
            win.renderProgress((index + 1) * 100, detail);
        };

        win.center();
        win.show();
        return win;
    }

    function requestDisplayName(request) {
        var textureSet = String(request.texture_set || "Texture Set");
        var channel = String(request.channel || "Channel");
        return textureSet + " / " + channel;
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

    function placePngLayer(path, targetDocument, parent) {
        var file = File(path);
        if (!file.exists) {
            throw new Error("PNG asset does not exist: " + path);
        }

        app.activeDocument = targetDocument;
        placeEmbeddedFile(file);
        var placed = targetDocument.activeLayer;
        if (!placed) {
            throw new Error("Photoshop did not create a placed layer: " + path);
        }
        // Place Embedded already creates a layer. Moving that layer directly
        // avoids temporary anchors whose stale DOM handles trigger unavailable
        // Select commands in current Photoshop builds.
        placed.move(parent, ElementPlacement.PLACEATBEGINNING);
        targetDocument.activeLayer = placed;
        return placed;
    }

    function placeEmbeddedFile(file) {
        // Direct placement avoids opening and closing a full Photoshop
        // document for every 4K layer and mask in a Painter stack.
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
        descriptor.putObject(
            charIDToTypeID("Ofst"),
            charIDToTypeID("Ofst"),
            offset
        );
        executeAction(charIDToTypeID("Plc "), descriptor, DialogModes.NO);
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

        var maskLayer = placePngLayer(path, targetDocument, targetLayer.parent);
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
        // Placed smart objects do not expose a reliable DOM `id` in every
        // Photoshop release; activeLayer assignment avoids the unavailable
        // Action Manager Get command used to resolve that property.
        app.activeDocument.activeLayer = layer;
    }

    function removeBuildPlaceholder(document, state) {
        if (state.placeholderRemoved) {
            return;
        }
        app.activeDocument = document;
        for (var index = 0; index < document.layers.length; index += 1) {
            var candidate = document.layers[index];
            if (candidate.name !== state.placeholderName) {
                continue;
            }
            // Remove the initial layer as soon as the first real node exists.
            // Direct Place invalidates long-lived DOM handles, so postponing
            // this cleanup until a large import finishes is not reliable.
            document.activeLayer = candidate;
            candidate.remove();
            state.placeholderRemoved = true;
            return;
        }
        // Direct Place consumes the transparent document layer in current
        // Photoshop. Absence means cleanup is complete; group-first builds
        // leave the named layer intact and take the explicit branch above.
        state.placeholderRemoved = true;
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
        var timings = state.timings || {};
        file.write(
            "{\n" +
            "  \"schema_version\": 1,\n" +
            "  \"export_list\": " + jsonQuote(sourcePath) + ",\n" +
            "  \"built\": [" + built.join(",") + "],\n" +
            "  \"errors\": [" + errors.join(",") + "],\n" +
            "  \"timings\": {" +
                "\"import_ms\":" + Number(timings.import_ms || 0) + "," +
                "\"save_ms\":" + Number(timings.save_ms || 0) + "," +
                "\"total_ms\":" + Number(timings.total_ms || 0) +
            "}\n" +
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
