"use strict";

const { entrypoints } = require("uxp");

const PLUGIN_VERSION = "0.1.47";

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
  panel.appendChild(exportAppliedButton);
  panel.appendChild(exportSeparateButton);
  panel.appendChild(copyButton);
  panel.appendChild(details);
  rootNode.appendChild(panel);

  buildButton.addEventListener("click", () => {
    handleBuildFromPainter(buildButton, details);
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
    `Channel: ${summary.channel}`,
    `UDIM: ${summary.usesUdim ? summary.udim : "(none)"}`,
    `Resolution: ${summary.resolution}`,
    `Top-level layers: ${summary.topLevelLayers}`,
    `PNG assets: ${summary.assetCount}`,
    `Mask assets: ${summary.maskAssetCount}`,
    `Baked assets: ${summary.bakedAssetCount}`,
    `Unplaced request nodes: ${summary.unplacedNodeCount || 0}`,
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
      `Top-level groups created: ${result.build.placedGroups ? result.build.placedGroups.length : 0} of ${result.build.topLevelGroupCount || 0}`,
      `PNG layers placed: ${result.build.placedLayerCount || 0} of ${result.build.topLevelAssetCount || 0}`,
      `Layer masks applied: ${result.build.appliedMaskCount || 0} of ${result.build.topLevelMaskAssetCount || 0}`,
      `Unplaced request nodes recorded: ${result.build.unplacedNodes ? result.build.unplacedNodes.length : 0}`,
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
          return `- ${group.psName || group.name}${blend} (${group.childLayerCount} direct PNG layers${mask})`;
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
            `- ${group}${layer.psName || layer.name}${blend}`,
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
      lines.push(
        "",
        "Unplaced request nodes:",
        ...result.build.unplacedNodes.map((node) => `- ${node.path} [${node.spKind}] ${node.reason}`)
      );
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
