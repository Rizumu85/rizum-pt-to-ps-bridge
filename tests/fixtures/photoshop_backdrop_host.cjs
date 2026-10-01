const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// A minimal Photoshop for photoshop_backdrop.jsx. The document tree comes
// from FAKE_DOCUMENT as nested [name, kind, blendMode?, children?] entries,
// top first. duplicate() deep-copies it; saveAs() writes, instead of pixels,
// what the saved composite would contain: each visible layer with the state
// of every folder around it. Prints whether the original was left untouched.
const spec = JSON.parse(process.env.FAKE_DOCUMENT);
let nextId = 1;

function File(filename) {
  return {
    fsName: filename,
    name: path.basename(filename),
    parent: { fsName: path.dirname(filename) },
    get exists() { return fs.existsSync(filename); },
    open(mode) {
      if (mode === "r") return fs.existsSync(filename);
      fs.writeFileSync(filename, "");
      return true;
    },
    read() { return fs.readFileSync(filename, "utf8"); },
    write(text) { fs.appendFileSync(filename, text); return true; },
    close() { return true; },
    remove() { fs.unlinkSync(filename); return true; },
    rename(name) { fs.renameSync(filename, path.join(path.dirname(filename), name)); return true; },
  };
}

function build(entries, parent) {
  parent.layers = entries.map(([name, kind, blendMode, children]) => {
    const layer = {
      id: nextId++, name, typename: kind === "group" ? "LayerSet" : "ArtLayer",
      blendMode: blendMode || (kind === "group" ? "PASSTHROUGH" : "NORMAL"),
      opacity: 100, visible: true, maskEnabled: true, parent,
    };
    if (kind === "group") build(children || [], layer);
    return layer;
  });
  return parent;
}

function clone(layers, parent) {
  return layers.map((layer) => {
    const copy = { ...layer, id: nextId++, parent };
    if (layer.layers) copy.layers = clone(layer.layers, copy);
    return copy;
  });
}

function snapshot(layers) {
  return layers.map((layer) => ({
    name: layer.name, visible: layer.visible, blendMode: layer.blendMode,
    opacity: layer.opacity, maskEnabled: layer.maskEnabled,
    ...(layer.layers ? { layers: snapshot(layer.layers) } : {}),
  }));
}

function composite(layers, around) {
  const shown = [];
  for (const layer of layers) {
    if (!layer.visible) continue;
    if (layer.layers) {
      shown.push(...composite(layer.layers, [...around, `${layer.name}:${layer.blendMode}:${layer.opacity}:${layer.maskEnabled ? "mask" : "nomask"}`]));
    } else {
      shown.push([layer.name, ...around].join(" < "));
    }
  }
  return shown;
}

function makeDocument(name, fullName, layers) {
  const document = { typename: "Document", id: nextId++, name, fullName, activeLayer: null, closed: false };
  document.layers = layers ? clone(layers, document) : build(spec, document).layers;
  document.duplicate = () => {
    const copy = makeDocument("copy", null, document.layers);
    app.documents.push(copy);
    return copy;
  };
  document.saveAs = (file) => { fs.writeFileSync(file.fsName, JSON.stringify(composite(document.layers, []))); };
  document.close = () => { document.closed = true; app.documents.splice(app.documents.indexOf(document), 1); };
  return document;
}

const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const document = makeDocument(path.basename(request.document.path), File(request.document.path));
const original = JSON.stringify(snapshot(document.layers));

function findLayer(list, id) {
  for (const layer of list) {
    if (layer.id === id) return layer;
    const inner = layer.layers && findLayer(layer.layers, id);
    if (inner) return inner;
  }
  return null;
}
function ActionDescriptor() {
  return {
    flags: {},
    putBoolean(key, value) { this.flags[key] = value; },
    putReference(_key, reference) { this.reference = reference; },
    putObject(_key, _class, value) { this.object = value; },
  };
}
function ActionReference() {
  return {
    putIdentifier(_type, id) { this.layerId = id; },
    putEnumerated() {},
  };
}
function executeAction(id, descriptor) {
  const active = app.activeDocument;
  if (id === "slct") {
    active.activeLayer = findLayer(active.layers, descriptor.reference.layerId);
    return;
  }
  if (id === "setd" && descriptor.object && descriptor.object.flags.userMaskEnabled === false) {
    active.activeLayer.maskEnabled = false;
    return;
  }
  throw new Error("Unexpected action " + id);
}
const app = { displayDialogs: "original", documents: [document], activeDocument: document, open() { throw new Error("already open"); } };
const context = vm.createContext({
  JSON: undefined, File, app, ActionDescriptor, ActionReference, executeAction,
  charIDToTypeID: (id) => id, stringIDToTypeID: (id) => id,
  DialogModes: { NO: "none" }, SaveOptions: { DONOTSAVECHANGES: "no" }, Extension: { LOWERCASE: "lower" },
  PNGSaveOptions: function PNGSaveOptions() {},
  BlendMode: { NORMAL: "NORMAL", PASSTHROUGH: "PASSTHROUGH" },
});
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context, { timeout: 5000 });
process.stdout.write(JSON.stringify({
  untouched: JSON.stringify(snapshot(document.layers)) === original,
  open: app.documents.length,
}));
