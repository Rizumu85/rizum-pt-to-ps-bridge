"use strict";

async function buildPsdFromRequest(options = {}) {
  const file = options.file || await pickBuildRequestFile();
  if (!file) {
    return {
      cancelled: true,
      message: "No build_request.json selected."
    };
  }

  const request = await readBuildRequestFile(file);
  validateBuildRequest(request);

  const result = {
    cancelled: false,
    fileName: file.name || "build_request.json",
    nativePath: file.nativePath || null,
    request,
    summary: summarizeBuildRequest(request)
  };

  if (options.createSkeleton) {
    result.build = await createPsdSkeletonFromRequest(request, options);
  }

  return result;
}

async function pickBuildRequestFile() {
  const { storage } = require("uxp");
  const fs = storage.localFileSystem;
  const file = await fs.getFileForOpening({
    types: ["json"],
    allowMultiple: false,
    mode: storage.modes.readOnly
  });
  return Array.isArray(file) ? file[0] : file;
}

async function readBuildRequestFile(file) {
  const text = await file.read();
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`Selected file is not valid JSON: ${error.message}`);
  }
}

function validateBuildRequest(request) {
  const required = [
    "schema_version",
    "request_type",
    "texture_set",
    "channel",
    "udim",
    "uv_tile",
    "layers",
    "asset_dir",
    "psd_file"
  ];
  const missing = required.filter((key) => !(key in request));
  if (missing.length > 0) {
    throw new Error(`build_request.json missing fields: ${missing.join(", ")}`);
  }
  if (request.schema_version !== 1) {
    throw new Error(`Unsupported schema_version: ${request.schema_version}`);
  }
  if (request.request_type !== "build") {
    throw new Error(`Expected request_type "build", got "${request.request_type}"`);
  }
  if (!Array.isArray(request.layers)) {
    throw new Error("build_request.json field layers must be an array");
  }
}

function summarizeBuildRequest(request) {
  const assets = collectAssets(request.layers);
  const unplacedNodes = collectUnplacedNodes(request);
  return {
    textureSet: request.texture_set,
    stack: request.stack || "",
    channel: request.channel,
    udim: request.udim,
    usesUdim: requestUsesUdim(request),
    resolution: request.uv_tile && request.uv_tile.resolution
      ? `${request.uv_tile.resolution.width}x${request.uv_tile.resolution.height}`
      : "unknown",
    psdFile: request.psd_file,
    topLevelLayers: request.layers.length,
    assetCount: assets.length,
    maskAssetCount: assets.filter((asset) => asset.kind === "mask").length,
    bakedAssetCount: assets.filter((asset) => asset.kind === "baked").length,
    unplacedNodeCount: unplacedNodes.length,
    unplacedMaskEffectCount: unplacedNodes.filter((node) => node.stack === "mask_effects").length,
    unplacedContentEffectCount: unplacedNodes.filter((node) => node.stack === "content_effects").length
  };
}

function collectAssets(nodes) {
  const assets = [];
  for (const node of nodes || []) {
    if (node.asset) {
      assets.push({
        kind: node.bake_policy === "bake" ? "baked" : "layer",
        asset: node.asset
      });
    }
    if (node.mask_asset) {
      assets.push({
        kind: "mask",
        asset: node.mask_asset
      });
    }
    assets.push(...collectAssets(node.children));
    assets.push(...collectAssets(node.content_effects));
  }
  return assets;
}

