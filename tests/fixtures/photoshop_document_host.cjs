const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Match the fresh ExtendScript host contract, not Node's built-in JSON object.
const calls = { opened: [], closed: [], saved: [] };
function File(filename) {
  const file = {
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
  return file;
}
const layer = (id, name) => ({ id, name, typename: "ArtLayer", visible: true, opacity: 100,
  kind: "LayerKind.NORMAL", blendMode: "BlendMode.NORMAL" });
function makeDocument(filename) {
  return {
    id: 10, name: path.basename(filename), fullName: File(filename), mode: "rgb",
    layers: [{ id: 1, name: "Group", typename: "LayerSet", visible: true,
      opacity: 100, blendMode: "BlendMode.NORMAL", layers: [layer(2, "Detail")] }, layer(3, "Base")],
    duplicate() { return makeDocument(filename + ".duplicate"); },
    close() { calls.closed.push(filename); },
    saveAs(file) { calls.saved.push(filename); fs.writeFileSync(file.fsName, "PNG"); },
  };
}
const app = {
  displayDialogs: "original", documents: [], preferences: { rulerUnits: "original" },
  bringToFront() {},
  open(file) {
    calls.opened.push(file.fsName);
    const doc = makeDocument(file.fsName);
    this.documents.push(doc);
    return doc;
  },
};
const context = vm.createContext({
  JSON: undefined, File, Folder: (p) => ({ exists: fs.existsSync(p) }), app,
  DialogModes: { NO: "none" }, Units: { PIXELS: "pixels" },
  DocumentMode: { RGB: "rgb" }, Extension: { LOWERCASE: "lower" },
  SaveOptions: { DONOTSAVECHANGES: "discard" }, PNGSaveOptions: function () {}, alert() {},
});
const script = fs.readFileSync(process.argv[2], "utf8").replace(/^#target.*$/m, "");
vm.runInContext(script, context, { timeout: 5000 });
calls.globalJson = vm.runInContext("typeof JSON", context);
calls.dialogs = app.displayDialogs;
calls.rulerUnits = app.preferences.rulerUnits;
process.stdout.write(JSON.stringify(calls));
