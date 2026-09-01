import { existsSync } from "node:fs"
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

export type PainterContext = {
  id: string
  textureSet: string
  stack: string
  channel: string
  channelLabel: string
  subtitle: string
  nodes: LayerNode[]
}

export type BridgeSession = {
  state: BridgeState
  sourceManifestPath: string
  targetSnapshotPath: string
  outputPath: string
  photoshopSubtitle: string
  painterContexts: PainterContext[]
  initialPainterContextId: string
  status: string
  sourceDocument: JsonObject
  sourceContext: JsonObject
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
  const contexts = painterContexts(target)
  const sourceContext = await photoshopDocumentContext(source, sourceManifestPath)
  const initialContext = matchingPainterContext(contexts, sourceContext) ?? contexts[0]
  if (photoshop.length === 0) throw new Error("Photoshop selection manifest has no exported layers")
  if (!initialContext) throw new Error("Painter snapshot has no addressable contexts")

  const sourceDocument = objectValue(source.document)
  const targetDocument = objectValue(target.project)
  const outputPath = path.resolve(
    options.output ?? path.join(path.dirname(sourceManifestPath), "desktop_transfer.json"),
  )

  return {
    state: { photoshop, painter: initialContext.nodes, mappings: [] },
    sourceManifestPath,
    targetSnapshotPath,
    outputPath,
    photoshopSubtitle: textValue(sourceDocument.name) || textValue(source.document_name) || "Selection",
    painterContexts: contexts,
    initialPainterContextId: initialContext.id,
    status: "Drag layers between Photoshop and Painter to map a transfer",
    sourceDocument,
    sourceContext,
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
    painterContexts: [],
    initialPainterContextId: "",
    status: message,
    sourceDocument: {},
    sourceContext: {},
    targetDocument: {},
  }
}