async function createPsdSkeletonFromRequest(request, options = {}) {
  const { app, core } = require("photoshop");
  const size = getRequestResolution(request);
  const documentName = makeDocumentName(request);
  const buildItems = topLevelBuildItems(request);
  const unplacedNodes = collectUnplacedNodes(request, buildItems);
  const build = {
    documentName,
    channel: request.channel,
    assetsExported: request.assets_exported !== false,
    width: size.width,
    height: size.height,
    resolution: getDocumentPpi(request),
    savePath: request.psd_file || null,
    topLevelAssetCount: countBuildItemRasterLayers(buildItems),
    topLevelMaskAssetCount: countBuildItemMasks(buildItems),
    topLevelGroupCount: buildItems.filter((item) => item.kind === "group").length,
    unplacedNodes,
    placedLayerCount: 0,
    placedLayers: [],
    placedGroups: [],
    sidecarPath: sidecarPathForPsd(request.psd_file),
    sidecarWritten: false,
    sidecarError: null,
    placementErrors: [],
    appliedMaskCount: 0,
    appliedMasks: [],
    maskErrors: [],
    baselineHashCount: 0,
    baselineHashErrors: [],
    removedResidualDefaultLayer: false,
    blendGammaAttempted: false,
    blendGammaSet: false,
    blendGammaError: "Skipped automatic rgbColorBlendGamma Set command because Photoshop can show a host modal error.",
    saved: false,
    saveError: null
  };

  await core.executeAsModal(async () => {
    const document = await app.createDocument({
      name: documentName,
      width: size.width,
      height: size.height,
      resolution: build.resolution,
      mode: "RGBColorMode",
      fill: "transparent"
    });

    build.documentId = document.id || null;

    if (options.placeTopLevelAssets) {
      await placeTopLevelBuildItems(app, document, buildItems, build);
      await removeResidualDefaultLayerIfSafe(document, build, buildItems);
    }

    if (options.attemptSave !== false && request.psd_file) {
      try {
        const fileEntry = await getFileEntryForPath(request.psd_file);
        await document.saveAs.psd(fileEntry);
        build.saved = true;
      } catch (error) {
        build.saveError = error && error.message ? error.message : String(error);
      }
    }
  }, {
    commandName: "Rizum Build Top-Level PNG Layers"
  });

  if (options.writeSidecar !== false && request.psd_file) {
    try {
      await attachBaselineHashes(build);
      await writeBuildSidecar(request, build);
      build.sidecarWritten = true;
    } catch (error) {
      build.sidecarError = error && error.message ? error.message : String(error);
    }
  }

  return build;
}

async function placeTopLevelBuildItems(app, targetDocument, items, build) {
  const topLevelPlacements = [];
  const rasters = items.filter((item) => item.kind === "raster");
  const groups = items.filter((item) => item.kind === "group");

  for (const item of [...rasters].reverse()) {
    try {
      const placed = await placeRasterNode(app, targetDocument, item.node, build.channel);
      const mask = await applyMaskAssetToPlacedLayer(
        app,
        targetDocument,
        placed,
        item.node,
        build,
        makeLayerName(item.node),
        item.order,
        item.sourceIndex
      );
      topLevelPlacements.push({
        item,
        layer: placed
      });
      build.placedLayers.push(placedLayerSummary(item, item.node, placed, build.channel, null, mask));
    } catch (error) {
      build.placementErrors.push({
        order: item.order,
        sourceIndex: item.sourceIndex,
        name: makeLayerName(item.node),
        path: item.node.asset && item.node.asset.path,
        error: error && error.message ? error.message : String(error)
      });
    }
  }

  for (const item of [...groups].reverse()) {
    try {
      await placeGroupNode(app, targetDocument, item, build, topLevelPlacements);
    } catch (error) {
      build.placementErrors.push({
        order: item.order,
        sourceIndex: item.sourceIndex,
        name: makeLayerName(item.node),
        path: item.node.asset && item.node.asset.path,
        error: error && error.message ? error.message : String(error)
      });
    }
  }

  build.placedLayers.sort((left, right) => left.order - right.order);
  build.placedGroups.sort((left, right) => left.order - right.order);
  build.placementErrors.sort((left, right) => left.order - right.order);
  build.maskErrors.sort((left, right) => left.order - right.order);
  build.placedLayerCount = build.placedLayers.length;
  build.appliedMaskCount = build.appliedMasks.length;
}

async function removeResidualDefaultLayerIfSafe(document, build, buildItems) {
  if (!document || !document.layers) {
    return;
  }

  const protectedTopLevelNames = requestedTopLevelNames(buildItems);
  for (const layer of Array.from(document.layers)) {
    if (!isDefaultEmptyLayer(layer) || protectedTopLevelNames.has(layer.name)) {
      continue;
    }

    try {
      await layer.delete();
      build.removedResidualDefaultLayer = true;
    } catch (error) {
      build.defaultLayerRemoveError = error && error.message ? error.message : String(error);
    }
    return;
  }
}

function requestedTopLevelNames(buildItems) {
  const names = new Set();
  for (const item of buildItems || []) {
    if (item && item.node) {
      names.add(makeLayerName(item.node));
    }
  }
  return names;
}

function isDefaultEmptyLayer(layer) {
  return layer
    && layer.name === "Layer 1"
    && layer.isBackgroundLayer !== true
    && (!layer.layers || layer.layers.length === 0);
}

