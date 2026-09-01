(function () {
    var requestPath = __RIZUM_TRANSFER_REQUEST_PATH__;
    var resultPath = File(requestPath).parent.fsName + "/photoshop_transfer_result.json";
    var result = { inserted: [], errors: [], warnings: [], saved: false };
    var previousDialogs = app.displayDialogs;
    var previousRulerUnits = app.preferences.rulerUnits;

    app.displayDialogs = DialogModes.NO;
    app.preferences.rulerUnits = Units.PIXELS;
    app.bringToFront();

    try {
        var request = readJson(requestPath);
        validateRequest(request);
        var document = resolveDocument(request.document || {});
        app.activeDocument = document;
        var anchors = {};

        for (var index = 0; index < request.layers.length; index += 1) {
            var item = request.layers[index];
            try {
                var target = findLayerById(document, Number(item.target_layer_id));
                if (!target) {
                    throw new Error("Photoshop target layer no longer exists: " + item.target_layer_id);
                }
                var placed = placePngLayer(item.png, document);
                placed.name = String(item.name || "Painter Layer");
                placed.visible = item.visible !== false;
                placed.opacity = opacityPercent(item.opacity);
                var blendMode = photoshopBlendMode(item.blend_mode);
                if (blendMode !== null) {
                    placed.blendMode = blendMode;
                }
                placed.rasterize(RasterizeType.ENTIRELAYER);
                moveMappedLayer(placed, target, item, anchors);
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
        }

        if (result.errors.length === 0) {
            try {
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
        writeResult(resultPath, result);
        app.displayDialogs = previousDialogs;
        app.preferences.rulerUnits = previousRulerUnits;
    }

    if (result.errors.length > 0) {
        alert(
            "Rizum PT Bridge inserted " + result.inserted.length +
            " layer(s), with " + result.errors.length +
            " error(s).\n\nDetails: " + resultPath
        );
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
        var targetName = String(descriptor.name || "");
        var index;

        for (index = 0; index < app.documents.length; index += 1) {
            var candidate = app.documents[index];
            if (!isNaN(targetId) && Number(candidate.id) === targetId) {
                return candidate;
            }
            if (targetPath && documentPath(candidate) === normalizedPath(targetPath)) {
                return candidate;
            }
        }
        if (targetPath && File(targetPath).exists) {
            return app.open(File(targetPath));
        }
        for (index = 0; index < app.documents.length; index += 1) {
            if (targetName && String(app.documents[index].name) === targetName) {
                return app.documents[index];
            }
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
        placeEmbeddedFile(file);
        var placed = targetDocument.activeLayer;
        if (!placed) {
            throw new Error("Photoshop did not create a placed layer: " + path);
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

    function moveMappedLayer(layer, target, item, anchors) {
        var key = String(item.insertion) + ":" + String(item.target_layer_id);
        var previous = anchors[key];
        if (previous) {
            layer.move(previous, ElementPlacement.PLACEAFTER);
        } else if (item.insertion === "inside") {
            if (target.typename !== "LayerSet") {
                throw new Error("Mapped inside target is no longer a Photoshop group");
            }
            layer.move(target, ElementPlacement.PLACEATBEGINNING);
        } else {
            layer.move(target, ElementPlacement.PLACEAFTER);
        }
        anchors[key] = layer;
    }

    function opacityPercent(value) {
        var opacity = Number(value);
        if (isNaN(opacity)) {
            return 100;
        }
        if (opacity >= 0 && opacity <= 1) {
            opacity *= 100;
        }
        return Math.max(0, Math.min(100, opacity));
    }

    function photoshopBlendMode(value) {
        switch (String(value || "").toUpperCase()) {
        case "NORMAL": return BlendMode.NORMAL;
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

    function writeResult(path, state) {
        var file = File(path);
        if (!file.open("w")) {
            return;
        }
        file.encoding = "UTF8";
        if (typeof JSON !== "undefined" && JSON.stringify) {
            file.write(JSON.stringify(state, null, 2));
        } else {
            file.write("{\"inserted\":[],\"errors\":[{\"message\":\"JSON.stringify unavailable\"}]}");
        }
        file.close();
    }

    function errorMessage(error) {
        if (!error) {
            return "Unknown error";
        }
        return error.message ? String(error.message) : String(error);
    }
}());
