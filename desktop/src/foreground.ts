import { dlopen, FFIType } from "bun:ffi"

const ASFW_ANY = 0xffffffff

// Windows lets only the foreground process hand focus to another process. The
// mapper is foreground when the user clicks Connect and stays open behind
// Painter's picker, so it must grant that right first or the picker can open
// hidden behind this window.
export function allowPainterForeground(): void {
  if (process.platform !== "win32") return
  const user32 = dlopen("user32.dll", {
    AllowSetForegroundWindow: { args: [FFIType.u32], returns: FFIType.bool },
  })
  try {
    user32.symbols.AllowSetForegroundWindow(ASFW_ANY)
  } finally {
    user32.close()
  }
}
