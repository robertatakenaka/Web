from unittest import (
    TestCase,
)

from xml_preproc.fs_commands import (
    RemoteCommands,
)


class TestRemoteCommands(TestCase):
    def setUp(self):
        self.rc = RemoteCommands("0.0.0.0:8000", "eu")

    def test_rsync(self):
        result = self.rc.rsync("source", "dest")
        self.assertEqual(
            result,
            'rsync  -e "ssh -p 8000"  -apu eu@0.0.0.0:source dest')

    def test_rsync_server_port(self):
        self.rc = RemoteCommands("0.0.0.0:8000")
        result = self.rc.rsync("source", "dest")
        self.assertEqual(
            result,
            'rsync  -e "ssh -p 8000"  -apu 0.0.0.0:source dest')

    def test_rsync_server_user(self):
        self.rc = RemoteCommands("0.0.0.0", "eu")
        result = self.rc.rsync("source", "dest")
        self.assertEqual(
            result,
            'rsync  -apu eu@0.0.0.0:source dest')

    def test_rsync_server(self):
        self.rc = RemoteCommands("0.0.0.0")
        result = self.rc.rsync("source", "dest")
        self.assertEqual(
            result,
            'rsync  -apu 0.0.0.0:source dest')

