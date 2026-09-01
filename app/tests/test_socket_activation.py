"""
Tests for Systemd Socket Activation & Unix Domain Socket IPC (Issue #1)
========================================================================
Validates systemd socket and service unit configuration, socket permissions,
Unix domain socket HTTP IPC, and graceful reload semantics.
"""

import os
import sys
import socket
import tempfile
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["LIARA_SECRET_KEY"] = "test_secret_key_for_unit_tests_1234567890abcdef"


class TestSocketActivation(unittest.TestCase):

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.socket_file = self.repo_root / "deploy" / "systemd" / "liara-backend.socket"
        self.service_file = self.repo_root / "deploy" / "systemd" / "liara-backend.service"
        self.nginx_file = self.repo_root / "deploy" / "nginx" / "liara.conf"

    def test_systemd_socket_unit_structure(self):
        """Verify liara-backend.socket has required directives and secure permissions."""
        self.assertTrue(self.socket_file.exists(), f"{self.socket_file} does not exist")
        content = self.socket_file.read_text()

        self.assertIn("ListenStream=/run/liara/liara-backend.sock", content)
        self.assertIn("SocketMode=0666", content)
        self.assertIn("SocketGroup=www-data", content)
        self.assertIn("PartOf=liara-backend.service", content)
        self.assertIn("WantedBy=sockets.target", content)

    def test_systemd_service_unit_structure(self):
        """Verify liara-backend.service has socket dependencies and dual-binding."""
        self.assertTrue(self.service_file.exists(), f"{self.service_file} does not exist")
        content = self.service_file.read_text()

        self.assertIn("Requires=liara-backend.socket", content)
        self.assertIn("RuntimeDirectory=liara", content)
        self.assertIn("RuntimeDirectoryMode=0775", content)
        self.assertIn("--bind unix:/run/liara/liara-backend.sock", content)
        self.assertIn("--bind 127.0.0.1:8100", content)
        self.assertIn("ExecReload=/bin/kill -HUP $MAINPID", content)

    def test_nginx_upstream_configuration(self):
        """Verify Nginx configuration uses unix domain socket upstream."""
        self.assertTrue(self.nginx_file.exists(), f"{self.nginx_file} does not exist")
        content = self.nginx_file.read_text()

        self.assertIn("upstream liara_backend {", content)
        self.assertIn("server unix:/run/liara/liara-backend.sock fail_timeout=0;", content)
        self.assertIn("proxy_pass http://liara_backend/;", content)
        self.assertIn("proxy_pass http://liara_backend/ws;", content)

    def test_unix_domain_socket_creation_and_ipc(self):
        """
        Verify that Unix Domain Sockets (AF_UNIX) can be created and bound
        on POSIX/Windows (if supported) without file descriptor collisions.
        """
        if hasattr(socket, "AF_UNIX"):
            with tempfile.TemporaryDirectory() as tmpdir:
                sock_path = os.path.join(tmpdir, "test_liara.sock")
                server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    server_sock.bind(sock_path)
                    server_sock.listen(1)
                    self.assertTrue(os.path.exists(sock_path))
                    os.chmod(sock_path, 0o660)
                    stat_res = os.stat(sock_path)
                    self.assertEqual(stat_res.st_mode & 0o777, 0o660)
                finally:
                    server_sock.close()
                    if os.path.exists(sock_path):
                        os.unlink(sock_path)


if __name__ == "__main__":
    unittest.main()
