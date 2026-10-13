    // Finding the mapped PSD and its layers, and the receipt files, shared by
    // every Bridge script: the backdrop read must address exactly the layers
    // the insert will, so both use this one copy.

    function resolveDocument(descriptor) {
        var targetId = Number(descriptor.id);
        var targetPath = String(descriptor.path || "");
        var index;

        for (index = 0; index < app.documents.length; index += 1) {
            var candidate = app.documents[index];
            // Native IDs are session-local and can be reused after Photoshop
            // restarts. A saved document's path is the authoritative identity.
            if (targetPath) {
                if (documentPath(candidate) === normalizedPath(targetPath)) return currentDocument(candidate, targetPath);
            } else if (!isNaN(targetId) && Number(candidate.id) === targetId) {
                return candidate;
            }
        }
        if (targetPath && File(targetPath).exists) {
            return app.open(File(targetPath));
        }
        throw new Error("The Photoshop document used by Desktop Bridge is not open or available");
    }

    // Another program can rewrite the PSD while Photoshop keeps an older copy
    // open: the user paints in Clip Studio and saves the same file. The
    // mapper read the file, so an insert into the open copy missed the mapped
    // layers, or could not be saved over the newer file. Photoshop stamps a
    // document's metadata with the file's time when it opens or saves it, so
    // a file clearly newer than the stamp was written by someone else. With
    // nothing unsaved in Photoshop, the newer file is opened in its place.
    function currentDocument(document, path) {
        if (!changedOnDisk(document, path)) return document;
        if (!document.saved) {
            throw new Error(
                String(document.name) + " has unsaved changes in Photoshop, and another program has saved the file since. "
                + "Save or close it in Photoshop, then reload it in Bridge."
            );
        }
        document.close(SaveOptions.DONOTSAVECHANGES);
        return app.open(File(path));
    }

    function changedOnDisk(document, path) {
        try {
            var file = File(path);
            var stamp = metadataTime(String(document.xmpMetadata.rawData));
            if (stamp === null || !file.exists) return false;
            // A save stamps first and finishes writing later, the later the larger the file.
            return file.modified.getTime() - stamp > 10000 + file.length / 10000;
        } catch (ignored) {
            return false;
        }
    }

    function metadataTime(xmp) {
        var match = xmp.match(/xmp:MetadataDate(?:="|>)(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d+)?(Z|[+-]\d\d:\d\d)?/);
        if (!match) return null;
        var zone = match[7];
        if (!zone) {
            return new Date(Number(match[1]), match[2] - 1, Number(match[3]), Number(match[4]), Number(match[5]), Number(match[6])).getTime();
        }
        var time = Date.UTC(Number(match[1]), match[2] - 1, Number(match[3]), Number(match[4]), Number(match[5]), Number(match[6]));
        if (zone !== "Z") {
            var minutes = Number(zone.substr(1, 2)) * 60 + Number(zone.substr(4, 2));
            time += (zone.charAt(0) === "-" ? 1 : -1) * minutes * 60000;
        }
        return time;
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
                "Photoshop's layers differ from the PSD Bridge read. Save the document in Photoshop, "
                + "reload it in Bridge and map again: "
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

    function selectLayer(layer) {
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putIdentifier(charIDToTypeID("Lyr "), Number(layer.id));
        descriptor.putReference(charIDToTypeID("null"), reference);
        descriptor.putBoolean(charIDToTypeID("MkVs"), false);
        executeAction(charIDToTypeID("slct"), descriptor, DialogModes.NO);
    }

    // Photoshop comes to the front while a Bridge script runs and covers the
    // progress Painter and the mapper show, so a user watching Photoshop took
    // a running insert for a finished one. This is the PSD builder's kind of
    // ScriptUI palette: no panel is open that could draw progress instead.
    // It can never be worth failing an insert, hence the silent catches.
    var progressWindow = null;
    var progressText = __RIZUM_PROGRESS_TEXT__;

    function progressLine(key, completed, total) {
        return String(progressText[key]).replace("{completed}", completed).replace("{total}", total);
    }

    function showProgress(status, fraction) {
        try {
            if (!progressWindow) {
                progressWindow = new Window("palette", "PT Bridge", undefined, {
                    closeButton: false, maximizeButton: false, minimizeButton: false
                });
                progressWindow.orientation = "column";
                progressWindow.alignChildren = ["fill", "top"];
                progressWindow.status = progressWindow.add("statictext", undefined, "");
                progressWindow.bar = progressWindow.add("progressbar", undefined, 0, 100);
                progressWindow.status.preferredSize = [400, 26];
                progressWindow.bar.preferredSize = [400, 14];
                try {
                    progressWindow.status.graphics.font = ScriptUI.newFont(progressText.font, "REGULAR", 15);
                } catch (ignored) {}
                progressWindow.center();
            }
            progressWindow.status.text = status;
            progressWindow.bar.value = Math.round(Math.max(0, Math.min(1, fraction || 0)) * 100);
            progressWindow.show();
            progressWindow.update();
        } catch (ignored) {}
    }

    function closeProgress() {
        try {
            if (progressWindow) progressWindow.close();
        } catch (ignored) {}
        progressWindow = null;
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