export async function writeTransferManifest(
  session: BridgeSession,
  state: BridgeState,
  painterContextId: string,
): Promise<string> {
  if (!session.outputPath) throw new Error("The transfer session has no output path")
  if (state.mappings.length === 0) throw new Error("Map at least one layer before Apply")
  const painterContext = session.painterContexts.find((context) => context.id === painterContextId)
  if (!painterContext) throw new Error("The selected Painter context is no longer available")

  const payload = {
    schema_version: 2,
    request_type: "desktop_transfer",
    created_at: new Date().toISOString(),
    photoshop: {
      manifest: session.sourceManifestPath,
      document: session.sourceDocument,
      context: session.sourceContext,
    },
    painter: {
      snapshot: session.targetSnapshotPath,
      document: session.targetDocument,
      context: {
        id: painterContext.id,
        texture_set: painterContext.textureSet,
        stack: painterContext.stack,
        channel: painterContext.channel,
        channel_label: painterContext.channelLabel,
      },
    },
    transfers: state.mappings.map((mapping, order) => ({
      order,
      direction: mapping.direction,
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
    const kindText = textValue(layer.ps_kind) || "layer"
    const isGroup = /group/i.test(kindText)
    const group = textValue(layer.group)
    const relativeAsset = textValue(layer.png)
    const relativeMask = textValue(layer.mask_png)
    const resolvedAsset = relativeAsset ? resolveAsset(manifestDir, relativeAsset) : null
    const ref: HostLayerRef = {
      host: "photoshop",
      externalId,
      nativeId: textValue(layer.ps_layer_id) || externalId,
      kind: kindText,
      path: textValue(layer.path) || (group ? `${group}/${name}` : name),
      assetPath: resolvedAsset,
      maskPath: relativeMask ? resolveAsset(manifestDir, relativeMask) : null,
      blendMode: textValue(layer.blend_mode) || "normal",
      opacity: numberValue(layer.opacity, 100),
      visible: layer.visible !== false,
    }
    return {
      id: `photoshop:${externalId}`,
      kind: isGroup ? "group" : "layer",
      name,
      detail: isGroup ? "Group" : layerDetail(layer),
      masked: Boolean(relativeMask),
      thumbnailPath: availableThumbnail(resolvedAsset),
      ref,
    }
  })
}

function painterContexts(snapshot: JsonObject): PainterContext[] {
  if (snapshot.schema_version !== 1 || snapshot.request_type !== "painter_snapshot") {
    throw new Error("Painter snapshot must use the painter_snapshot schema_version 1 contract")
  }

  const contexts = arrayValue(snapshot.contexts).map((value, index) => {
    const record = objectValue(value)
    const textureSet = textValue(record.texture_set)
    const stack = textValue(record.stack)
    const channel = textValue(record.channel)
    const channelLabel = textValue(record.channel_label) || channel
    if (!textureSet || !channel) {
      throw new Error(`Painter snapshot context ${index + 1} is missing texture_set or channel`)
    }

    const nodes = requestNodes(arrayValue(record.layers), "", channel)
    if (nodes.length === 0) {
      throw new Error(`Painter snapshot context ${textureSet} / ${channelLabel} has no layers`)
    }
    return {
      id: painterContextId(textureSet, stack, channel),
      textureSet,
      stack,
      channel,
      channelLabel,
      subtitle: painterContextSubtitle(textureSet, stack, channelLabel),
      nodes,
    } satisfies PainterContext
  })

  const uniqueContexts = new Set(
    contexts.map((context) => painterContextKey(context.textureSet, context.stack, context.channel)),
  )
  if (uniqueContexts.size !== contexts.length) {
    throw new Error("Painter snapshot contains duplicate texture set / stack / channel contexts")
  }
  return contexts
}

function requestNodes(values: unknown[], parentPath: string, channel: string): LayerNode[] {
  return values.map((value, index) => {
    const node = objectValue(value)
    const name = textValue(node.name) || textValue(node.display_name) || `Layer ${index + 1}`
    const kindText = textValue(node.kind) || "layer"
    const childValues = arrayValue(node.children)
    const isGroup = /group/i.test(kindText) || childValues.length > 0
    const uid = textValue(node.uid_hex) || textValue(node.uid) || `${parentPath}:${index}`
    const nodePath = parentPath ? `${parentPath}/${name}` : name
    const resolvedAsset = assetPath(node.asset)
    return {
      id: `substance_painter:${uid}`,
      kind: isGroup ? "group" : "layer",
      name,
      detail: isGroup ? `${childValues.length} Layers` : layerDetail(node),
      masked: Boolean(node.mask_asset) || node.has_mask === true,
      thumbnailPath: availableThumbnail(resolvedAsset),
      ref: {
        host: "substance_painter",
        externalId: uid,
        nativeId: uid,
        kind: kindText,
        path: nodePath,
        assetPath: resolvedAsset,
        maskPath: assetPath(node.mask_asset),
        blendMode: textValue(node.ps_blend_mode) || textValue(node.blend_mode) || "normal",
        opacity: channelNumberValue(node.opacity, channel, 100),
        visible: node.visible !== false,
        hasMask: Boolean(node.mask_asset) || node.has_mask === true,
      },
      children: isGroup ? requestNodes(childValues, nodePath, channel) : undefined,
    } satisfies LayerNode
  })
}

function targetSnapshotFromSelection(selection: JsonObject, manifestPath: string): string {
  const explicit = textValue(selection.painter_snapshot)
  if (explicit) return resolveAsset(path.dirname(manifestPath), explicit)
  throw new Error("Pass --painter <snapshot> or include painter_snapshot in the Photoshop manifest")
}

function painterContextSubtitle(textureSet: string, stack: string, channel: string): string {
  const stackLabel = stack && stack !== textureSet ? `${textureSet} / ${stack}` : textureSet
  return `${stackLabel} · ${channel}`
}

function painterContextId(textureSet: string, stack: string, channel: string): string {
  return `ctx-${Buffer.from(painterContextKey(textureSet, stack, channel), "utf8").toString("base64url")}`
}

function painterContextKey(textureSet: string, stack: string, channel: string): string {
  return JSON.stringify([textureSet, stack, channel])
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
    id: ref.nativeId ?? ref.externalId,
    kind: ref.kind,
    path: ref.path,
    png: ref.assetPath ?? null,
    mask_png: ref.maskPath ?? null,
    blend_mode: ref.blendMode ?? null,
    opacity: ref.opacity ?? null,
    visible: ref.visible ?? null,
    has_mask: ref.hasMask === true,
  }
}

async function photoshopDocumentContext(
  selection: JsonObject,
  manifestPath: string,
): Promise<JsonObject> {
  const relativePath = textValue(selection.sidecar) || textValue(selection.painter_snapshot)
  if (!relativePath) return {}
  const sidecarPath = resolveAsset(path.dirname(manifestPath), relativePath)
  if (!existsSync(sidecarPath)) return {}
  const candidate = await readJsonObject(sidecarPath)
  return textValue(candidate.texture_set) && textValue(candidate.channel) ? candidate : {}
}

function matchingPainterContext(
  contexts: PainterContext[],
  sourceContext: JsonObject,
): PainterContext | null {
  const textureSet = textValue(sourceContext.texture_set)
  const stack = textValue(sourceContext.stack)
  const channel = textValue(sourceContext.channel)
  if (!textureSet || !channel) return null
  return (
    contexts.find(
      (context) =>
        context.textureSet === textureSet &&
        context.stack === stack &&
        context.channel === channel,
    ) ?? null
  )
}

function assetPath(value: unknown): string | null {
  return nullableText(objectValue(value).path)
}

function availableThumbnail(value: string | null): string | null {
  // Snapshot-only nodes often have no rendered asset; checking once at the
  // transport boundary prevents the native image host from painting a broken-file glyph.
  return value && existsSync(value) ? value : null
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

function channelNumberValue(value: unknown, channel: string, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) return value
  const values = objectValue(value)
  return numberValue(values[channel], numberValue(values.mask, fallback))
}
