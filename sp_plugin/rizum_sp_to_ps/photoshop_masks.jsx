    // Layer-mask Action Manager steps shared by the PSD builder and the
    // mapped transfer. They are one copy because the transfer's own copy once
    // dropped MkVs: Photoshop pastes into a mask only while the mask is shown,
    // otherwise the paste lands as a new grayscale layer and the mask stays
    // white. Keep every mask step here so the two scripts cannot drift again.

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

    // Merges the selected layer's mask into its pixels, as Photoshop's Apply
    // Layer Mask does. The user prefers PSDs without layer masks; it is a
    // setting, off by default, because most workflows keep masks editable.
    // Photoshop applies no mask to a folder, so callers skip folders.
    function applySelectedLayerMask() {
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putEnumerated(
            charIDToTypeID("Chnl"),
            charIDToTypeID("Chnl"),
            charIDToTypeID("Msk ")
        );
        descriptor.putReference(charIDToTypeID("null"), reference);
        descriptor.putBoolean(charIDToTypeID("Aply"), true);
        executeAction(charIDToTypeID("Dlt "), descriptor, DialogModes.NO);
    }

    // Selecting a layer makes Photoshop open every folder above it, and the
    // mask steps cannot work without selecting, so folders the user keeps
    // folded came back open after a Bridge Apply. They are recorded before
    // the first mask step and folded again after the last, before the save
    // that stores the state; a folder the script added stays as it opens.
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

    // Merges the mask of every layer in the active document into its pixels,
    // folders excepted, once the document is rasterized. Each layer is
    // selected by its id: a placed layer's DOM handle went stale on the way
    // and the export failed with "Get is not currently available".
    function applyAllLayerMasks() {
        var folded = foldedFolders();
        var count = new ActionReference();
        count.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("numberOfLayers"));
        count.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var total = executeActionGet(count).getInteger(stringIDToTypeID("numberOfLayers"));
        var masked = [];
        for (var index = 1; index <= total; index += 1) {
            var reference = new ActionReference();
            reference.putIndex(charIDToTypeID("Lyr "), index);
            var layer = executeActionGet(reference);
            var hasMask = stringIDToTypeID("hasUserMask");
            if (typeIDToStringID(layer.getEnumerationValue(stringIDToTypeID("layerSection"))) === "layerSectionContent"
                    && layer.hasKey(hasMask) && layer.getBoolean(hasMask)) {
                masked.push(layer.getInteger(stringIDToTypeID("layerID")));
            }
        }
        for (var item = 0; item < masked.length; item += 1) {
            var target = new ActionReference();
            target.putIdentifier(charIDToTypeID("Lyr "), masked[item]);
            var select = new ActionDescriptor();
            select.putReference(charIDToTypeID("null"), target);
            select.putBoolean(charIDToTypeID("MkVs"), false);
            executeAction(charIDToTypeID("slct"), select, DialogModes.NO);
            applySelectedLayerMask();
        }
        foldAgain(folded);
    }

    // Copies a placed grayscale layer into targetLayer's new mask and removes
    // the placed layer; the caller places it where its script places PNGs.
    function pasteLayerAsMask(targetDocument, targetLayer, maskLayer) {
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
    }
