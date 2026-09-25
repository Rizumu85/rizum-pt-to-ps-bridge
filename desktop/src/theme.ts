export const colors = {
  canvas: "#1B1B1B",
  panel: "#222222",
  control: "#2B2B2B",
  controlHover: "#363636",
  controlActive: "#404040",
  fieldHover: "#FFFFFF0D",
  mapped: "#303030",
  line: "#353535",
  text: "#E0E0E0",
  textHover: "#FFFFFF",
  textPressed: "#C4C4C4",
  secondary: "#9E9E9E",
  tertiary: "#666666",
  danger: "#FF453A",
  drop: "#E0E0E0",
  dropGhost: "#FFFFFF08",
  dropGhostBorder: "#E0E0E059",
  thumbnail: "#505050",
  thumbnailBorder: "#737373",
  maskDark: "#202020",
  maskLight: "#9B9B9B",
}

// The upstream GPUI preview remains the visual contract; keeping its tokens
// explicit here lets the real bridge evolve without importing preview runtime code.
export const typography = {
  family: "MiSans VF",
  primarySize: 13,
  primaryWeight: 400,
  labelSize: 12,
  labelWeight: 400,
  secondarySize: 11,
  secondaryWeight: 400,
}

export const metrics = {
  windowWidth: 700,
  minWindowHeight: 420,
  maxInitialHeight: 580,
  cardRadius: 8,
  rowRadius: 6,
  toolbarHeight: 43,
  rowHeight: 32,
  treeIndent: 18,
  dragThreshold: 5,
  panelGap: 16,
  contentPadding: 16,
}
