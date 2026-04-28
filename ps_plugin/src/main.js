"use strict";

const { entrypoints } = require("uxp");

const PLUGIN_VERSION = "0.1.59";

console.log(`[Rizum] main.js loaded ${PLUGIN_VERSION}`);
scheduleStartupRender();

entrypoints.setup({
  plugin: {
    create() {
      console.log(`[Rizum] plugin.create ${PLUGIN_VERSION}`);
      renderIntoDocumentBody("plugin.create");
    },
    destroy() {
      console.log(`[Rizum] plugin.destroy ${PLUGIN_VERSION}`);
    }
  },
  commands: {
    rizumDiagnostics() {
      console.log(`[Rizum] command.rizumDiagnostics ${PLUGIN_VERSION}`);
      renderIntoDocumentBody("command");
      window.alert(`Rizum PT Bridge ${PLUGIN_VERSION}: plugin JavaScript executed.`);
    }
  },
  panels: {
    rizumBridge: {
      create(rootNode) {
        console.log("[Rizum] panel.create", describeNode(rootNode));
        renderDiagnosticPanel(rootNode, "panel.create");
      },
      show(rootNode, data) {
        console.log("[Rizum] panel.show", describeNode(rootNode), JSON.stringify(data || {}));
        renderDiagnosticPanel(rootNode, "panel.show");
      },
      hide(rootNode) {
        console.log("[Rizum] panel.hide", describeNode(rootNode));
      },
      destroy(rootNode) {
        console.log("[Rizum] panel.destroy", describeNode(rootNode));
      }
    }
  }
});

function scheduleStartupRender() {
  if (document.body) {
    setTimeout(() => renderIntoDocumentBody("startup"), 0);
    return;
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderIntoDocumentBody("DOMContentLoaded");
  });
}

function renderIntoDocumentBody(phase) {
  if (!document.body) {
    console.log("[Rizum] document.body render skipped: no body");
    return;
  }
  renderDiagnosticPanel(document.body, phase);
}

function describeNode(node) {
  if (!node) {
    return "no root node";
  }
  const count = node.childNodes ? node.childNodes.length : "unknown";
  return `${node.nodeName || "node"} children=${count}`;
}

