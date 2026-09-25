import { colors, metrics } from "./theme"

/**
 * The carried cards are drawn as one SVG picture. GPUiX has no transform, so
 * this is the only way the stack can tilt; its <img> decodes SVG in full
 * colour with text, where <svg> would paint a one-colour icon.
 */
export const dragCard = {
  width: 200,
  height: 30,
  /** The card's offset inside the picture, leaving room for tilt and shadow. */
  insetX: 22,
  insetY: 20,
  pictureWidth: 252,
  pictureHeight: 78,
}

type CarriedItem = { name: string; thumbnailPath?: string | null }

const escape = (text: string) =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")

// SVG text cannot ellipsize, so names are cut by an estimate of their width.
function fitted(name: string, width: number): string {
  let used = 0
  let end = 0
  for (const char of name) {
    const advance = /[⺀-￿]/.test(char) ? 13 : 7.2
    if (used + advance > width) return `${name.slice(0, end)}…`
    used += advance
    end += char.length
  }
  return name
}

export function dragCardPicture(items: readonly CarriedItem[], angle: number): string {
  const { width, height, insetX, insetY, pictureWidth, pictureHeight } = dragCard
  const first = items[0]
  const count = items.length
  const badge = count > 1 ? 26 : 0
  const back = [2, 1].filter(layer => layer < Math.min(count, 3)).map(layer => {
    const offset = layer * 4
    return `<rect x="${insetX + offset}" y="${insetY + offset}" width="${width}" height="${height}" rx="${metrics.rowRadius}"
      fill="${colors.control}" stroke="${colors.line}" opacity="${layer === 1 ? 0.7 : 0.45}"/>`
  }).join("")
  const thumb = first.thumbnailPath
    ? `<image x="${insetX + 8}" y="${insetY + 7}" width="16" height="16" href="${escape(first.thumbnailPath)}"/>`
    : `<rect x="${insetX + 8.5}" y="${insetY + 7.5}" width="15" height="15" rx="3" fill="none" stroke="${colors.thumbnailBorder}"/>`
  const label = escape(fitted(first.name, width - 40 - badge))
  const counter = count > 1
    ? `<rect x="${insetX + width - 8 - 20}" y="${insetY + 7}" width="20" height="16" rx="8" fill="${colors.text}"/>
       <text x="${insetX + width - 18}" y="${insetY + 19}" text-anchor="middle" font-size="11" font-weight="600"
         font-family="Segoe UI, sans-serif" fill="${colors.canvas}">${count}</text>`
    : ""
  const centerX = insetX + width / 2
  const centerY = insetY + height / 2
  // Drawn at twice its displayed size so it stays sharp on high-DPI screens.
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${pictureWidth * 2}" height="${pictureHeight * 2}"
    viewBox="0 0 ${pictureWidth} ${pictureHeight}">
    <defs><filter id="lift" x="-20%" y="-60%" width="140%" height="220%">
      <feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000000" flood-opacity="0.45"/>
    </filter></defs>
    <g transform="rotate(${angle} ${centerX} ${centerY})" filter="url(#lift)">
      ${back}
      <rect x="${insetX}" y="${insetY}" width="${width}" height="${height}" rx="${metrics.rowRadius}"
        fill="${colors.control}" stroke="${colors.line}"/>
      ${thumb}
      <text x="${insetX + 32}" y="${insetY + 19.5}" font-size="13"
        font-family="MiSans VF, Microsoft YaHei UI, Segoe UI, sans-serif" fill="${colors.text}">${label}</text>
      ${counter}
    </g></svg>`
}

export function dragCardSource(items: readonly CarriedItem[], angle: number): string {
  return `data:image/svg+xml;base64,${Buffer.from(dragCardPicture(items, angle)).toString("base64")}`
}
