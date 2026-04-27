"use strict";

async function exportSelectedLayers(options = {}) {
  const mode = options.mode || "applied";
  const { app, core, imaging } = require("photoshop");
  const { storage } = require("uxp");
  const document = app.activeDocument;
  if (!document) {
    throw new Error("No active Photoshop document.");
  }

  const selectedLayers = Array.from(document.activeLayers || []);
  if (selectedLayers.length === 0) {
    throw new Error("Select at least one Photoshop layer to export.");
  }

  const folder = options.folder || await storage.localFileSystem.getFolder();
  if (!folder) {
    return {
      cancelled: true,
      message: "No export folder selected."
    };
  }

  const result = {
    cancelled: false,
    mode,
    folder: folder.nativePath || "(selected folder)",
    documentName: document.name || "(active document)",
    selectedCount: selectedLayers.length,
    exported: [],
    errors: []
  };

  await core.executeAsModal(
    async () => {
      for (let index = 0; index < selectedLayers.length; index += 1) {
        const layer = selectedLayers[index];
        try {
          await exportOneLayer(app, imaging, document, layer, folder, mode, index, result);
        } catch (error) {
          result.errors.push({
            layer: layer && layer.name ? layer.name : `Layer ${index + 1}`,
            error: error && error.message ? error.message : String(error)
          });
        }
      }
    },
    { commandName: "Rizum export selected layers" }
  );

  return result;
}

async function exportOneLayer(app, imaging, document, layer, folder, mode, index, result) {
  if (!layer || layer.id === undefined || layer.id === null) {
    throw new Error("Selected item has no layer id.");
  }

  const baseName = uniqueBaseName(layer.name || `Layer ${index + 1}`, index);
  if (mode === "separate") {
    let mask = await getLayerMaskIfPresent(imaging, document, layer);
    try {
      await exportLayerPixels(app, imaging, document, layer, folder, `${baseName}_layer.png`, {
        disableMask: Boolean(mask)
      });
      result.exported.push(`${baseName}_layer.png`);

      if (mask) {
        await exportMaskPixels(app, imaging, document, folder, `${baseName}_mask.png`, mask);
        mask = null;
        result.exported.push(`${baseName}_mask.png`);
      }
    } finally {
      disposePixels(mask);
    }
    return;
  }

  await exportLayerPixels(app, imaging, document, layer, folder, `${baseName}.png`, {
    disableMask: false
  });
  result.exported.push(`${baseName}.png`);
}

async function exportLayerPixels(app, imaging, document, layer, folder, filename, options = {}) {
  let originalMaskDensity = null;
  if (options.disableMask) {
    originalMaskDensity = await setMaskDensity(layer, 0);
  }

  let pixels = null;
  try {
    pixels = await getLayerPixels(imaging, document, layer);
    await savePixelsAsPng(app, imaging, document, folder, filename, pixels);
  } finally {
    if (originalMaskDensity !== null) {
      await setMaskDensity(layer, originalMaskDensity);
    }
    disposePixels(pixels);
  }
}

async function exportMaskPixels(app, imaging, document, folder, filename, maskPixels) {
  let rgbImageData = null;
  try {
    rgbImageData = await grayscalePixelsToRgb(imaging, maskPixels.imageData);
    await savePixelsAsPng(app, imaging, document, folder, filename, {
      imageData: rgbImageData,
      sourceBounds: maskPixels.sourceBounds
    });
  } finally {
    if (rgbImageData && typeof rgbImageData.dispose === "function") {
      rgbImageData.dispose();
    }
    disposePixels(maskPixels);
  }
}

async function getLayerPixels(imaging, document, layer) {
  const width = documentWidth(document);
  const height = documentHeight(document);
  try {
    return await imaging.getPixels({
      documentID: document.id,
      layerID: layer.id,
      sourceBounds: fullDocumentBounds(document),
      targetSize: {
        width,
        height
      },
      colorSpace: "RGB",
      componentSize: 8,
      applyAlpha: false
    });
  } catch (error) {
    if (isEmptyImageRegionError(error)) {
      return null;
    }
    throw error;
  }
}

