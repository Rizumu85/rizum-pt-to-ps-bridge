import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises"
import path from "node:path"

import {
  emptyBridgeState,
  type BridgeState,
  type HostLayerRef,
  type LayerNode,
} from "./model"

type JsonObject = Record<string, unknown>

export type SessionOptions = {
  photoshopManifest: string
  painterSnapshot?: string
  output?: string
}

export type BridgeSession = {
  state: BridgeState
  sourceManifestPath: string
  targetSnapshotPath: string
  outputPath: string
  photoshopSubtitle: string
  painterSubtitle: string
  status: string
  sourceDocument: JsonObject
  targetDocument: JsonObject
}

export function parseSessionOptions(
  argv: string[],
  env: Record<string, string | undefined> = process.env,
): SessionOptions {
  const values: Partial<SessionOptions> = {
    photoshopManifest: env.PT_BRIDGE_PHOTOSHOP_MANIFEST,
    painterSnapshot: env.PT_BRIDGE_PAINTER_SNAPSHOT,
    output: env.PT_BRIDGE_TRANSFER_OUTPUT,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index]
    const value = argv[index + 1]
    if (!["--session", "--photoshop", "--painter", "--output"].includes(flag)) {
      throw new Error(`Unknown desktop argument: ${flag}`)
    }
    if (!value || value.startsWith("--")) {
      throw new Error(`Desktop argument ${flag} requires a path`)
    }

    if (flag === "--session" || flag === "--photoshop") values.photoshopManifest = value
    if (flag === "--painter") values.painterSnapshot = value
    if (flag === "--output") values.output = value
    index += 1
  }

  if (!values.photoshopManifest) {
    throw new Error("Pass --session <photoshop_selection.json> to load a transfer session")
  }
  return values as SessionOptions
}

export async function loadBridgeSession(options: SessionOptions): Promise<BridgeSession> {
  const sourceManifestPath = path.resolve(options.photoshopManifest)
  const source = await readJsonObject(sourceManifestPath)
  if (source.request_type !== "photoshop_selection") {
    throw new Error("Photoshop manifest request_type must be 'photoshop_selection'")
  }
  if (source.schema_version !== 1) {
    throw new Error("Photoshop selection manifest uses an unsupported schema_version")
  }

  const targetSnapshotPath = path.resolve(
    options.painterSnapshot ?? targetSnapshotFromSelection(source, sourceManifestPath),
  )
  const target = await readJsonObject(targetSnapshotPath)
  const photoshop = photoshopNodes(source, sourceManifestPath)
  const painter = painterNodes(target)
  if (photoshop.length === 0) throw new Error("Photoshop selection manifest has no exported layers")
  if (painter.length === 0) throw new Error("Painter snapshot has no addressable layers")

  const sourceDocument = objectValue(source.document)
  const targetDocument = objectValue(target.document)
  const outputPath = path.resolve(
    options.output ?? path.join(path.dirname(sourceManifestPath), "desktop_transfer.json"),
  )

  return {
    state: { photoshop, painter, mappings: [] },
    sourceManifestPath,
    targetSnapshotPath,
    outputPath,
    photoshopSubtitle: textValue(sourceDocument.name) || textValue(source.document_name) || "Selection",
    painterSubtitle: painterSubtitle(target),
    status: "Drag exported Photoshop layers into the Painter stack",
    sourceDocument,
    targetDocument,
  }
}

export function failedBridgeSession(error: unknown): BridgeSession {
  const message = error instanceof Error ? error.message : String(error)
  return {
    state: structuredClone(emptyBridgeState),
    sourceManifestPath: "",
    targetSnapshotPath: "",
    outputPath: "",
    photoshopSubtitle: "No selection loaded",
    painterSubtitle: "No snapshot loaded",
    status: message,
    sourceDocument: {},
    targetDocument: {},
  }
}

