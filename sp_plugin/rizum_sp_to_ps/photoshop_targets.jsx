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
