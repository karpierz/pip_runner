# Copyright (c) 2026 Adam Karpierz
# SPDX-License-Identifier: Zlib

import unittest
import inspect
import threading
import platform
from pathlib import Path

from pip_runner._pip_cmd import PipCmd

here = Path(__file__).resolve().parent
data_dir = here/"data"


class PipCmdTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pip_cmd = PipCmd()
        cls.lock = threading.Lock()

    def setUp(self):
        self.lock.acquire()

    def tearDown(self):
        self.lock.release()

    ## Low-level pip API ##

    def test_api_surface(self):
        # ensure methods exist and are callable
        for method_name in (
            "py",
            "pip",
        ):
            method = getattr(self.pip_cmd, method_name)
            self.assertTrue(callable(method))
            self.assertTrue(inspect.ismethod(method))

    def test_py(self):
        output = self.pip_cmd.py(version=True, capture_output=True, text=True)
        version = output.stdout.strip().split(" ")[1].strip()
        self.assertEqual(version, platform.python_version())

    def test_pip(self):
        self.assertTrue(1 == 1)