function renderDiagnosticPanel(rootNode, phase) {
  if (!rootNode) {
    console.log("[Rizum] render skipped: no root node");
    return;
  }

  const oldPanel = rootNode.querySelector ? rootNode.querySelector("#rizum-bridge-panel") : null;
  if (oldPanel) {
    oldPanel.remove();
  }

  const panel = document.createElement("div");
  panel.id = "rizum-bridge-panel";
  setStyles(panel, {
    boxSizing: "border-box",
    display: "block",
    minHeight: "520px",
    maxHeight: "calc(100vh - 12px)",
    width: "100%",
    padding: "10px",
    margin: "0",
    border: "3px solid #0057d8",
    background: "#ffffff",
    color: "#111111",
    fontFamily: "Arial, sans-serif",
    fontSize: "13px",
    lineHeight: "1.35",
    overflow: "auto"
  });

  const heading = document.createElement("h3");
  heading.textContent = "Rizum PT Bridge";
  setStyles(heading, {
    margin: "0 0 10px",
    color: "#111111",
    fontSize: "16px",
    fontWeight: "700"
  });

  const status = document.createElement("p");
  status.textContent = `Top-level raster build ${PLUGIN_VERSION} rendered through ${phase}.`;
  setStyles(status, {
    margin: "0 0 10px",
    color: "#111111"
  });

  const buildButton = makeButton("Build from Painter");
  const pathInput = document.createElement("input");
  pathInput.type = "text";
  pathInput.placeholder = "Paste build_request.json path";
  setStyles(pathInput, {
    boxSizing: "border-box",
    width: "100%",
    minHeight: "30px",
    margin: "0 0 8px",
    padding: "5px 7px",
    border: "1px solid #777777",
    background: "#ffffff",
    color: "#111111",
    fontSize: "12px"
  });
  const pastePathButton = makeButton("Paste Request Path");
  const buildPathButton = makeButton("Build Request Path");
  const buildFolderButton = makeButton("Build Request Folder");
  const buildListButton = makeButton("Build Export List");
  const exportAppliedButton = makeButton("Export Selected (Applied Mask)");
  const exportSeparateButton = makeButton("Export Selected + Masks");
  const copyButton = makeButton("Copy Details");

  const details = document.createElement("textarea");
  details.readOnly = true;
  details.spellcheck = false;
  setDetailsText(details, [
    "Choose a Painter build_request.json.",
    `Root: ${describeNode(rootNode)}`,
    `Phase: ${phase}`,
    "Build creates a PSD from Painter. Export Selected writes chosen Photoshop layers as PNGs for manual Painter import."
  ].join("\n"));
  setStyles(details, {
    boxSizing: "border-box",
    minHeight: "90px",
    maxHeight: "360px",
    width: "100%",
    margin: "2px 0 0",
    padding: "8px",
    border: "1px solid #777777",
    resize: "vertical",
    background: "#ffffff",
    color: "#111111",
    whiteSpace: "pre-wrap",
    overflow: "auto",
    wordBreak: "break-word",
    fontFamily: "Consolas, monospace",
    fontSize: "12px"
  });

  panel.appendChild(heading);
  panel.appendChild(status);
  panel.appendChild(buildButton);
  panel.appendChild(pathInput);
  panel.appendChild(pastePathButton);
  panel.appendChild(buildPathButton);
  panel.appendChild(buildFolderButton);
  panel.appendChild(buildListButton);
  panel.appendChild(exportAppliedButton);
  panel.appendChild(exportSeparateButton);
  panel.appendChild(copyButton);
  panel.appendChild(details);
  rootNode.appendChild(panel);

  buildButton.addEventListener("click", () => {
    handleBuildFromPainter(buildButton, details);
  });
  pastePathButton.addEventListener("click", () => {
    handlePasteRequestPath(pastePathButton, details, pathInput);
  });
  buildPathButton.addEventListener("click", () => {
    handleBuildRequestPath(buildPathButton, details, pathInput);
  });
  buildFolderButton.addEventListener("click", () => {
    handleBuildRequestFolder(buildFolderButton, details);
  });
  buildListButton.addEventListener("click", () => {
    handleBuildExportList(buildListButton, details);
  });
  exportAppliedButton.addEventListener("click", () => {
    handleExportSelected(exportAppliedButton, details, "applied");
  });
  exportSeparateButton.addEventListener("click", () => {
    handleExportSelected(exportSeparateButton, details, "separate");
  });
  copyButton.addEventListener("click", () => {
    handleCopyDetails(copyButton, details);
  });

  console.log("[Rizum] panel rendered plain HTML", describeNode(rootNode));
}

async function handlePasteRequestPath(button, details, pathInput) {
  console.log(`[Rizum] Paste request path clicked ${PLUGIN_VERSION}`);
  const originalLabel = button.textContent;
  button.disabled = true;

  try {
    if (!navigator.clipboard || !navigator.clipboard.readText) {
      throw new Error("navigator.clipboard.readText is not available");
    }
    const clipboardValue = await navigator.clipboard.readText();
    const text = normalizeClipboardText(clipboardValue).trim();
    if (!text) {
      setDetailsText(details, "Clipboard did not contain text. Use Ctrl+V in the path field instead.");
      button.textContent = "No Text";
      return;
    }
    pathInput.value = text;
    setDetailsText(details, "Pasted build_request.json path.\n\nClick Build Request Path to create the PSD.");
    button.textContent = "Pasted";
  } catch (error) {
    console.log("[Rizum] Paste request path failed", error && error.stack ? error.stack : error);
    setDetailsText(details, `Could not read clipboard text:\n${error.message || error}\n\nUse Ctrl+V in the path field instead.`);
    button.textContent = "Paste Failed";
  } finally {
    button.disabled = false;
    setTimeout(() => {
      button.textContent = originalLabel;
    }, 1600);
  }
}