async function placeGroupNode(app, targetDocument, item, build, topLevelPlacements) {
  const { constants } = require("photoshop");
  const groupName = makeLayerName(item.node);
  const taggedGroupName = makeTaggedLayerName(item.node);
  const options = {
    name: taggedGroupName
  };
  const opacity = layerOpacityPercent(item.node, build.channel);
  if (opacity !== null) {
    options.opacity = opacity;
  }
  const blendMode = layerBlendMode(item.node, build.channel, constants, {
    allowPassThrough: true
  });
  if (blendMode !== null) {
    options.blendMode = blendMode;
  }

  const group = await targetDocument.createLayerGroup(options);
  const reversedChildren = [...item.children].reverse();
  for (const childItem of reversedChildren) {
    try {
      const placed = await placeRasterNode(app, targetDocument, childItem.node, build.channel, group);
      const childName = `${groupName}/${makeLayerName(childItem.node)}`;
      const mask = await applyMaskAssetToPlacedLayer(
        app,
        targetDocument,
        placed,
        childItem.node,
        build,
        childName,
        childItem.order,
        item.sourceIndex
      );
      build.placedLayers.push(placedLayerSummary(childItem, childItem.node, placed, build.channel, groupName, mask));
    } catch (error) {
      build.placementErrors.push({
        order: childItem.order,
        sourceIndex: item.sourceIndex,
        name: `${groupName}/${makeLayerName(childItem.node)}`,
        path: childItem.node.asset && childItem.node.asset.path,
        error: error && error.message ? error.message : String(error)
      });
    }
  }

  group.name = taggedGroupName;
  group.visible = item.node.visible !== false;
  if (opacity !== null) {
    group.opacity = opacity;
  }
  if (blendMode !== null) {
    group.blendMode = blendMode;
  }
  const groupMask = await applyMaskAssetToPlacedLayer(
    app,
    targetDocument,
    group,
    item.node,
    build,
    groupName,
    item.order,
    item.sourceIndex
  );
  await moveGroupToTopLevelOrder(group, item, topLevelPlacements, constants);

  build.placedGroups.push({
    order: item.order,
    sourceIndex: item.sourceIndex,
    name: groupName,
    psName: group.name,
    spUid: nodeUidHex(item.node),
    spKind: nodeKind(item.node),
    blendMode: layerBlendModeName(item.node, build.channel),
    maskPath: groupMask && groupMask.path ? groupMask.path : null,
    maskApplied: groupMask ? groupMask.applied === true : false,
    childLayerCount: item.children.length
  });
}

async function moveGroupToTopLevelOrder(group, item, topLevelPlacements, constants) {
  const previous = nearestTopLevelPlacement(topLevelPlacements, item.sourceIndex, "previous");
  if (previous) {
    await group.move(previous.layer, constants.ElementPlacement.PLACEAFTER);
    return;
  }

  const next = nearestTopLevelPlacement(topLevelPlacements, item.sourceIndex, "next");
  if (next) {
    await group.move(next.layer, constants.ElementPlacement.PLACEBEFORE);
  }
}

function nearestTopLevelPlacement(placements, sourceIndex, direction) {
  const candidates = (placements || []).filter((placement) => (
    direction === "previous"
      ? placement.item.sourceIndex < sourceIndex
      : placement.item.sourceIndex > sourceIndex
  ));
  candidates.sort((left, right) => (
    direction === "previous"
      ? right.item.sourceIndex - left.item.sourceIndex
      : left.item.sourceIndex - right.item.sourceIndex
  ));
  return candidates[0] || null;
}

function placedLayerSummary(item, node, placed, channel, groupName, mask) {
  return {
    order: item.order,
    sourceIndex: item.sourceIndex,
    name: makeLayerName(node),
    psName: placed.name,
    groupName: groupName || null,
    spUid: nodeUidHex(node),
    spKind: nodeKind(node),
    blendMode: layerBlendModeName(node, channel),
    maskPath: mask && mask.path ? mask.path : null,
    maskApplied: mask ? mask.applied === true : false,
    path: node.asset.path
  };
}

async function placeRasterNode(app, targetDocument, node, channel, parentGroup) {
  const pngEntry = await getExistingFileEntryForPath(node.asset.path);
  const pngDocument = await app.open(pngEntry);

  try {
    const { constants } = require("photoshop");
    const sourceLayer = firstLayer(pngDocument);
    if (!sourceLayer) {
      throw new Error("Opened PNG document has no duplicateable layer");
    }

    const targetName = makeTaggedLayerName(node);
    const duplicated = await sourceLayer.duplicate(targetDocument, undefined, targetName);
    if (parentGroup) {
      await duplicated.move(parentGroup, constants.ElementPlacement.PLACEINSIDE);
    }
    duplicated.name = targetName;
    duplicated.visible = node.visible !== false;

    const opacity = layerOpacityPercent(node, channel);
    if (opacity !== null) {
      duplicated.opacity = opacity;
    }

    const blendMode = layerBlendMode(node, channel, constants);
    if (blendMode !== null) {
      duplicated.blendMode = blendMode;
    }

    return duplicated;
  } finally {
    await closeTemporaryDocument(pngDocument);
  }
}

