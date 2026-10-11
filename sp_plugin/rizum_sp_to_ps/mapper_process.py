"""The native mapper's process, started so it holds none of Painter's files."""

from __future__ import annotations

import subprocess
import sys
import threading
from functools import lru_cache


@lru_cache(maxsize=None)
def mapper_process_class(QtCore):
    """Build the process class for the Qt binding Painter provides."""

    class MapperProcess(QtCore.QObject):
        """
        The mapper talks over its stdio pipes, so it has to inherit them. A
        QProcess child inherits every inheritable handle Painter holds, and
        Painter keeps the open project's .spp open: while the mapper ran,
        Painter could not move the .spp aside on save and crashed. Popen with
        close_fds hands Windows an explicit list of just the three pipes.
        """

        output = QtCore.Signal(bytes)
        # Exit code and everything the mapper wrote to stderr.
        finished = QtCore.Signal(int, str)

        def __init__(self, executable, arguments, interrupt_line=None):
            super().__init__()
            self._command = [str(executable), *map(str, arguments)]
            self._popen = None
            # Set by the reader thread itself when the mapper writes
            # interrupt_line. Painter renders on its UI thread, so the output
            # signal would only arrive once the work it asks to stop is done.
            self._interrupt_line = interrupt_line
            self.interrupted = threading.Event()

        def start(self):
            """Start the mapper; raises OSError when it cannot start. Connect signals first."""
            self._popen = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                # The mapper is a console program; Painter must not open a console for it.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            errors = []
            stderr = threading.Thread(target=lambda: errors.append(self._popen.stderr.read()), daemon=True)
            stderr.start()
            threading.Thread(target=self._pump, args=(stderr, errors), daemon=True).start()

        def _pump(self, stderr, errors):
            # Signals cross to Painter's thread queued and in order, so every
            # output chunk is handled before finished.
            pending = b""
            for chunk in iter(lambda: self._popen.stdout.read1(65536), b""):
                if self._interrupt_line is not None:
                    *lines, pending = (pending + chunk).split(b"\n")
                    if any(line.strip() == self._interrupt_line for line in lines):
                        self.interrupted.set()
                self.output.emit(chunk)
            stderr.join()
            code = self._popen.wait()
            self.finished.emit(code, b"".join(errors).decode("utf-8", errors="replace").strip())

        def write(self, data):
            try:
                self._popen.stdin.write(data)
                self._popen.stdin.flush()
            except (OSError, ValueError):
                # The mapper has exited; its finished signal is already on the way.
                pass

        def bring_to_front(self):
            """Raise the mapper's window, restoring it if minimized. Windows only."""
            if sys.platform != "win32" or self._popen is None:
                return
            import ctypes
            from ctypes import wintypes

            # Windows lets only the foreground process hand focus on. Painter
            # is that process when its Bridge button is clicked, so it raises
            # the window itself; the mapper asking for focus would be refused.
            # A private library object, so these prototypes stay off the
            # functions other code reaches through ctypes.windll.
            user32 = ctypes.WinDLL("user32")
            visitor = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows.argtypes = [visitor, wintypes.LPARAM]
            user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            for name in ("IsWindowVisible", "IsIconic", "SetForegroundWindow"):
                getattr(user32, name).argtypes = [wintypes.HWND]
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            windows = []

            def visit(hwnd, _lparam):
                owner = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                if owner.value == self._popen.pid and user32.IsWindowVisible(hwnd):
                    windows.append(hwnd)
                return True

            user32.EnumWindows(visitor(visit), 0)
            for hwnd in windows:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)

        def stop(self, grace_seconds=0.8):
            if self._popen is None or self._popen.poll() is not None:
                return
            self._popen.terminate()
            try:
                self._popen.wait(grace_seconds)
            except subprocess.TimeoutExpired:
                self._popen.kill()

    return MapperProcess
