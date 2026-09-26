import os
import sys
import tempfile
import unittest
from pathlib import Path

from PySide6 import QtCore

from sp_plugin.rizum_sp_to_ps.mapper_process import mapper_process_class


@unittest.skipUnless(sys.platform == "win32", "Handle inheritance is the Windows failure")
class MapperProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])

    def run_child(self, source, stdin=b""):
        process = mapper_process_class(QtCore)(sys.executable, ["-c", source])
        output, finished = [], []
        process.output.connect(output.append)
        process.finished.connect(lambda code, stderr: finished.append((code, stderr)))
        process.start()
        if stdin:
            process.write(stdin)
        deadline = QtCore.QDeadlineTimer(10000)
        while not finished and not deadline.hasExpired():
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        return b"".join(output), finished

    def test_child_holds_none_of_the_painters_open_files(self):
        # Painter keeps the open project's .spp open; a child that inherits the
        # handle blocks the save that moves it aside, and Painter crashed.
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project.spp"
            with open(project, "wb") as held:
                os.set_inheritable(held.fileno(), True)
                handle = __import__("msvcrt").get_osfhandle(held.fileno())
                # The child names whatever file that handle value points at in it.
                source = (
                    "import ctypes; buffer = ctypes.create_unicode_buffer(1024);"
                    f"size = ctypes.windll.kernel32.GetFinalPathNameByHandleW({handle}, buffer, 1024, 0);"
                    "print(buffer.value if size else '')"
                )
                output, finished = self.run_child(source)
        self.assertEqual(finished, [(0, "")])
        self.assertNotIn("project.spp", output.decode())

    def test_pipes_carry_stdin_stdout_and_stderr_in_order(self):
        source = "import sys; line = sys.stdin.readline(); print('got', line.strip()); sys.stderr.write('warn'); sys.exit(3)"
        output, finished = self.run_child(source, stdin=b"hello\n")
        self.assertEqual(output.decode().strip(), "got hello")
        self.assertEqual(finished, [(3, "warn")])


if __name__ == "__main__":
    unittest.main()