async function applyMaskAssetToPlacedLayer(app, targetDocument, targetLayer, node, build, name, order, sourceIndex) {
  const maskAsset = node && node.mask_asset;
  if (!maskAsset || !maskAsset.path) {
    return null;
  }

  try {
    await putMaskPngOnLayer(app, targetDocument, targetLayer, maskAsset.path, build);
    const applied = {
      order,
      sourceIndex,
      name,
      path: maskAsset.path
    };
    build.appliedMasks.push(applied);
    return {
      path: maskAsset.path,
      applied: true
    };
  } catch (error) {
    build.maskErrors.push({
      order,
      sourceIndex,
      name,
      path: maskAsset.path,
      error: error && error.message ? error.message : String(error)
    });
    return {
      path: maskAsset.path,
      applied: false
    };
  }
}

async function putMaskPngOnLayer(app, targetDocument, targetLayer, path, build) {
  const { imaging } = require("photoshop");
  if (!targetLayer || targetLayer.id === undefined || targetLayer.id === null) {
    throw new Error("Target Photoshop layer has no layer id for mask placement");
  }
  if (!targetDocument || targetDocument.id === undefined || targetDocument.id === null) {
    throw new Error("Target Photoshop document has no document id for mask placement");
  }

  const maskEntry = await getExistingFileEntryForPath(path);
  const maskDocument = await app.open(maskEntry);
  let imageData = null;

  try {
    const maskLayer = firstLayer(maskDocument);
    if (!maskLayer || maskLayer.id === undefined || maskLayer.id === null) {
      throw new Error("Opened mask PNG document has no readable layer");
    }

    const pixels = await imaging.getPixels({
      documentID: maskDocument.id,
      layerID: maskLayer.id,
      sourceBounds: {
        left: 0,
        top: 0,
        width: build.width,
        height: build.height
      },
      targetSize: {
        width: build.width,
        height: build.height
      },
      colorSpace: "Grayscale",
      colorProfile: "Gray Gamma 2.2",
      componentSize: 8,
      applyAlpha: true
    });
    imageData = pixels.imageData;

    await imaging.putLayerMask({
      documentID: targetDocument.id,
      layerID: targetLayer.id,
      kind: "user",
      imageData,
      replace: true,
      targetBounds: {
        left: 0,
        top: 0
      }
    });
  } finally {
    if (imageData && typeof imageData.dispose === "function") {
      imageData.dispose();
    }
    await closeTemporaryDocument(maskDocument);
  }
}

async function writeBuildSidecar(request, build) {
  if (!build.sidecarPath) {
    throw new Error("No sidecar path could be derived from request.psd_file");
  }

  const fileEntry = await getFileEntryForPath(build.sidecarPath);
  await fileEntry.write(JSON.stringify(buildSidecarPayload(request, build), null, 2));
}

async function attachBaselineHashes(build) {
  build.baselineHashCount = 0;
  build.baselineHashErrors = [];

  for (const layer of build.placedLayers || []) {
    if (!layer.path) {
      continue;
    }
    try {
      layer.baselineHash = await sha1ImageAssetPixels(layer.path, layer.maskPath, {
        width: build.width,
        height: build.height
      });
      layer.baselineHashKind = "pixel_v1";
      build.baselineHashCount += 1;
    } catch (error) {
      build.baselineHashErrors.push({
        name: layer.psName || layer.name,
        path: layer.path,
        error: error && error.message ? error.message : String(error)
      });
    }
  }
}

async function sha1ImageAssetPixels(path, maskPath = null, size = {}) {
  const { core } = require("photoshop");
  return await core.executeAsModal(
    async () => sha1ImageAssetPixelsInModal(path, maskPath, size),
    { commandName: "Rizum hash source PNG" }
  );
}

async function sha1ImageAssetPixelsInModal(path, maskPath, size) {
  const { app } = require("photoshop");
  const { sha1LayerPixels } = loadPixelHashModule();
  const fileEntry = await getExistingFileEntryForPath(path);
  const imageDocument = await app.open(fileEntry);

  try {
    const layer = firstLayer(imageDocument);
    if (!layer) {
      throw new Error("Opened PNG document has no readable layer");
    }
    if (maskPath) {
      await putMaskPngOnLayer(app, imageDocument, layer, maskPath, {
        width: size.width || imageDocument.width,
        height: size.height || imageDocument.height
      });
    }
    return await sha1LayerPixels(imageDocument, layer);
  } finally {
    await closeTemporaryDocument(imageDocument);
  }
}

