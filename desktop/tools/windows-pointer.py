"""Send Win32 input to a test-owned window; physical-click opts into cursor input."""

import ctypes
import sys
import time
from ctypes import wintypes


pid, action, x, y = sys.argv[1:]
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetThreadDpiAwarenessContext.argtypes = [wintypes.HANDLE]
user32.SetThreadDpiAwarenessContext(wintypes.HANDLE(-4))
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.IsWindowVisible.argtypes = [wintypes.HWND]
windows = []
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


@callback_type
def visit(hwnd, _):
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    if owner.value == int(pid) and user32.IsWindowVisible(hwnd):
        windows.append(hwnd)
    return True


user32.EnumWindows(visit, 0)
if not windows:
    raise RuntimeError("Test process has no window")
hwnd = windows[0]
scale = user32.GetDpiForWindow(hwnd) / 96
px, py = round(float(x) * scale), round(float(y) * scale)
position = (py << 16) | (px & 0xffff)
user32.PostMessageW(hwnd, 0x0200, 0, position)
time.sleep(0.15)
if action == "physical-click":
    previous = user32.GetForegroundWindow()
    cursor = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(cursor))
    point = wintypes.POINT(px, py)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    try:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Test window did not acquire foreground")
        user32.SetCursorPos(point.x, point.y)
        time.sleep(0.2)
        user32.mouse_event(2, 0, 0, 0, 0)
        time.sleep(0.15)
        user32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(0.2)
    finally:
        user32.SetCursorPos(cursor.x, cursor.y)
        user32.SetForegroundWindow(previous)
elif action == "click":
    user32.PostMessageW(hwnd, 0x0201, 1, position)
    time.sleep(0.15)
    user32.PostMessageW(hwnd, 0x0202, 0, position)
elif action == "wheel":
    point = wintypes.POINT(px, py)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    screen = ((point.y & 0xffff) << 16) | (point.x & 0xffff)
    user32.PostMessageW(hwnd, 0x020A, ((-360 & 0xffff) << 16), screen)
elif action != "hover":
    raise ValueError(action)