async function handleBuildRequestPath(button, details, pathInput) {
  console.log(`[Rizum] Build request path clicked ${PLUGIN_VERSION}`);
  button.disabled = true;
  const path = pathInput && pathInput.value ? pathInput.value.trim() : "";
  setDetailsText(details, "Resolving pasted build_request.json path...");

  try {
    const { buildPsdFromPath } = loadBuildPsdModule();
    const result = await buildPsdFromPath(path, {
      createSkeleton: true,
      placeTopLevelAssets: true
    });
    setDetailsText(details, formatRequestSummary(result));
  } catch (error) {
    console.log("[Rizum] Build request path failed", error && error.stack ? error.stack : error);
    setDetailsText(details, `Could not build pasted build_request.json path:\n${error.message || error}`);
  } finally {
    button.disabled = false;
  }
}

async function handleBuildRequestFolder(button, details) {
  console.log(`[Rizum] Build request folder clicked ${PLUGIN_VERSION}`);
  button.disabled = true;
  setDetailsText(details, "Choose a folder containing build_request.json files...");

  try {
    const { buildPsdFromFolder } = loadBuildPsdModule();
    const result = await buildPsdFromFolder({
      createSkeleton: true,
      placeTopLevelAssets: true,
      closeAfterSave: true
    });
    if (result.cancelled) {
      setDetailsText(details, result.message);
      return;
    }
    setDetailsText(details, formatFolderBuildSummary(result));
  } catch (error) {
    console.log("[Rizum] Build request folder failed", error && error.stack ? error.stack : error);
    setDetailsText(details, `Could not build request folder:\n${error.message || error}`);
  } finally {
    button.disabled = false;
  }
}

async function handleBuildExportList(button, details) {
  console.log(`[Rizum] Build export list clicked ${PLUGIN_VERSION}`);
  button.disabled = true;
  setDetailsText(details, "Choose _last_export.json from Painter...");

  try {
    const { buildPsdFromExportList } = loadBuildPsdModule();
    const result = await buildPsdFromExportList({
      createSkeleton: true,
      placeTopLevelAssets: true,
      closeAfterSave: false
    });
    if (result.cancelled) {
      setDetailsText(details, result.message);
      return;
    }
    setDetailsText(details, formatExportListBuildSummary(result));
  } catch (error) {
    console.log("[Rizum] Build export list failed", error && error.stack ? error.stack : error);
    setDetailsText(details, `Could not build Painter export list:\n${error.message || error}`);
  } finally {
    button.disabled = false;
  }
}

async function handleBuildFromPainter(button, details) {
  console.log(`[Rizum] Build from Painter clicked ${PLUGIN_VERSION}`);
  button.disabled = true;
  setDetailsText(details, "Opening file picker...");

  try {
    const { buildPsdFromRequest } = loadBuildPsdModule();
    const result = await buildPsdFromRequest({
      createSkeleton: true,
      placeTopLevelAssets: true
    });
    if (result.cancelled) {
      setDetailsText(details, result.message);
      return;
    }
    setDetailsText(details, formatRequestSummary(result));
  } catch (error) {
    console.log("[Rizum] Build request validation failed", error && error.stack ? error.stack : error);
    setDetailsText(details, `Could not validate build_request.json:\n${error.message || error}`);
  } finally {
    button.disabled = false;
  }
}

async function handleExportSelected(button, details, mode) {
  console.log(`[Rizum] Export selected clicked ${PLUGIN_VERSION} ${mode}`);
  button.disabled = true;
  setDetailsText(details, "Choose an export folder...");

  try {
    const { exportSelectedLayers } = loadExportSelectedModule();
    const result = await exportSelectedLayers({ mode });
    if (result.cancelled) {
      setDetailsText(details, result.message);
      return;
    }
    setDetailsText(details, formatExportSelectedSummary(result));
  } catch (error) {
    console.log("[Rizum] Export selected failed", error && error.stack ? error.stack : error);
    setDetailsText(details, `Could not export selected layers:\n${error.message || error}`);
  } finally {
    button.disabled = false;
  }
}