async function sha1File(path) {
  const { sha1ArrayBuffer } = loadSha1Module();
  const fileEntry = await getExistingFileEntryForPath(path);
  const buffer = await readFileAsArrayBuffer(fileEntry);
  return `sha1:${sha1ArrayBuffer(buffer)}`;
}

async function readFileAsArrayBuffer(fileEntry) {
  const { storage } = require("uxp");
  const formats = storage.formats || {};
  const attempts = [
    { format: formats.binary },
    { format: "binary" }
  ].filter((options) => options.format !== undefined && options.format !== null);
  const errors = [];

  for (const options of attempts) {
    try {
      const data = await fileEntry.read(options);
      if (data instanceof ArrayBuffer) {
        return data;
      }
      if (ArrayBuffer.isView(data)) {
        return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
      }
      errors.push(`read ${options.format}: returned ${typeof data}`);
    } catch (error) {
      errors.push(`read ${options.format}: ${error && error.message ? error.message : error}`);
    }
  }

  throw new Error(`Could not read file as binary for baseline hash: ${errors.join("; ")}`);
}

function loadSha1Module() {
  try {
    return require("./src/sha1.js");
  } catch (rootRelativeError) {
    return require("./sha1.js");
  }
}

function loadPixelHashModule() {
  try {
    return require("./src/pixel-hash.js");
  } catch (rootRelativeError) {
    return require("./pixel-hash.js");
  }
}

function buildSidecarPayload(request, build) {
  return {
    rizum_version: "0.1.47",
    schema_version: 1,
    created_at: new Date().toISOString(),
    build_request_file: request.build_request_file || null,
    psd_file: request.psd_file || null,
    texture_set: request.texture_set || "",
    stack: request.stack || "",
    channel: request.channel || "",
    channel_identifier: request.channel_identifier || null,
    udim: request.udim,
    uses_udim: requestUsesUdim(request),
    normal_map_format: request.normal_map_format || null,
    baseline_cache_key: request.baseline_cache_key || null,
    project: request.project || null,
    document: {
      name: build.documentName,
      width: build.width,
      height: build.height,
      resolution: build.resolution
    },
    layers: [
      ...build.placedGroups.map(sidecarGroupRecord),
      ...build.placedLayers.map(sidecarLayerRecord)
    ].sort((left, right) => left.order - right.order),
    unplaced_nodes: (build.unplacedNodes || []).map(sidecarUnplacedNodeRecord)
  };
}

function sidecarGroupRecord(group) {
  return {
    order: group.order,
    sp_uid: group.spUid,
    sp_kind: group.spKind,
    ps_kind: "group",
    ps_name: group.psName,
    display_name: group.name,
    group: null,
    sync_direction: "both",
    blend_mode: group.blendMode || null,
    mask_path: group.maskPath || null,
    baseline_hash: null,
    baseline_hash_kind: null
  };
}

function sidecarLayerRecord(layer) {
  return {
    order: layer.order,
    sp_uid: layer.spUid,
    sp_kind: layer.spKind,
    ps_kind: "layer",
    ps_name: layer.psName,
    display_name: layer.name,
    group: layer.groupName || null,
    sync_direction: "both",
    blend_mode: layer.blendMode || null,
    asset_path: layer.path || null,
    mask_path: layer.maskPath || null,
    baseline_hash: layer.baselineHash || null,
    baseline_hash_kind: layer.baselineHashKind || null
  };
}

function sidecarUnplacedNodeRecord(node) {
  return {
    order: node.order,
    sp_uid: node.spUid,
    sp_kind: node.spKind,
    display_name: node.name,
    request_path: node.path,
    stack: node.stack,
    parent: node.parent || null,
    reason: node.reason,
    sync_direction: node.syncDirection,
    bake_policy: node.bakePolicy || null
  };
}

function topLevelRasterNodes(request) {
  return topLevelBuildItems(request)
    .filter((item) => item.kind === "raster");
}

function topLevelBuildItems(request) {
  return (request.layers || [])
    .map((node, sourceIndex) => ({
      kind: topLevelItemKind(node),
      node,
      sourceIndex,
      order: sourceIndex * 1000,
      children: directRasterChildItems(node, sourceIndex)
    }))
    .filter((item) => item.kind !== null);
}