export async function writeTransferManifest(session: BridgeSession, state: BridgeState): Promise<string> {
  if (!session.outputPath) throw new Error("The transfer session has no output path")
  if (state.mappings.length === 0) throw new Error("Map at least one Photoshop layer before Apply")

  const payload = {
    schema_version: 1,
    request_type: "desktop_transfer",
    created_at: new Date().toISOString(),
    source: {
      host: "photoshop",
      manifest: session.sourceManifestPath,
      document: session.sourceDocument,
    },
    target: {
      host: "substance_painter",
      snapshot: session.targetSnapshotPath,
      document: session.targetDocument,
    },
    transfers: state.mappings.map((mapping, order) => ({
      order,
      source: manifestRef(mapping.source),
      target: manifestRef(mapping.target),
      insertion: mapping.placement,
    })),
  }

  await mkdir(path.dirname(session.outputPath), { recursive: true })
  const temporaryPath = `${session.outputPath}.tmp-${process.pid}`
  await writeFile(temporaryPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8")
  await unlink(session.outputPath).catch((error: NodeJS.ErrnoException) => {
    if (error.code !== "ENOENT") throw error
  })
  // The destination plugin must never observe a half-written transfer contract.
  await rename(temporaryPath, session.outputPath)
  return session.outputPath
}

function photoshopNodes(manifest: JsonObject, manifestPath: string): LayerNode[] {
  const manifestDir = path.dirname(manifestPath)
  return arrayValue(manifest.layers).map((value, index) => {
    const layer = objectValue(value)
    const externalId = textValue(layer.source_id) || `selection-${index + 1}`
    const name = textValue(layer.display_name) || textValue(layer.name) || `Layer ${index + 1}`
    const group = textValue(layer.group)
    const relativeAsset = textValue(layer.png)
    const relativeMask = textValue(layer.mask_png)
    const ref: HostLayerRef = {
      host: "photoshop",
      externalId,
      kind: textValue(layer.ps_kind) || "layer",
      path: textValue(layer.path) || (group ? `${group}/${name}` : name),
      assetPath: relativeAsset ? resolveAsset(manifestDir, relativeAsset) : null,
      maskPath: relativeMask ? resolveAsset(manifestDir, relativeMask) : null,
    }
    return {
      id: `photoshop:${externalId}`,
      kind: "layer",
      name,
      detail: layerDetail(layer),
      masked: Boolean(relativeMask),
      ref,
    }
  })
}

function painterNodes(snapshot: JsonObject): LayerNode[] {
  if (snapshot.request_type === "build") {
    return requestNodes(arrayValue(snapshot.layers), "")
  }
  if (snapshot.schema_version === 1 && Array.isArray(snapshot.layers)) {
    return sidecarNodes(arrayValue(snapshot.layers))
  }
  throw new Error("Painter snapshot must be a build_request.json or Photoshop .rizum.json sidecar")
}

function requestNodes(values: unknown[], parentPath: string): LayerNode[] {
  return values.map((value, index) => {
    const node = objectValue(value)
    const name = textValue(node.name) || textValue(node.display_name) || `Layer ${index + 1}`
    const kindText = textValue(node.kind) || "layer"
    const childValues = arrayValue(node.children)
    const isGroup = /group/i.test(kindText) || childValues.length > 0
    const uid = textValue(node.uid_hex) || textValue(node.uid) || `${parentPath}:${index}`
    const nodePath = parentPath ? `${parentPath}/${name}` : name
    return {
      id: `substance_painter:${uid}`,
      kind: isGroup ? "group" : "layer",
      name,
      detail: isGroup ? `${childValues.length} Layers` : layerDetail(node),
      masked: Boolean(node.mask_asset) || node.has_mask === true,
      ref: {
        host: "substance_painter",
        externalId: uid,
        kind: kindText,
        path: nodePath,
        assetPath: assetPath(node.asset),
        maskPath: assetPath(node.mask_asset),
      },
      children: isGroup ? requestNodes(childValues, nodePath) : undefined,
    } satisfies LayerNode
  })
}

function sidecarNodes(values: unknown[]): LayerNode[] {
  const ordered = values
    .map((value, index) => ({ record: objectValue(value), index }))
    .sort((left, right) => numberValue(left.record.order, left.index) - numberValue(right.record.order, right.index))
  const entries = ordered.map(({ record, index }) => ({ record, node: sidecarNode(record, index) }))
  const groups = new Map<string, LayerNode>()

  for (const { record, node } of entries) {
    if (node.kind !== "group") continue
    for (const key of [record.path, record.ps_name, record.display_name]) {
      const text = textValue(key)
      if (text) groups.set(text, node)
    }
  }

  const roots: LayerNode[] = []
  for (const { record, node } of entries) {
    const parentName = textValue(record.group)
    const parent = parentName ? groups.get(parentName) : undefined
    if (parent && parent !== node) {
      parent.children = [...(parent.children ?? []), node]
    } else {
      roots.push(node)
    }
  }
  return roots
}

function sidecarNode(record: JsonObject, index: number): LayerNode {
  const name = textValue(record.display_name) || textValue(record.ps_name) || `Layer ${index + 1}`
  const kindText = textValue(record.sp_kind) || textValue(record.ps_kind) || "layer"
  const isGroup = textValue(record.ps_kind) === "group"
  const uid = textValue(record.sp_uid) || `${textValue(record.path) || name}:${index}`
  return {
    id: `substance_painter:${uid}`,
    kind: isGroup ? "group" : "layer",
    name,
    detail: isGroup ? "Group" : layerDetail(record),
    masked: Boolean(record.mask_path),
    ref: {
      host: "substance_painter",
      externalId: uid,
      kind: kindText,
      path: textValue(record.path) || name,
      assetPath: nullableText(record.asset_path),
      maskPath: nullableText(record.mask_path),
    },
    children: isGroup ? [] : undefined,
  }
}

function targetSnapshotFromSelection(selection: JsonObject, manifestPath: string): string {
  const explicit = textValue(selection.painter_snapshot)
  if (explicit) return resolveAsset(path.dirname(manifestPath), explicit)
  const document = objectValue(selection.document)
  const psd = textValue(document.path) || textValue(selection.source_psd)
  if (!psd) {
    throw new Error("Pass --painter <snapshot> because the Photoshop manifest has no document path")
  }
  return psd.replace(/\.[^.\\/]*$/, "") + ".rizum.json"
}

function painterSubtitle(snapshot: JsonObject): string {
  const textureSet = textValue(snapshot.texture_set)
  const channel = textValue(snapshot.channel_label) || textValue(snapshot.channel)
  if (textureSet && channel) return `${textureSet} · ${channel}`
  return textureSet || channel || "Painter snapshot"
}

function layerDetail(record: JsonObject): string {
  const blend = textValue(record.blend_mode) || textValue(record.ps_blend_mode) || "Normal"
  const opacity = numberValue(record.opacity, 100)
  return `${humanize(blend)} · ${Math.round(opacity)}%`
}

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ")
}

function manifestRef(ref: HostLayerRef) {
  return {
    host: ref.host,
    id: ref.externalId,
    kind: ref.kind,
    path: ref.path,
    png: ref.assetPath ?? null,
    mask_png: ref.maskPath ?? null,
  }
}

function assetPath(value: unknown): string | null {
  return nullableText(objectValue(value).path)
}

function resolveAsset(base: string, value: string): string {
  return path.isAbsolute(value) ? value : path.resolve(base, value)
}

async function readJsonObject(filePath: string): Promise<JsonObject> {
  let parsed: unknown
  try {
    parsed = JSON.parse(await readFile(filePath, "utf8"))
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`Could not read ${filePath}: ${message}`)
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${filePath} must contain a JSON object`)
  }
  return parsed as JsonObject
}

function objectValue(value: unknown): JsonObject {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as JsonObject) : {}
}

function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function textValue(value: unknown): string {
  if (typeof value === "string") return value.trim()
  if (typeof value === "number" && Number.isFinite(value)) return String(value)
  return ""
}

function nullableText(value: unknown): string | null {
  return textValue(value) || null
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback
}

