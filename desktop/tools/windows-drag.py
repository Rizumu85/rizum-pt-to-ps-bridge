"""Post a Win32 drag to a test-owned window: windows-drag.py pid step..., step = down|move|up:x:y:pause_ms.

Messages go to the window, not the cursor, so the user's pointer is never moved.
"""

import ctypes
import sys
import time
from ctypes import wintypes

pid = int(sys.argv[1])
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetThreadDpiAwarenessContext.argtypes = [wintypes.HANDLE]
user32.SetThreadDpiAwarenessContext(wintypes.HANDLE(-4))
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
windows = []
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


@callback_type
def visit(hwnd, _):
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    if owner.value == pid and user32.IsWindowVisible(hwnd):
        windows.append(hwnd)
    return True


user32.EnumWindows(visit, 0)
hwnd = windows[0]
scale = user32.GetDpiForWindow(hwnd) / 96
for step in sys.argv[2:]:
    kind, x, y, pause = step.split(":")
    px, py = round(float(x) * scale), round(float(y) * scale)
    position = (py << 16) | (px & 0xFFFF)
    message, wparam = {"down": (0x0201, 1), "move": (0x0200, 1), "up": (0x0202, 0)}[kind]
    user32.PostMessageW(hwnd, message, wparam, position)
    time.sleep(float(pause) / 1000)