async function handleCopyDetails(button, details) {
  const originalLabel = button.textContent;
  const text = getDetailsText(details);
  if (!text) {
    button.textContent = "Nothing to Copy";
    setTimeout(() => {
      button.textContent = originalLabel;
    }, 1200);
    return;
  }

  try {
    if (!navigator.clipboard || !navigator.clipboard.setContent) {
      throw new Error("navigator.clipboard.setContent is not available");
    }
    await navigator.clipboard.setContent({
      "text/plain": text
    });
    button.textContent = "Copied";
  } catch (error) {
    console.log("[Rizum] Copy Details failed", error && error.stack ? error.stack : error);
    selectDetails(details);
    button.textContent = "Select + Ctrl+C";
  }

  setTimeout(() => {
    button.textContent = originalLabel;
  }, 1600);
}

function normalizeClipboardText(value) {
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value === "object") {
    return value["text/plain"] || value.text || "";
  }
  return "";
}

function loadBuildPsdModule() {
  try {
    return require("./src/build-psd.js");
  } catch (rootRelativeError) {
    console.log("[Rizum] root-relative build-psd require failed", rootRelativeError.message || rootRelativeError);
    return require("./build-psd.js");
  }
}

function loadExportSelectedModule() {
  try {
    return require("./src/export-selected.js");
  } catch (rootRelativeError) {
    console.log("[Rizum] root-relative export-selected require failed", rootRelativeError.message || rootRelativeError);
    return require("./export-selected.js");
  }
}

function formatFolderBuildSummary(result) {
  return formatBatchBuildSummary(result, {
    title: "Build Request Folder result.",
    sourceLabel: "Folder",
    source: result.folderPath || result.folderName,
    countLabel: "build_request.json files found"
  });
}

function formatExportListBuildSummary(result) {
  return formatBatchBuildSummary(result, {
    title: "Build Export List result.",
    sourceLabel: "Export list",
    source: result.nativePath || result.fileName,
    countLabel: "build requests listed"
  });
}

function formatBatchBuildSummary(result, labels) {
  const built = result.built || [];
  const errors = result.errors || [];
  const saved = built.filter((entry) => entry.build && entry.build.saved).length;
  const closed = built.filter((entry) => entry.build && entry.build.closed).length;
  const placementErrors = built.reduce((total, entry) => (
    total + ((entry.build && entry.build.placementErrors && entry.build.placementErrors.length) || 0)
  ), 0);
  const maskErrors = built.reduce((total, entry) => (
    total + ((entry.build && entry.build.maskErrors && entry.build.maskErrors.length) || 0)
  ), 0);
  const needsAttention = built.reduce((total, entry) => {
    const counts = entry.build && entry.build.unplacedNodeCounts;
    return total + (counts && counts.needs_attention || 0);
  }, 0);

  const lines = [
    labels.title,
    "",
    `${labels.sourceLabel}: ${labels.source}`,
    `${labels.countLabel}: ${result.requestCount}`,
    `Built: ${built.length}`,
    `Saved: ${saved}`,
    `Closed after save: ${closed}`,
    `Failed requests: ${errors.length}`,
    `Placement errors: ${placementErrors}`,
    `Mask errors: ${maskErrors}`,
    `Unplaced nodes needing attention: ${needsAttention}`
  ];

  if (built.length > 0) {
    lines.push(
      "",
      "Built PSDs:",
      ...built.map((entry) => formatFolderBuildEntry(entry))
    );
  }
  if (errors.length > 0) {
    lines.push(
      "",
      "Failed requests:",
      ...errors.map((entry) => `- ${entry.nativePath || entry.fileName}: ${entry.error}`)
    );
  }
  return lines.join("\n");
}