function topLevelItemKind(node) {
  if (!node) {
    return null;
  }
  if (node.asset && node.asset.path) {
    return "raster";
  }
  if (isGroupNode(node) && directRasterChildItems(node, 0).length > 0) {
    return "group";
  }
  return null;
}

function directRasterChildItems(node, sourceIndex) {
  if (!isGroupNode(node)) {
    return [];
  }
  return (node.children || [])
    .map((child, childIndex) => ({
      kind: "raster",
      node: child,
      sourceIndex,
      childIndex,
      order: sourceIndex * 1000 + childIndex + 1
    }))
    .filter((item) => item.node && item.node.asset && item.node.asset.path);
}

function collectUnplacedNodes(request, buildItems = topLevelBuildItems(request)) {
  const placedUids = new Set();
  for (const item of buildItems || []) {
    addPlacedUid(placedUids, item.node);
    for (const child of item.children || []) {
      addPlacedUid(placedUids, child.node);
    }
  }

  const records = [];
  let order = 0;
  for (const node of request.layers || []) {
    visitUnplacedNode(node, {
      stack: "layers",
      parent: null,
      path: makeLayerName(node),
      placedUids,
      records,
      nextOrder: () => order++
    });
  }
  return records;
}

function visitUnplacedNode(node, context) {
  if (!node) {
    return;
  }

  const uid = nodeUidHex(node);
  if (uid && !context.placedUids.has(uid) && shouldRecordUnplacedNode(node, context.stack)) {
    context.records.push({
      order: context.nextOrder(),
      spUid: uid,
      spKind: nodeKind(node),
      name: makeLayerName(node),
      path: context.path,
      stack: context.stack,
      parent: context.parent,
      reason: unplacedNodeReason(node, context.stack),
      syncDirection: unplacedNodeSyncDirection(node, context.stack),
      bakePolicy: node.bake_policy || null
    });
  }

  for (const child of node.children || []) {
    visitUnplacedNode(child, {
      ...context,
      stack: "children",
      parent: context.path,
      path: `${context.path}/${makeLayerName(child)}`
    });
  }
  for (const effect of node.content_effects || []) {
    visitUnplacedNode(effect, {
      ...context,
      stack: "content_effects",
      parent: context.path,
      path: `${context.path}#content/${makeLayerName(effect)}`
    });
  }
  for (const effect of node.mask_effects || []) {
    visitUnplacedNode(effect, {
      ...context,
      stack: "mask_effects",
      parent: context.path,
      path: `${context.path}#mask/${makeLayerName(effect)}`
    });
  }
}

function addPlacedUid(placedUids, node) {
  const uid = nodeUidHex(node);
  if (uid) {
    placedUids.add(uid);
  }
}

function shouldRecordUnplacedNode(node, stack) {
  if (stack === "content_effects" || stack === "mask_effects") {
    return true;
  }
  if (node.asset && node.asset.path) {
    return true;
  }
  if (node.mask_asset && node.mask_asset.path) {
    return true;
  }
  return false;
}

function unplacedNodeReason(node, stack) {
  if (stack === "mask_effects") {
    return "baked_into_parent_mask";
  }
  if (stack === "content_effects") {
    return node.asset && node.asset.path ? "content_effect_asset_not_placed" : "content_effect_metadata_only";
  }
  if (node.asset && node.asset.path) {
    return "nested_asset_not_placed";
  }
  if (node.mask_asset && node.mask_asset.path) {
    return "mask_asset_not_placed";
  }
  return "metadata_only";
}

function unplacedNodeSyncDirection(node, stack) {
  if (stack === "mask_effects") {
    return "sp_to_ps_only";
  }
  if (stack === "content_effects" && node.asset && node.asset.path) {
    return "sp_to_ps_only";
  }
  if (node.asset && node.asset.path) {
    return "sp_to_ps_only";
  }
  if (node.mask_asset && node.mask_asset.path) {
    return "sp_to_ps_only";
  }
  return "none";
}

function countBuildItemRasterLayers(items) {
  return (items || []).reduce((total, item) => {
    if (item.kind === "group") {
      return total + item.children.length;
    }
    return total + 1;
  }, 0);
}

function countBuildItemMasks(items) {
  return (items || []).reduce((total, item) => {
    let count = item.node && item.node.mask_asset && item.node.mask_asset.path ? 1 : 0;
    if (item.kind === "group") {
      count += (item.children || []).filter((child) => (
        child.node && child.node.mask_asset && child.node.mask_asset.path
      )).length;
    }
    return total + count;
  }, 0);
}

function isGroupNode(node) {
  return node && String(node.kind || "").toLowerCase().includes("group");
}

