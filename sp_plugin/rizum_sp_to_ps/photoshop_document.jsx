#target photoshop

(function () {
    var requestPath = __RIZUM_DOCUMENT_REQUEST_PATH__;
    var request = null;
    var source = null;
    var renderDocument = null;
    var progress = null;
    var previousDialogs = app.displayDialogs;
    var result = {
        success: false,
        manifest: null,
        exported_count: 0,
        errors: [],
        elapsed_ms: 0
    };
    var startedAt = new Date().getTime();

    app.displayDialogs = DialogModes.NO;
    try {
        request = readJson(requestPath);
        validateRequest(request);
        source = resolveDocument(String(request.psd_file));
        app.activeDocument = source;

        var records = collectDocumentLayers(source);
        // One isolated duplicate keeps Photoshop's native renderer while avoiding
        // a full PSD clone for every layer in large production documents.
        renderDocument = source.duplicate("Rizum Document Export", false);
        if (renderDocument.mode !== DocumentMode.RGB) {
            renderDocument.changeMode(ChangeMode.RGB);
        }
        progress = createProgress(records.length);
        var exported = [];
        for (var index = 0; index < records.length; index += 1) {
            var record = records[index];
            updateProgress(progress, index, records.length, record.display_name);
            try {
                var filename = uniquePngName(record.display_name, index);
                var outputPath = File(request.output_dir + "/" + filename).fsName;
                exportAppliedLayer(source, renderDocument, record.index_path, outputPath);
                record.png = filename;
                exported.push(manifestLayer(record));
            } catch (layerError) {
                result.errors.push({
                    layer: record.path,
                    error: errorMessage(layerError)
                });
            }
        }

        if (exported.length === 0) {
            throw new Error("Photoshop could not export any layers from this document.");
        }

        var manifest = {
            schema_version: 1,
            request_type: "photoshop_selection",
            rizum_version: "0.1.65",
            created_at: isoTimestamp(),
            mode: "applied",
            document: {
                id: documentId(source),
                name: String(source.name || File(request.psd_file).name),
                path: documentPath(source)
            },
            sidecar: sidecarPath(documentPath(source)),
            layers: exported,
            errors: result.errors
        };
        writeJsonAtomic(String(request.manifest_file), manifest);
        result.success = true;
        result.manifest = String(request.manifest_file);
        result.exported_count = exported.length;
    } catch (error) {
        result.errors.push({ layer: "Photoshop document", error: errorMessage(error) });
    } finally {
        if (renderDocument) {
            try {
                renderDocument.close(SaveOptions.DONOTSAVECHANGES);
            } catch (ignoredClose) {}
        }
        if (source) {
            try {
                app.activeDocument = source;
            } catch (ignoredActivate) {}
        }
        closeProgress(progress);
        result.elapsed_ms = new Date().getTime() - startedAt;
        app.displayDialogs = previousDialogs;
        if (request && request.result_file) {
            writeJsonAtomic(String(request.result_file), result);
        }
    }

    function validateRequest(value) {
        if (!value || value.request_type !== "photoshop_document_export") {
            throw new Error("Expected a Photoshop document export request.");
        }
        if (value.schema_version !== 1) {
            throw new Error("Unsupported Photoshop document request schema.");
        }
        if (!value.psd_file || !File(value.psd_file).exists) {
            throw new Error("Photoshop document does not exist: " + value.psd_file);
        }
        if (!value.output_dir || !Folder(value.output_dir).exists) {
            throw new Error("Photoshop export directory does not exist: " + value.output_dir);
        }
        if (!value.manifest_file || !value.result_file) {
            throw new Error("Photoshop document request has no output contract.");
        }
    }

    function resolveDocument(path) {
        var expected = normalizedPath(path);
        for (var index = 0; index < app.documents.length; index += 1) {
            var candidate = app.documents[index];
            if (normalizedPath(documentPath(candidate)) === expected) {
                return candidate;
            }
        }
        return app.open(File(path));
    }

    function collectDocumentLayers(document) {
        var records = [];
        var previousLayer = null;
        try {
            previousLayer = document.activeLayer;
        } catch (ignored) {}
        collectLayers(document, document.layers, [], [], null, records);
        if (previousLayer) {
            try {
                document.activeLayer = previousLayer;
            } catch (ignoredRestore) {}
        }
        return records;
    }

    function collectLayers(document, collection, indexPath, namePath, parentId, output) {
        for (var index = 0; index < collection.length; index += 1) {
            var layer = collection[index];
            var nextIndexPath = indexPath.concat([index]);
            var nextNamePath = namePath.concat([String(layer.name || "Layer")]);
            var isGroup = layer.typename === "LayerSet";
            var nativeId = layerId(document, layer);
            output.push({
                source_id: "ps:" + documentId(document) + ":" + nativeId,
                ps_layer_id: nativeId,
                parent_id: parentId,
                display_name: String(layer.name || "Layer"),
                ps_kind: isGroup ? "group" : layerKind(layer),
                group: namePath.length ? namePath.join("/") : null,
                path: nextNamePath.join("/"),
                blend_mode: blendMode(layer),
                opacity: numericValue(layer.opacity, 100),
                visible: layer.visible !== false,
                index_path: nextIndexPath,
                png: null
            });
            if (isGroup) {
                collectLayers(
                    document,
                    layer.layers,
                    nextIndexPath,
                    nextNamePath,
                    nativeId,
                    output
                );
            }
        }
    }

    function exportAppliedLayer(source, renderDocument, indexPath, outputPath) {
        // The isolated duplicate lets Photoshop render native masks, effects,
        // clipping, and imported PSD features without touching the working file.
        app.activeDocument = renderDocument;
        restoreVisibility(source.layers, renderDocument.layers);
        isolateLayer(renderDocument, indexPath);
        var output = File(outputPath);
        if (output.exists) {
            output.remove();
        }
        var options = new PNGSaveOptions();
        options.interlaced = false;
        try {
            renderDocument.saveAs(output, options, true, Extension.LOWERCASE);
        } finally {
            app.activeDocument = source;
        }
    }

    function restoreVisibility(sourceLayers, renderLayers) {
        if (sourceLayers.length !== renderLayers.length) {
            throw new Error("Photoshop layer structure changed during export.");
        }
        for (var index = 0; index < sourceLayers.length; index += 1) {
            var sourceLayer = sourceLayers[index];
            var renderLayer = renderLayers[index];
            renderLayer.visible = sourceLayer.visible;
            if (sourceLayer.typename === "LayerSet") {
                if (renderLayer.typename !== "LayerSet") {
                    throw new Error("Photoshop group structure changed during export.");
                }
                restoreVisibility(sourceLayer.layers, renderLayer.layers);
            }
        }
    }

    function isolateLayer(document, indexPath) {
        var collection = document.layers;
        var current = null;
        for (var depth = 0; depth < indexPath.length; depth += 1) {
            var targetIndex = indexPath[depth];
            for (var index = 0; index < collection.length; index += 1) {
                collection[index].visible = index === targetIndex;
            }
            current = collection[targetIndex];
            if (!current) {
                throw new Error("Photoshop layer structure changed during export.");
            }
            current.visible = true;
            if (depth + 1 < indexPath.length) {
                if (current.typename !== "LayerSet") {
                    throw new Error("Photoshop layer path no longer resolves to a group.");
                }
                collection = current.layers;
            }
        }
        document.activeLayer = current;
    }

    function manifestLayer(record) {
        return {
            source_id: record.source_id,
            ps_layer_id: record.ps_layer_id,
            parent_id: record.parent_id,
            display_name: record.display_name,
            ps_kind: record.ps_kind,
            group: record.group,
            path: record.path,
            blend_mode: record.blend_mode,
            opacity: record.opacity,
            visible: record.visible,
            png: record.png,
            mask_png: null
        };
    }

    function layerId(document, layer) {
        try {
            var direct = Number(layer.id);
            if (!isNaN(direct)) {
                return direct;
            }
        } catch (ignored) {}
        document.activeLayer = layer;
        var reference = new ActionReference();
        reference.putEnumerated(
            charIDToTypeID("Lyr "),
            charIDToTypeID("Ordn"),
            charIDToTypeID("Trgt")
        );
        var descriptor = executeActionGet(reference);
        return descriptor.getInteger(stringIDToTypeID("layerID"));
    }

    function documentId(document) {
        try {
            return Number(document.id);
        } catch (ignored) {
            return 0;
        }
    }

    function layerKind(layer) {
        try {
            return enumName(layer.kind, "layerkind") || "layer";
        } catch (ignored) {
            return "layer";
        }
    }

    function blendMode(layer) {
        try {
            return enumName(layer.blendMode, "blendmode") || "normal";
        } catch (ignored) {
            return "normal";
        }
    }

    function enumName(value, prefix) {
        return String(value || "")
            .replace(new RegExp("^" + prefix + "\\.", "i"), "")
            .toLowerCase();
    }

    function numericValue(value, fallback) {
        var number = Number(value);
        return isNaN(number) ? fallback : number;
    }

    function uniquePngName(name, index) {
        var safe = String(name || "Layer")
            .replace(/[\\\/:*?"<>|]/g, "_")
            .replace(/^\s+|\s+$/g, "");
        if (!safe) {
            safe = "Layer";
        }
        var prefix = String(index + 1);
        while (prefix.length < 4) {
            prefix = "0" + prefix;
        }
        return prefix + "_" + safe + ".png";
    }

    function sidecarPath(path) {
        var value = String(path || "");
        return value ? value.replace(/\.[^.\\\/]*$/, "") + ".rizum.json" : null;
    }

    function documentPath(document) {
        try {
            return document.fullName.fsName;
        } catch (ignored) {
            return "";
        }
    }

    function normalizedPath(path) {
        return String(path || "").replace(/\\/g, "/").toLowerCase();
    }

    function isoTimestamp() {
        var date = new Date();
        if (date.toISOString) {
            return date.toISOString();
        }
        return date.toUTCString();
    }

    function createProgress(total) {
        try {
            var window = new Window("palette", "PT Bridge · Reading PSD");
            window.orientation = "column";
            window.alignChildren = ["fill", "top"];
            window.preferredSize.width = 360;
            window.label = window.add("statictext", undefined, "Preparing layers...");
            window.bar = window.add("progressbar", undefined, 0, Math.max(1, total));
            window.bar.preferredSize = [340, 14];
            window.show();
            window.update();
            return window;
        } catch (ignored) {
            return null;
        }
    }

    function updateProgress(window, index, total, name) {
        if (!window) {
            return;
        }
        window.label.text = "Exporting " + (index + 1) + " / " + total + " · " + name;
        window.bar.value = index;
        window.update();
    }

    function closeProgress(window) {
        if (!window) {
            return;
        }
        try {
            window.bar.value = window.bar.maxvalue;
            window.update();
            window.close();
        } catch (ignored) {}
    }

    function readJson(path) {
        var file = File(path);
        if (!file.exists || !file.open("r")) {
            throw new Error("Could not open JSON file: " + path);
        }
        file.encoding = "UTF8";
        var text = file.read();
        file.close();
        return JSON.parse(text);
    }

    function writeJsonAtomic(path, value) {
        var target = File(path);
        var temporary = File(path + ".tmp");
        if (!temporary.open("w")) {
            throw new Error("Could not write JSON file: " + path);
        }
        temporary.encoding = "UTF8";
        temporary.write(JSON.stringify(value, null, 2));
        temporary.close();
        if (target.exists && !target.remove()) {
            throw new Error("Could not replace JSON file: " + path);
        }
        if (!temporary.rename(target.name)) {
            throw new Error("Could not publish JSON file: " + path);
        }
    }

    function errorMessage(error) {
        if (!error) {
            return "Unknown error";
        }
        return error.message ? String(error.message) : String(error);
    }
}());