function formatFolderBuildEntry(entry) {
  const summary = entry.summary || {};
  const build = entry.build || {};
  const counts = build.unplacedNodeCounts || categorizeUnplacedNodes(build.unplacedNodes);
  const status = build.saved ? "saved" : "not saved";
  const closed = build.closed ? ", closed" : "";
  const placementErrors = build.placementErrors && build.placementErrors.length || 0;
  const maskErrors = build.maskErrors && build.maskErrors.length || 0;
  const channel = summary.channelLabel || summary.channel || "unknown";
  const role = summary.channelRole ? `, ${summary.channelRole}` : "";
  return [
    `- ${summary.textureSet || "unknown"} / ${channel}${role} / ${summary.usesUdim ? summary.udim : "no UDIM"}: ${status}${closed}`,
    `  PSD: ${summary.psdFile || "(no PSD path)"}`,
    `  Groups: ${build.placedGroups ? build.placedGroups.length : 0}/${build.groupCount || 0}, PNG layers: ${build.placedLayerCount || 0}/${build.topLevelAssetCount || 0}, masks: ${build.appliedMaskCount || 0}/${build.topLevelMaskAssetCount || 0}`,
    `  Unplaced: ${formatUnplacedCounts(counts)}, placement errors: ${placementErrors}, mask errors: ${maskErrors}`
  ].join("\n");
}

function formatExportSelectedSummary(result) {
  const modeText = result.mode === "separate"
    ? "Layer PNG plus separate mask PNG when a mask exists"
    : "Layer PNG with current mask applied";
  const lines = [
    "Selected Photoshop layers exported.",
    "",
    `Mode: ${modeText}`,
    `Document: ${result.documentName}`,
    `Folder: ${result.folder}`,
    `Selected layers: ${result.selectedCount}`,
    `Files exported: ${result.exported.length}`,
  ];

  if (result.exported.length > 0) {
    lines.push("", "Exported files:", ...result.exported.map((file) => `- ${file}`));
  }
  if (result.layers && result.layers.length > 0) {
    lines.push(
      "",
      "Selected layer details:",
      ...result.layers.map((layer) => {
        const mask = layer.maskDetected ? "yes" : "no";
        const maskExport = layer.maskExported ? "yes" : "no";
        const files = layer.files && layer.files.length > 0 ? layer.files.join(", ") : "(none)";
        return `- ${layer.name}: mask detected=${mask}, mask exported=${maskExport}, files=${files}`;
      })
    );
  }
  if (result.errors.length > 0) {
    lines.push("", "Export errors:", ...result.errors.map((entry) => `- ${entry.layer}: ${entry.error}`));
  }
  return lines.join("\n");
}

