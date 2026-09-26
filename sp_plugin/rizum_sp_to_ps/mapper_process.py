"""The native mapper's process, started so it holds none of Painter's files."""

from __future__ import annotations

import subprocess
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

        def __init__(self, executable, arguments):
            super().__init__()
            self._command = [str(executable), *map(str, arguments)]
            self._popen = None

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
            for chunk in iter(lambda: self._popen.stdout.read1(65536), b""):
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

        def stop(self, grace_seconds=0.8):
            if self._popen is None or self._popen.poll() is not None:
                return
            self._popen.terminate()
            try:
                self._popen.wait(grace_seconds)
            except subprocess.TimeoutExpired:
                self._popen.kill()

    return MapperProcess