function firstLayer(document) {
  return document && document.layers && document.layers.length > 0
    ? document.layers[0]
    : null;
}

async function closeTemporaryDocument(document) {
  if (document && typeof document.closeWithoutSaving === "function") {
    await document.closeWithoutSaving();
    return;
  }

  if (document && typeof document.close === "function") {
    const { constants } = require("photoshop");
    await document.close(constants.SaveOptions.DONOTSAVECHANGES);
  }
}

function makeLayerName(node) {
  const name = node && node.name !== undefined && node.name !== null
    ? String(node.name).trim()
    : "";
  return name || `Layer ${node && node.uid_hex ? node.uid_hex : "unknown"}`;
}

function makeTaggedLayerName(node) {
  const uid = nodeUidHex(node);
  const name = makeLayerName(node);
  return uid ? `${name} [rz:${uid}]` : name;
}

function nodeUidHex(node) {
  const uid = node && node.uid_hex !== undefined && node.uid_hex !== null
    ? String(node.uid_hex).trim().toLowerCase()
    : "";
  return uid || null;
}

function nodeKind(node) {
  return node && node.kind !== undefined && node.kind !== null
    ? String(node.kind)
    : "unknown";
}

function layerOpacityPercent(node, channel) {
  const opacity = node && node.opacity;
  if (opacity === undefined || opacity === null) {
    return null;
  }

  let raw = null;
  if (typeof opacity === "number") {
    raw = opacity;
  } else if (typeof opacity === "object") {
    if (channel && opacity[channel] !== undefined) {
      raw = opacity[channel];
    } else if (opacity.mask !== undefined) {
      raw = opacity.mask;
    } else {
      raw = firstNumericValue(opacity);
    }
  }

  const value = Number(raw);
  if (!Number.isFinite(value)) {
    return null;
  }
  const percent = value >= 0 && value <= 1 ? value * 100 : value;
  return Math.max(0, Math.min(100, percent));
}

function layerBlendMode(node, channel, constants, options = {}) {
  const modeName = layerBlendModeName(node, channel);
  if (modeName === null || (modeName === "PASSTHROUGH" && !options.allowPassThrough)) {
    return null;
  }

  const blendModes = constants && constants.BlendMode ? constants.BlendMode : {};
  return blendModes[modeName] || modeName;
}

function layerBlendModeName(node, channel) {
  const decision = channelDecision(node, channel);
  if (decision && decision.ps_blend_mode) {
    return normalizeBlendModeName(decision.ps_blend_mode);
  }

  if (node && node.ps_blend_mode) {
    return normalizeBlendModeName(node.ps_blend_mode);
  }

  const painterMode = channelValue(node && node.blend_mode, channel);
  if (painterMode) {
    return painterBlendModeToPhotoshop(painterMode);
  }

  return null;
}

function channelDecision(node, channel) {
  if (!node || !node.blend_decisions || typeof node.blend_decisions !== "object") {
    return null;
  }
  if (channel && node.blend_decisions[channel]) {
    return node.blend_decisions[channel];
  }
  return null;
}

function channelValue(values, channel) {
  if (values === undefined || values === null) {
    return null;
  }
  if (typeof values !== "object") {
    return values;
  }
  if (channel && values[channel] !== undefined) {
    return values[channel];
  }
  return null;
}

function normalizeBlendModeName(value) {
  const mode = String(value || "").trim();
  return mode ? mode.toUpperCase() : null;
}

function painterBlendModeToPhotoshop(value) {
  return PAINTER_TO_PHOTOSHOP_BLEND_MODE[String(value || "").trim()] || null;
}

const PAINTER_TO_PHOTOSHOP_BLEND_MODE = {
  Normal: "NORMAL",
  Replace: "NORMAL",
  PassThrough: "PASSTHROUGH",
  Multiply: "MULTIPLY",
  Screen: "SCREEN",
  Overlay: "OVERLAY",
  Darken: "DARKEN",
  Lighten: "LIGHTEN",
  LinearDodge: "LINEARDODGE",
  LinearBurn: "LINEARBURN",
  ColorBurn: "COLORBURN",
  ColorDodge: "COLORDODGE",
  SoftLight: "SOFTLIGHT",
  HardLight: "HARDLIGHT",
  VividLight: "VIVIDLIGHT",
  LinearLight: "LINEARLIGHT",
  PinLight: "PINLIGHT",
  Difference: "DIFFERENCE",
  Exclusion: "EXCLUSION",
  Subtract: "SUBTRACT",
  Divide: "DIVIDE",
  Tint: "HUE",
  Saturation: "SATURATION",
  Color: "COLOR",
  Value: "LUMINOSITY",
  SignedAddition: "LINEARDODGE",
  InverseDivide: "DIVIDE",
  InverseSubtract: "SUBTRACT"
};

