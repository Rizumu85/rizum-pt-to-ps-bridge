const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// A minimal Photoshop layer model for photoshop_transfer.jsx: Place creates a
// layer above the active one, new groups open at the top of their container,
// and move() follows ElementPlacement. Prints the final layer tree.
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
let nextId = 100;

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
  const layer = {
    id: nextId++, name, typename, visible: true, opacity: 100, blendMode: "BlendMode.NORMAL",
    rasterized: false, parent: null,
    rasterize() { this.rasterized = true; },
    remove() { detach(this); },
    move(target, placement) {
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
});
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
  return { putPath() {}, putEnumerated() {}, putUnitDouble() {}, putObject() {} };
}
function executeAction(id) {
  if (id !== "Plc ") throw new Error("Unexpected action " + id);
  insertAboveActive(makeLayer("Placed", "ArtLayer"));
}
const names = (list) => Object.fromEntries(list.map((name) => [name, name]));
const app = {
  displayDialogs: "original", preferences: { rulerUnits: "original" }, documents: [document],
  activeDocument: document, bringToFront() {},
  open() { throw new Error("The mapped document is already open"); },
};
const context = vm.createContext({
  JSON: undefined, File, app, ActionDescriptor, executeAction,
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
  visible: layer.visible, rasterized: layer.rasterized,
  ...(layer.typename === "LayerSet" ? { layers: tree(layer.layers) } : {}),
}));
process.stdout.write(JSON.stringify({ saved: document.saved, layers: tree(document.layers) }));
