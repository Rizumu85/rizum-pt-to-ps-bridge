(function () {
    __RIZUM_JSON_RUNTIME__
__RIZUM_TARGET_RUNTIME__
    // Reads, for each place Bridge will insert Painter layers, what the PSD
    // shows below that place, so Painter can rewrite the layers to look there
    // as they do in Painter (design.md §4.3). It works on a duplicate of the
    // document and closes it unsaved: the mapped PSD is never changed, which
    // is why an Apply can still be cancelled while this runs.
    var requestPath = __RIZUM_BACKDROP_REQUEST_PATH__;
    var folder = File(requestPath).parent.fsName;
    var resultPath = folder + "/photoshop_backdrop_result.json";
    var progressPath = folder + "/photoshop_backdrop_progress.json";
    var result = { success: false, backdrops: [], errors: [] };
    var previousDialogs = app.displayDialogs;

    app.displayDialogs = DialogModes.NO;

    try {
        publishProgress("reading_request", 0, 0);
        var request = readJson(requestPath);
        if (!request || request.request_type !== "photoshop_backdrop_request") {
            throw new Error("Expected a Photoshop backdrop request");
        }
        var points = request.points || [];
        var document = resolveDocument(request.document || {});
        app.activeDocument = document;
        // Resolve every place in the original, where layer ids are valid, and
        // carry it into each duplicate by position.
        var paths = [];
        for (var index = 0; index < points.length; index += 1) {
            var target = findTarget(document, points[index]);
            if (points[index].insertion === "inside" && target.typename !== "LayerSet") {
                throw new Error("Mapped inside target is no longer a Photoshop group");
            }
            paths.push(indexPath(target));
        }
        publishProgress("reading_backdrop", 0, points.length);
        for (index = 0; index < points.length; index += 1) {
            var copy = document.duplicate("PT Bridge backdrop", false);
            try {
                var png = folder + "/backdrop_" + index + ".png";
                isolateBelow(copy, paths[index], points[index].insertion);
                copy.saveAs(File(png), new PNGSaveOptions(), true, Extension.LOWERCASE);
                result.backdrops.push({ key: points[index].key, png: png });
            } finally {
                copy.close(SaveOptions.DONOTSAVECHANGES);
                app.activeDocument = document;
            }
            publishProgress("reading_backdrop", index + 1, points.length);
        }
        result.success = true;
    } catch (error) {
        result.errors.push({ name: requestPath, message: errorMessage(error) });
    } finally {
        app.displayDialogs = previousDialogs;
        writeJsonAtomic(resultPath, result);
    }

    function publishProgress(phase, completed, total) {
        writeJsonAtomic(progressPath, { phase: phase, completed: completed, total: total });
    }

    function indexPath(layer) {
        var path = [];
        var current = layer;
        while (current && current.typename !== "Document") {
            var siblings = current.parent.layers;
            for (var index = 0; index < siblings.length; index += 1) {
                if (siblings[index] === current || Number(siblings[index].id) === Number(current.id)) {
                    path.unshift(index);
                    break;
                }
            }
            current = current.parent;
        }
        return path;
    }

    // Leaves visible exactly what lies below the insertion place, as the
    // inserted layers will composite against it.
    function isolateBelow(copy, path, insertion) {
        // chain[i]: the layer at depth i on the way to the target, with the
        // collection it sits in.
        var chain = [];
        var owner = copy;
        for (var depth = 0; depth < path.length; depth += 1) {
            var layer = owner.layers[path[depth]];
            chain.push({ owner: owner, index: path[depth], layer: layer });
            owner = layer;
        }
        var target = chain[chain.length - 1];
        // levels: the folders the insert lands inside, outermost first.
        var levels;
        if (insertion === "inside") {
            levels = chain;
            hideFirst(target.layer, target.layer.layers.length);
        } else {
            levels = chain.slice(0, chain.length - 1);
            hideFirst(target.owner, insertion === "before" ? target.index : target.index + 1);
        }
        for (var level = levels.length - 1; level >= 0; level -= 1) {
            hideFirst(levels[level].owner, levels[level].index);
        }
        // Inside an isolated folder Photoshop composites the insert against
        // that folder's own content, not the document; read only that, with
        // the folder and everything around it out of the way.
        var isolated = -1;
        for (level = levels.length - 1; level >= 0; level -= 1) {
            if (levels[level].layer.blendMode !== BlendMode.PASSTHROUGH) {
                isolated = level;
                break;
            }
        }
        if (isolated < 0) {
            return;
        }
        for (level = 0; level <= isolated; level += 1) {
            var siblings = levels[level].owner.layers;
            for (var index = 0; index < siblings.length; index += 1) {
                if (index !== levels[level].index) {
                    siblings[index].visible = false;
                }
            }
            neutralize(copy, levels[level].layer, level === isolated);
        }
    }

    function hideFirst(owner, count) {
        for (var index = 0; index < count; index += 1) {
            owner.layers[index].visible = false;
        }
    }

    function neutralize(copy, folder, isolatedFolder) {
        if (isolatedFolder) {
            folder.blendMode = BlendMode.NORMAL;
        }
        folder.opacity = 100;
        disableMask(copy, folder);
    }

    function disableMask(copy, layer) {
        try {
            app.activeDocument = copy;
            selectLayer(layer);
            var descriptor = new ActionDescriptor();
            var reference = new ActionReference();
            reference.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
            descriptor.putReference(charIDToTypeID("null"), reference);
            var settings = new ActionDescriptor();
            settings.putBoolean(stringIDToTypeID("userMaskEnabled"), false);
            descriptor.putObject(charIDToTypeID("T   "), charIDToTypeID("Lyr "), settings);
            executeAction(charIDToTypeID("setd"), descriptor, DialogModes.NO);
        } catch (ignored) {
            // A folder without a mask has nothing to disable.
        }
    }
}());