async function getLayerMaskIfPresent(imaging, document, layer) {
  const width = documentWidth(document);
  const height = documentHeight(document);
  try {
    return await imaging.getLayerMask({
      documentID: document.id,
      layerID: layer.id,
      kind: "user",
      sourceBounds: fullDocumentBounds(document),
      targetSize: {
        width,
        height
      }
    });
  } catch (error) {
    return null;
  }
}

async function savePixelsAsPng(app, imaging, sourceDocument, folder, filename, pixels) {
  const fileEntry = await folder.createFile(filename, { overwrite: true });
  const tempDocument = await app.createDocument({
    name: filename.replace(/\.png$/i, ""),
    width: documentWidth(sourceDocument),
    height: documentHeight(sourceDocument),
    resolution: sourceDocument.resolution || 72,
    mode: "RGBColorMode",
    fill: "transparent"
  });

  try {
    if (pixels && pixels.imageData) {
      const targetLayer = firstLayer(tempDocument);
      if (!targetLayer || targetLayer.id === undefined || targetLayer.id === null) {
        throw new Error("Temporary PNG document has no writable layer.");
      }
      await imaging.putPixels({
        documentID: tempDocument.id,
        layerID: targetLayer.id,
        imageData: pixels.imageData,
        replace: true,
        targetBounds: {
          left: pixels.sourceBounds && pixels.sourceBounds.left || 0,
          top: pixels.sourceBounds && pixels.sourceBounds.top || 0
        }
      });
    }
    await tempDocument.saveAs.png(fileEntry, {}, true);
  } finally {
    await closeTemporaryDocument(tempDocument);
  }
}

async function grayscalePixelsToRgb(imaging, imageData) {
  if (!imageData || typeof imageData.getData !== "function") {
    throw new Error("Mask image data is not readable.");
  }

  const gray = await imageData.getData({ chunky: true });
  const rgb = new Uint8Array(imageData.width * imageData.height * 3);
  for (let source = 0, target = 0; source < gray.length; source += 1, target += 3) {
    const value = gray[source];
    rgb[target] = value;
    rgb[target + 1] = value;
    rgb[target + 2] = value;
  }

  return await imaging.createImageDataFromBuffer(rgb, {
    width: imageData.width,
    height: imageData.height,
    components: 3,
    chunky: true,
    colorProfile: "sRGB IEC61966-2.1",
    colorSpace: "RGB"
  });
}

async function setMaskDensity(layer, density) {
  try {
    const previous = layer.layerMaskDensity;
    layer.layerMaskDensity = density;
    return previous;
  } catch (error) {
    return null;
  }
}

function fullDocumentBounds(document) {
  return {
    left: 0,
    top: 0,
    width: documentWidth(document),
    height: documentHeight(document)
  };
}

function documentWidth(document) {
  return dimensionValue(document && document.width);
}

function documentHeight(document) {
  return dimensionValue(document && document.height);
}

function dimensionValue(value) {
  if (typeof value === "number") {
    return value;
  }
  if (value && typeof value.value === "number") {
    return value.value;
  }
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return numeric;
  }
  throw new Error(`Unsupported Photoshop document dimension: ${value}`);
}

function uniqueBaseName(name, index) {
  return `${String(index + 1).padStart(2, "0")}_${safeFileName(stripRizumSuffix(name))}`;
}

function stripRizumSuffix(name) {
  return String(name || "layer").replace(/\s\[rz:[0-9a-f]+\]$/i, "");
}

function safeFileName(name) {
  return String(name || "layer")
    .replace(/[<>:"/\\|?*\x00-\x1f]+/g, "_")
    .replace(/\s+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80) || "layer";
}

function isEmptyImageRegionError(error) {
  const message = error && error.message ? error.message : String(error);
  return message.toLowerCase().includes("invalid empty image region");
}

function disposePixels(pixels) {
  if (pixels && pixels.imageData && typeof pixels.imageData.dispose === "function") {
    pixels.imageData.dispose();
  }
}

function firstLayer(document) {
  return document && document.layers && document.layers.length > 0 ? document.layers[0] : null;
}

async function closeTemporaryDocument(document) {
  if (document && typeof document.closeWithoutSaving === "function") {
    await document.closeWithoutSaving();
    return;
  }
  if (document && typeof document.close === "function") {
    await document.close("no");
  }
}

module.exports = {
  exportSelectedLayers
};
