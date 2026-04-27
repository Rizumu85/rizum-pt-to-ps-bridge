"use strict";

function loadSha1Module() {
  try {
    return require("./src/sha1.js");
  } catch (rootRelativeError) {
    return require("./sha1.js");
  }
}

async function sha1LayerPixels(document, layer, options = {}) {
  const { imaging } = require("photoshop");
  if (!document || document.id === undefined || document.id === null) {
    throw new Error("Photoshop document has no id for pixel hashing");
  }
  if (!layer || layer.id === undefined || layer.id === null) {
    throw new Error("Photoshop layer has no id for pixel hashing");
  }

  const getPixelsOptions = {
    documentID: document.id,
    layerID: layer.id,
    colorSpace: "RGB",
    componentSize: 8,
    applyAlpha: false
  };
  if (options.sourceBounds) {
    getPixelsOptions.sourceBounds = options.sourceBounds;
  }

  let pixels;
  try {
    pixels = await imaging.getPixels(getPixelsOptions);
  } catch (error) {
    if (isEmptyImageRegionError(error)) {
      return sha1EmptyPixels();
    }
    throw error;
  }

  try {
    return await sha1ImageData(pixels.imageData, pixels.sourceBounds);
  } finally {
    if (pixels.imageData && typeof pixels.imageData.dispose === "function") {
      pixels.imageData.dispose();
    }
  }
}

function sha1EmptyPixels() {
  const { createSha1 } = loadSha1Module();
  const hasher = createSha1();
  hasher.update(asciiBytes("rizum-empty-pixel-v1\n"));
  return `sha1:${hasher.digest()}`;
}

function isEmptyImageRegionError(error) {
  const message = error && error.message ? error.message : String(error);
  return message.toLowerCase().includes("invalid empty image region");
}

async function sha1ImageData(imageData, sourceBounds) {
  if (!imageData || typeof imageData.getData !== "function") {
    throw new Error("Photoshop image data is not readable");
  }

  const { createSha1 } = loadSha1Module();
  const data = await imageData.getData({ chunky: true });
  const hasher = createSha1();
  hasher.update(asciiBytes(imageDataHeader(imageData, sourceBounds)));
  hasher.update(data);
  return `sha1:${hasher.digest()}`;
}

function imageDataHeader(imageData, sourceBounds) {
  return [
    "rizum-pixel-v1",
    `width=${imageData.width || 0}`,
    `height=${imageData.height || 0}`,
    `components=${imageData.components || 0}`,
    `componentSize=${imageData.componentSize || 0}`,
    `pixelFormat=${imageData.pixelFormat || ""}`,
    `colorSpace=${imageData.colorSpace || ""}`,
    `hasAlpha=${imageData.hasAlpha ? "1" : "0"}`,
    `bounds=${boundsKey(sourceBounds)}`
  ].join(";") + "\n";
}

function boundsKey(bounds) {
  if (!bounds) {
    return "";
  }
  return [
    bounds.left || 0,
    bounds.top || 0,
    bounds.right || "",
    bounds.bottom || "",
    bounds.width || "",
    bounds.height || ""
  ].join(",");
}

function asciiBytes(text) {
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i += 1) {
    bytes[i] = text.charCodeAt(i) & 0x7f;
  }
  return bytes;
}

module.exports = {
  sha1ImageData,
  sha1LayerPixels,
  sha1EmptyPixels
};
