import { existsSync } from "node:fs"
import { mkdir, readFile, rename, stat, unlink, writeFile } from "node:fs/promises"
import path from "node:path"
import type { Readable } from "node:stream"

import {
  emptyBridgeState,
  findNode,
  type BridgeState,
  type HostLayerRef,
  type LayerNode,
} from "./model"
import {
  clearTransferDirectory,
  readPhotoshopDocument,
  renderPhotoshopTransfer,
  type PhotoshopDocument,
} from "./psd"

type JsonObject = Record<string, unknown>

export type SessionOptions = {
  photoshopDocument?: string
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
  photoshop: PhotoshopDocument | null
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
    photoshopDocument: env.PT_BRIDGE_PHOTOSHOP_DOCUMENT,
    painterSnapshot: env.PT_BRIDGE_PAINTER_SNAPSHOT,
    output: env.PT_BRIDGE_TRANSFER_OUTPUT,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index]
    const value = argv[index + 1]
    if (!["--psd", "--painter", "--output"].includes(flag)) {
      throw new Error(`Unknown desktop argument: ${flag}`)
    }
    if (!value || value.startsWith("--")) {
      throw new Error(`Desktop argument ${flag} requires a path`)
    }

    if (flag === "--psd") values.photoshopDocument = value
    if (flag === "--painter") values.painterSnapshot = value
    if (flag === "--output") values.output = value
    index += 1
  }

  if (!values.painterSnapshot) {
    throw new Error("Pass --painter <painter_snapshot.json> to open PT Bridge")
  }
  return values
}

export async function loadBridgeSession(options: SessionOptions): Promise<BridgeSession> {
  if (!options.painterSnapshot) throw new Error("Pass --painter <painter_snapshot.json> to open PT Bridge")
  const targetSnapshotPath = path.resolve(options.painterSnapshot)
  const target = await readJsonObject(targetSnapshotPath)
  const photoshop = options.photoshopDocument
    ? await readPhotoshopDocument(options.photoshopDocument)
    : null
  const contexts = painterContexts(target)
  const sourceContext = photoshop ? await photoshopSidecar(photoshop.path) : {}
  const active = objectValue(target.active_context)
  const activeContexts = contexts.filter(context =>
    context.textureSet === textValue(active.texture_set) && context.stack === textValue(active.stack))
  // Painter's current working stack takes priority over the connected PSD's origin.
  // Older snapshots have no active context and keep their document-based selection.
  const initialContext = activeContexts.length
    ? matchingPainterContext(activeContexts, sourceContext) ?? activeContexts[0]
    : matchingPainterContext(contexts, sourceContext) ?? contexts[0]
  if (!initialContext) throw new Error("Painter snapshot has no addressable contexts")

  const outputPath = path.resolve(
    options.output ?? path.join(path.dirname(targetSnapshotPath), "desktop_transfer.json"),
  )

  return {
    state: { photoshop: photoshop?.nodes ?? [], painter: initialContext.nodes, mappings: [] },
    photoshop,
    targetSnapshotPath,
    outputPath,
    photoshopSubtitle: photoshop ? photoshop.name : "No document connected",
    painterContexts: contexts,
    initialPainterContextId: initialContext.id,
    status: photoshop
      ? "Drag layers between Photoshop and Painter to map a transfer"
      : "Connect Photoshop to start mapping layers",
    sourceDocument: photoshop ? { name: photoshop.name, path: photoshop.path } : {},
    sourceContext,
    targetDocument: objectValue(target.project),
  }
}

export function failedBridgeSession(error: unknown): BridgeSession {
  const message = error instanceof Error ? error.message : String(error)
  return {
    state: structuredClone(emptyBridgeState),
    photoshop: null,
    targetSnapshotPath: "",
    outputPath: "",
    photoshopSubtitle: "No document connected",
    painterContexts: [],
    initialPainterContextId: "",
    status: message,
    sourceDocument: {},
    sourceContext: {},
    targetDocument: {},
  }
}

// Painter owns the file picker and Photoshop automation, but the mapper stays
// open while Painter works so a connection never costs the user their window.
// The link shares stdio with GPUiX: GPUiX serves SSE automation whenever stdin
// is a pipe. Painter replies are single-line JSON, which the SSE parser ignores
// (they never start with "data:"), and the link listens on the same
// process.stdin stream because a second reader on fd 0 would split its bytes.
// Requests share stdout with SSE replies and console output, hence the marker.
export const PAINTER_REQUEST_MARKER = "@ptbridge "

export type PainterReply =
  | { type: "photoshop_connected"; psd: string }
  | { type: "photoshop_connect_cancelled" }
  | { type: "photoshop_connect_failed"; message: string }

export type PainterLink = {
  request: (type: "connect_photoshop") => Promise<PainterReply>
}