function formatRequestSummary(result) {
  const summary = result.summary;
  const lines = [
    "build_request.json is valid.",
    "",
    `File: ${result.fileName}`,
    `Path: ${result.nativePath || "not exposed by host"}`,
    `Texture set: ${summary.textureSet}`,
    `Stack: ${summary.stack || "(default)"}`,
    `Channel: ${summary.channelLabel || summary.channel}`,
    `Channel role: ${summary.channelRole || "unknown"}`,
    `Channel format: ${summary.channelFormat || "unknown"}, ${summary.bitDepth || "unknown"} bit, ${summary.isColor ? "color" : "data"}`,
    `Normal map format: ${summary.channelRole === "normal" ? (summary.normalMapFormat || "unknown") : "(not normal)"}`,
    `UDIM: ${summary.usesUdim ? summary.udim : "(none)"}`,
    `Resolution: ${summary.resolution}`,
    `Top-level layers: ${summary.topLevelLayers}`,
    `PNG assets: ${summary.assetCount}`,
    `Mask assets: ${summary.maskAssetCount}`,
    `Baked assets: ${summary.bakedAssetCount}`,
    `Empty layer PNGs removed: ${summary.emptyLayerAssetsRemoved || 0}`,
    `Unplaced request nodes: ${formatUnplacedCounts(summary)}`,
    `PNG files exported: ${result.request.assets_exported === false ? "no (JSON-only bundle)" : "yes/unknown"}`,
    "",
    `Output PSD: ${summary.psdFile}`,
    ""
  ];

  if (result.build) {
    lines.push(
      "PSD skeleton created.",
      `Document: ${result.build.documentName}`,
      `Size: ${result.build.width}x${result.build.height}`,
      `Resolution: ${result.build.resolution} ppi`,
      `PNG files exported: ${result.build.assetsExported ? "yes/unknown" : "no (JSON-only bundle)"}`,
      `Groups created: ${result.build.placedGroups ? result.build.placedGroups.length : 0} of ${result.build.groupCount || 0}`,
      `PNG layers placed: ${result.build.placedLayerCount || 0} of ${result.build.topLevelAssetCount || 0}`,
      `Layer masks applied: ${result.build.appliedMaskCount || 0} of ${result.build.topLevelMaskAssetCount || 0}`,
      `Unplaced request nodes recorded: ${formatUnplacedCounts(result.build.unplacedNodeCounts || categorizeUnplacedNodes(result.build.unplacedNodes))}`,
      `Baseline hashes written: ${result.build.baselineHashCount || 0} of ${result.build.placedLayerCount || 0}`,
      `Blend gamma command: ${result.build.blendGammaAttempted ? (result.build.blendGammaSet ? "set" : "failed") : "skipped"}`,
      `Top-level Layer 1 removed: ${result.build.removedResidualDefaultLayer ? "yes" : "no"}`,
      `Sidecar written: ${result.build.sidecarWritten ? "yes" : "no"}`,
      `Saved: ${result.build.saved ? "yes" : "no"}`
    );
    if (result.build.blendGammaError) {
      lines.push(`Blend gamma warning: ${result.build.blendGammaError}`);
    }
    if (result.build.sidecarPath) {
      lines.push(`Sidecar: ${result.build.sidecarPath}`);
    }
    if (result.build.sidecarError) {
      lines.push(`Sidecar warning: ${result.build.sidecarError}`);
    }
    if (result.build.defaultLayerRemoveError) {
      lines.push(`Default layer cleanup warning: ${result.build.defaultLayerRemoveError}`);
    }
    if (result.build.baselineHashErrors && result.build.baselineHashErrors.length > 0) {
      lines.push(
        "Baseline hash warnings:",
        ...result.build.baselineHashErrors.map((entry) => `- ${entry.name}: ${entry.error}`)
      );
    }
    if (result.build.placedGroups && result.build.placedGroups.length > 0) {
      lines.push(
        "",
        "Placed groups:",
        ...result.build.placedGroups.map((group) => {
          const blend = group.blendMode ? ` [${group.blendMode}]` : "";
          const mask = group.maskPath ? `, mask ${group.maskApplied ? "applied" : "failed"}` : "";
          const path = group.groupName ? `${group.groupName}/` : "";
          const childGroups = group.childGroupCount ? `, ${group.childGroupCount} child groups` : "";
          return `- ${path}${group.psName || group.name}${blend} (${group.childLayerCount} PNG layers${childGroups}${mask})`;
        })
      );
    }
    if (result.build.placedLayers && result.build.placedLayers.length > 0) {
      lines.push(
        "",
        "Placed layers:",
        ...result.build.placedLayers.map((layer) => {
          const blend = layer.blendMode ? ` [${layer.blendMode}]` : "";
          const group = layer.groupName ? `${layer.groupName}/` : "";
          const lines = [
            `- ${group}${layer.psName || layer.name}${blend}${layer.clipped ? " [clipped]" : ""}`,
            `  ${layer.path || "(no source path)"}`
          ];
          if (layer.maskPath) {
            lines.push(`  Mask ${layer.maskApplied ? "applied" : "failed"}: ${layer.maskPath}`);
          }
          return lines.join("\n");
        })
      );
    }
    if (result.build.unplacedNodes && result.build.unplacedNodes.length > 0) {
      appendUnplacedNodeSections(lines, result.build.unplacedNodes);
    }
    if (result.build.maskErrors && result.build.maskErrors.length > 0) {
      lines.push(
        "",
        "Mask errors:",
        ...result.build.maskErrors.map((entry) => `- ${entry.name}: ${entry.error}`)
      );
    }
    if (result.build.placementErrors && result.build.placementErrors.length > 0) {
      lines.push(
        "",
        "Placement errors:",
        ...result.build.placementErrors.map((entry) => `- ${entry.name}: ${entry.error}`)
      );
      if (hasMissingPngErrors(result.build.placementErrors)) {
        lines.push(
          "",
          "Hint: Re-run the Painter smoke test with Export PNGs enabled, then choose the new build_request.json."
        );
      }
    }
    if (result.build.saveError) {
      lines.push(
        "",
        "Save attempt did not complete.",
        result.build.saveError,
        "",
        "The Photoshop document should remain open; this slice is still valid if document creation and PNG placement worked."
      );
    }
  } else {
    lines.push("PSD creation did not run.");
  }

  return lines.join("\n");
}

