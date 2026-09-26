const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// A minimal Photoshop layer model for photoshop_transfer.jsx: Place creates a
// layer above the active one, new groups open at the top of their container,
// move() follows ElementPlacement, and a folder is never moved into a folder.
// As in Photoshop, a paste goes into a layer mask only while that mask is
// selected and shown; otherwise it lands as a new layer. Prints the final layer tree.
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
let nextId = 100;
// Like Photoshop, Place centres an image in the visible part of the window;
// a zoomed view sets how far from the canvas corner a canvas-sized image lands.
const viewOffset = (process.env.FAKE_VIEW_OFFSET || "0,0").split(",").map(Number);
const CANVAS = 64;

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

function container(owner) {
  owner.layers = [];
  owner.artLayers = { add: () => insertAboveActive(makeLayer("Layer", "ArtLayer")) };
  owner.layerSets = {
    add: () => {
      const set = makeLayer("Group", "LayerSet");
      attach(set, owner, 0);
      document.activeLayer = set;
      return set;
    },
  };
  return owner;
}

function makeLayer(name, typename) {
  let blendMode = "BlendMode.NORMAL"
  const layer = {
    id: nextId++, name, typename, visible: true, opacity: 100,
    // Like a document whose mode lacks it, this host refuses Divide.
    get blendMode() { return blendMode },
    set blendMode(value) {
      if (value === "DIVIDE") throw new Error("General Photoshop error occurred. - The command \"Set\" is not currently available.")
      blendMode = value
    },
    rasterized: false, parent: null, offset: [0, 0],
    get bounds() { return [this.offset[0], this.offset[1], this.offset[0] + CANVAS, this.offset[1] + CANVAS]; },
    translate(dx, dy) { this.offset = [this.offset[0] + dx, this.offset[1] + dy]; },
    rasterize() { this.rasterized = true; },
    remove() { detach(this); },
    move(target, placement) {
      // Like Photoshop, a folder can be moved beside a layer but not into a folder.
      if (typename === "LayerSet" && placement !== "PLACEBEFORE" && placement !== "PLACEAFTER") {
        throw new Error("Illegal Argument")
      }
      detach(this);
      if (placement === "PLACEATEND") attach(this, target, target.layers.length);
      else if (placement === "PLACEATBEGINNING") attach(this, target, 0);
      else {
        const siblings = target.parent.layers;
        const index = siblings.indexOf(target);
        attach(this, target.parent, placement === "PLACEAFTER" ? index + 1 : index);
      }
    },
  };
  return typename === "LayerSet" ? container(layer) : layer;
}

function attach(layer, parent, index) {
  layer.parent = parent;
  parent.layers.splice(index, 0, layer);
}

function detach(layer) {
  const siblings = layer.parent.layers;
  siblings.splice(siblings.indexOf(layer), 1);
  layer.parent = null;
}

function insertAboveActive(layer) {
  const active = document.activeLayer;
  if (active && active.parent) attach(layer, active.parent, active.parent.layers.indexOf(active));
  else attach(layer, document, 0);
  document.activeLayer = layer;
  return layer;
}

const document = container({
  id: 10, name: path.basename(request.document.path), fullName: File(request.document.path),
  activeLayer: null, saved: false,
  save() { this.saved = true; },
  selection: { selectAll() {}, deselect() {} },
});
let maskShown = false;
let clipboard = null;
const group = makeLayer("Group", "LayerSet");
group.id = 1;
attach(group, document, 0);
const detail = makeLayer("Detail", "ArtLayer");
detail.id = 2;
attach(detail, group, 0);
const base = makeLayer("Base", "ArtLayer");
base.id = 3;
attach(base, document, 1);
document.activeLayer = base;

function ActionDescriptor() {
  return {
    flags: {},
    putPath() {}, putEnumerated() {}, putUnitDouble() {}, putObject() {}, putClass() {},
    putBoolean(key, value) { this.flags[key] = value; },
    putReference(_key, reference) { this.reference = reference; },
  };
}
function ActionReference() {
  return {
    putIdentifier(_type, id) { this.layerId = id; },
    putEnumerated(_type, _enum, value) { this.channel = value; },
  };
}
function findLayer(list, id) {
  for (const layer of list) {
    if (layer.id === id) return layer;
    const inner = layer.layers && findLayer(layer.layers, id);
    if (inner) return inner;
  }
  return null;
}
function executeAction(id, descriptor) {
  if (id === "slct") {
    const reference = (descriptor && descriptor.reference) || {};
    if (reference.layerId !== undefined) {
      document.activeLayer = findLayer(document.layers, reference.layerId);
      maskShown = false;
    } else {
      maskShown = reference.channel === "Msk " && descriptor.flags.MkVs === true;
    }
    return;
  }
  if (id === "copy") { clipboard = document.activeLayer.name; return; }
  if (id === "Mk  ") { document.activeLayer.mask = "reveal all"; return; }
  if (id === "past") {
    if (maskShown && document.activeLayer.mask) document.activeLayer.mask = "pasted " + clipboard;
    else insertAboveActive(makeLayer("Pasted " + clipboard, "ArtLayer"));
    return;
  }
  if (id !== "Plc ") throw new Error("Unexpected action " + id);
  const placed = makeLayer("Placed", "ArtLayer");
  placed.offset = [...viewOffset];
  insertAboveActive(placed);
}
const names = (list) => Object.fromEntries(list.map((name) => [name, name]));
const app = {
  displayDialogs: "original", preferences: { rulerUnits: "original" }, documents: [document],
  activeDocument: document, bringToFront() {},
  open() { throw new Error("The mapped document is already open"); },
};
const context = vm.createContext({
  JSON: undefined, File, app, ActionDescriptor, ActionReference, executeAction,
  charIDToTypeID: (id) => id, stringIDToTypeID: (id) => id,
  DialogModes: { NO: "none" }, Units: { PIXELS: "pixels" },
  RasterizeType: { ENTIRELAYER: "ENTIRELAYER" },
  ElementPlacement: names(["PLACEAFTER", "PLACEBEFORE", "PLACEATEND", "PLACEATBEGINNING"]),
  BlendMode: Object.fromEntries([
    "NORMAL", "PASSTHROUGH", "MULTIPLY", "SCREEN", "OVERLAY", "DARKEN", "LIGHTEN", "LINEARDODGE",
    "LINEARBURN", "COLORBURN", "COLORDODGE", "SOFTLIGHT", "HARDLIGHT", "VIVIDLIGHT", "LINEARLIGHT",
    "PINLIGHT", "DIFFERENCE", "EXCLUSION", "SUBTRACT", "DIVIDE", "HUE", "SATURATION", "COLORBLEND",
    "LUMINOSITY",
  ].map((mode) => [mode, mode])),
});
const script = fs.readFileSync(process.argv[2], "utf8").replace(/^#target.*$/m, "");
vm.runInContext(script, context, { timeout: 5000 });

const tree = (list) => list.map((layer) => ({
  name: layer.name, typename: layer.typename, blendMode: layer.blendMode, opacity: layer.opacity,
  visible: layer.visible, rasterized: layer.rasterized, mask: layer.mask || null, offset: layer.offset,
  ...(layer.typename === "LayerSet" ? { layers: tree(layer.layers) } : {}),
}));
process.stdout.write(JSON.stringify({ saved: document.saved, layers: tree(document.layers) }));