function firstNumericValue(values) {
  for (const value of Object.values(values || {})) {
    if (Number.isFinite(Number(value))) {
      return value;
    }
  }
  return null;
}

function getRequestResolution(request) {
  const resolution = request.uv_tile && request.uv_tile.resolution;
  const width = resolution && Number(resolution.width);
  const height = resolution && Number(resolution.height);

  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error("build_request.json must include a positive uv_tile.resolution width and height");
  }

  return {
    width: Math.round(width),
    height: Math.round(height)
  };
}

function getDocumentPpi(request) {
  const ppi = request.export_settings && Number(request.export_settings.ppi);
  return Number.isFinite(ppi) && ppi > 0 ? ppi : 72;
}

function makeDocumentName(request) {
  const psdName = basename(request.psd_file || "");
  if (psdName) {
    return stripExtension(psdName);
  }

  const pieces = [request.texture_set, request.stack, request.channel]
    .filter((piece) => piece !== undefined && piece !== null && String(piece).length > 0);
  if (requestUsesUdim(request)) {
    pieces.push(request.udim);
  }
  return pieces.length > 0 ? pieces.join("_") : "Rizum Painter Build";
}

function requestUsesUdim(request) {
  return !(request.uv_tile && request.uv_tile.is_udim === false);
}

function basename(path) {
  const parts = String(path || "").split(/[\\/]/);
  return parts[parts.length - 1] || "";
}

function stripExtension(name) {
  return String(name).replace(/\.[^.]*$/, "");
}

function sidecarPathForPsd(path) {
  const text = String(path || "");
  if (!text) {
    return null;
  }
  return text.replace(/\.[^.\\/]*$/, "") + ".rizum.json";
}

async function getFileEntryForPath(path) {
  const { storage } = require("uxp");
  const fs = storage.localFileSystem;
  if (!fs.createEntryWithUrl && !fs.getEntryWithUrl) {
    throw new Error("This UXP runtime exposes neither localFileSystem.createEntryWithUrl nor getEntryWithUrl");
  }

  const errors = [];
  for (const url of fileUrlCandidates(path)) {
    if (fs.createEntryWithUrl) {
      try {
        return await fs.createEntryWithUrl(url, {
          overwrite: true
        });
      } catch (error) {
        errors.push(`create ${url}: ${error && error.message ? error.message : error}`);
      }
    }

    if (!fs.getEntryWithUrl) {
      continue;
    }

    try {
      return await fs.getEntryWithUrl(url);
    } catch (error) {
      errors.push(`get ${url}: ${error && error.message ? error.message : error}`);
    }
  }
  throw new Error(`Could not resolve PSD output path through UXP: ${errors.join("; ")}`);
}

async function getExistingFileEntryForPath(path) {
  const { storage } = require("uxp");
  const fs = storage.localFileSystem;
  if (!fs.getEntryWithUrl) {
    throw new Error("This UXP runtime does not expose localFileSystem.getEntryWithUrl");
  }

  for (const url of fileUrlCandidates(path)) {
    try {
      return await fs.getEntryWithUrl(url);
    } catch (error) {
      // Try the next URL shape. Photoshop accepts different file URL forms
      // across hosts, but the user-facing error should stay concise.
    }
  }
  throw new Error(`PNG asset not found: ${path}`);
}

function fileUrlCandidates(path) {
  const normalized = String(path || "").replace(/\\/g, "/");
  const encoded = encodeURI(normalized);
  if (/^[A-Za-z]:\//.test(normalized)) {
    return [`file:/${encoded}`, `file:///${encoded}`];
  }
  if (normalized.startsWith("/")) {
    return [`file://${encoded}`];
  }
  return [`file:${encoded}`];
}

module.exports = {
  buildPsdFromRequest,
  collectAssets,
  collectUnplacedNodes,
  buildSidecarPayload,
  createPsdSkeletonFromRequest,
  fileUrlCandidates,
  getRequestResolution,
  countBuildItemRasterLayers,
  isDefaultEmptyLayer,
  layerBlendMode,
  layerBlendModeName,
  layerOpacityPercent,
  makeDocumentName,
  makeLayerName,
  makeTaggedLayerName,
  requestUsesUdim,
  readBuildRequestFile,
  sha1File,
  sidecarPathForPsd,
  summarizeBuildRequest,
  topLevelBuildItems,
  topLevelRasterNodes,
  validateBuildRequest
};