export function createPainterLink(
  input: Readable,
  write: (line: string) => void,
): PainterLink {
  let waiting: { resolve: (reply: PainterReply) => void; reject: (error: Error) => void } | null = null
  let closed = false
  let buffer = ""

  const settle = (outcome: PainterReply | Error) => {
    const current = waiting
    waiting = null
    if (!current) return
    if (outcome instanceof Error) current.reject(outcome)
    else current.resolve(outcome)
  }
  const close = () => {
    closed = true
    settle(new Error("Painter closed the Bridge connection"))
  }

  input.on("data", (chunk: string | Uint8Array) => {
    buffer += typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf8")
    for (let newline = buffer.indexOf("\n"); newline >= 0; newline = buffer.indexOf("\n")) {
      const line = buffer.slice(0, newline).trim()
      buffer = buffer.slice(newline + 1)
      if (line.startsWith("{")) settle(parsePainterReply(line))
    }
  })
  input.on("end", close)
  input.on("error", close)

  return {
    request(type) {
      if (closed) return Promise.reject(new Error("Painter closed the Bridge connection"))
      if (waiting) return Promise.reject(new Error("A Painter request is already pending"))
      return new Promise((resolve, reject) => {
        waiting = { resolve, reject }
        write(`${PAINTER_REQUEST_MARKER}${JSON.stringify({ type })}\n`)
      })
    },
  }
}

function parsePainterReply(line: string): PainterReply | Error {
  let reply: JsonObject
  try {
    reply = objectValue(JSON.parse(line))
  } catch {
    return new Error("Painter sent an unreadable Bridge reply")
  }
  if (reply.type === "photoshop_connected" && textValue(reply.psd)) {
    return { type: "photoshop_connected", psd: textValue(reply.psd) }
  }
  if (reply.type === "photoshop_connect_cancelled") return { type: "photoshop_connect_cancelled" }
  if (reply.type === "photoshop_connect_failed") {
    return { type: "photoshop_connect_failed", message: textValue(reply.message) || "Photoshop connection failed" }
  }
  return new Error(`Painter sent an unsupported Bridge reply: ${String(reply.type)}`)
}

/** Resolves the reconnected session, or null when the user cancelled Painter's picker. */
export async function connectPhotoshop(
  session: BridgeSession,
  link: PainterLink,
): Promise<BridgeSession | null> {
  const reply = await link.request("connect_photoshop")
  if (reply.type === "photoshop_connect_cancelled") return null
  if (reply.type === "photoshop_connect_failed") throw new Error(reply.message)
  return loadBridgeSession({
    photoshopDocument: reply.psd,
    painterSnapshot: session.targetSnapshotPath,
    output: session.outputPath,
  })
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

  // Photoshop pixels are rendered only for what the user mapped, at Apply.
  const assets = path.join(path.dirname(session.outputPath), "photoshop_assets")
  if (state.mappings.some(mapping => mapping.direction === "photoshop_to_painter")) {
    await clearTransferDirectory(assets)
  }
  const warnings: string[] = []
  const transfers = []
  for (const [order, mapping] of state.mappings.entries()) {
    let source: unknown = manifestRef(mapping.source)
    if (mapping.direction === "photoshop_to_painter") {
      const node = findNode(state.painter, mapping.sourceId)
      if (!node || !session.photoshop) throw new Error("A mapped Photoshop layer is no longer available")
      source = await renderPhotoshopTransfer(session.photoshop, node, assets, warnings)
    }
    transfers.push({
      order,
      direction: mapping.direction,
      source,
      target: manifestRef(mapping.target),
      insertion: mapping.placement,
    })
  }

  const payload = {
    schema_version: 3,
    request_type: "desktop_transfer",
    created_at: new Date().toISOString(),
    photoshop: {
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
    transfers,
    warnings,
  }

  await writeAtomicJson(session.outputPath, payload)
  return session.outputPath
}

async function writeAtomicJson(filePath: string, payload: unknown): Promise<void> {
  const directory = path.dirname(filePath)
  try {
    await mkdir(directory, { recursive: true })
  } catch (error) {
    // Bun can report EEXIST for existing OneDrive reparse directories. Verify
    // the directory rather than ignoring real file conflicts or access failures.
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error
    const existing = await stat(directory).catch(() => null)
    if (!existing?.isDirectory()) throw error
  }
  const temporaryPath = `${filePath}.tmp-${process.pid}`
  await writeFile(temporaryPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8")
  await unlink(filePath).catch((error: NodeJS.ErrnoException) => {
    if (error.code !== "ENOENT") throw error
  })
  // Painter watches this contract after the desktop exits, so replacement must be atomic.
  await rename(temporaryPath, filePath)
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
    // A Photoshop layer without a persistent id is addressed by index_path.
    id: ref.host === "photoshop" ? ref.nativeId ?? null : ref.nativeId ?? ref.externalId,
    kind: ref.kind,
    path: ref.path,
    png: ref.assetPath ?? null,
    mask_png: ref.maskPath ?? null,
    blend_mode: ref.blendMode ?? null,
    opacity: ref.opacity ?? null,
    visible: ref.visible ?? null,
    has_mask: ref.hasMask === true,
    index_path: ref.indexPath ?? null,
  }
}

async function photoshopSidecar(psdPath: string): Promise<JsonObject> {
  // Written by the Photoshop build next to each PSD it saves.
  const sidecarPath = psdPath.replace(/\.[^.\\/]*$/, "") + ".rizum.json"
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