function appendUnplacedNodeSections(lines, nodes) {
  const groups = {
    needs_attention: [],
    unsupported: [],
    known_baked: []
  };
  for (const node of nodes || []) {
    const category = node.category || "known_baked";
    if (groups[category]) {
      groups[category].push(node);
    } else {
      groups.needs_attention.push(node);
    }
  }

  appendUnplacedGroup(lines, "Unplaced assets needing attention:", groups.needs_attention);
  appendUnplacedGroup(lines, "Unsupported editable effects recorded as provenance:", groups.unsupported);
  appendUnplacedGroup(lines, "Known baked request nodes:", groups.known_baked);
}

function appendUnplacedGroup(lines, title, nodes) {
  if (!nodes || nodes.length === 0) {
    return;
  }
  lines.push("", title, ...nodes.map((node) => `- ${node.path} [${node.spKind}] ${node.reason}`));
}

function formatUnplacedCounts(source) {
  const counts = source && source.known_baked !== undefined
    ? source
    : {
        known_baked: source.unplacedKnownBakedCount || 0,
        unsupported: source.unplacedUnsupportedCount || 0,
        needs_attention: source.unplacedNeedsAttentionCount || 0
      };
  const total = counts.known_baked + counts.unsupported + counts.needs_attention;
  return `${total} (known baked ${counts.known_baked}, unsupported ${counts.unsupported}, needs attention ${counts.needs_attention})`;
}

function categorizeUnplacedNodes(nodes) {
  const counts = {
    known_baked: 0,
    unsupported: 0,
    needs_attention: 0
  };
  for (const node of nodes || []) {
    const category = node.category || "known_baked";
    if (counts[category] === undefined) {
      counts.needs_attention += 1;
    } else {
      counts[category] += 1;
    }
  }
  return counts;
}

function hasMissingPngErrors(errors) {
  return (errors || []).some((entry) => String(entry.error || "").includes("PNG asset not found"));
}

function makeButton(label) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  setStyles(button, {
    display: "block",
    width: "100%",
    minHeight: "34px",
    margin: "0 0 8px",
    padding: "6px 8px",
    border: "1px solid #555555",
    borderRadius: "3px",
    background: "#eeeeee",
    color: "#111111",
    fontSize: "13px"
  });
  return button;
}

function setDetailsText(details, text) {
  if ("value" in details) {
    details.value = text;
  } else {
    details.textContent = text;
  }
}

function getDetailsText(details) {
  return "value" in details ? details.value : details.textContent;
}

function selectDetails(details) {
  if (details.focus) {
    details.focus();
  }
  if (details.select) {
    details.select();
  }
}

function setStyles(node, styles) {
  Object.keys(styles).forEach((key) => {
    node.style[key] = styles[key];
  });
}
