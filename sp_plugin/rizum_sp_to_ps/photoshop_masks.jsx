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
