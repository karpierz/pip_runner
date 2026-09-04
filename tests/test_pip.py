# Copyright (c) 2026 Adam Karpierz
# SPDX-License-Identifier: Zlib

import unittest
from unittest import mock
import os
import inspect
import tempfile
import threading
import platform
from pathlib import Path
import logging

from utlx import run

import pip_runner
from pip_runner import Pip

is_graalpy = (platform.python_implementation().lower() == "graalvm")

here = Path(__file__).resolve().parent
data_dir = here/"data"


class PipTestCase(unittest.TestCase):

    pip_commands = (
        "install",
        "lock",
        "download",
        "uninstall",
        "freeze",
        "inspect",
        "list",
        "show",
        "check",
        "config",
        "search",
        "cache",
        "index",
        "wheel",
        "hash",
        "completion",
        "debug",
        "help",
    )

    @classmethod
    def setUpClass(cls):
        cls.pip = Pip()
        cls.lock = threading.Lock()
        # os.environ["PIP_CONFIG_FILE"] = str(data_dir/"pip.ini")

    def setUp(self):
        self.lock.acquire()

    def tearDown(self):
        self.lock.release()

    ### High-level API ###

    def test_api_surface(self):
        # ensure methods exist and are callable
        attr = inspect.getattr_static(self.pip, "version")
        self.assertIsInstance(attr, property)
        attr = inspect.getattr_static(self.pip, "version_info")
        self.assertIsInstance(attr, property)
        for method_name in (
            "pip",
            "help",
            "install",
            "upgrade",
            "download",
            "lock",
            "wheel",
            "uninstall",
            "list",
            "freeze",
            "inspect",
            "show",
            "check",
            "config",
            "config_list",
            "config_edit",
            "config_get",
            "config_set",
            "config_unset",
            "config_debug",
            "cache",
            "cache_dir",
            "cache_info",
            "cache_list",
            "cache_remove",
            "cache_purge",
            "search",
            "index",
            "hash",
            "completion",
            "debug",
            "command_exists",
        ):
            method = getattr(self.pip, method_name)
            self.assertTrue(callable(method))
            self.assertTrue(inspect.ismethod(method))

    def test_version(self):
        """Gets the pip version."""
        version = self.pip.version
        self.assertIsInstance(version, str)
        print(flush=True)
        print("PIP VERSION:", version)

    def test_version_info(self):
        """Gets the pip version info."""
        version_info = self.pip.version_info
        self.assertIsInstance(version_info, pip_runner.version_info)
        self.assertIsInstance(version_info.major, int)
        self.assertIsInstance(version_info.minor, int)
        self.assertIsInstance(version_info.micro, int)

    @mock.patch.object(Pip, "version", new_callable=mock.PropertyMock)
    def test_version_info_valid_format(self, mock_version):
        """Test version_info with valid version string."""

        mock_version.return_value = "pip 24.0.1 from /path/to/pip"
        version_info = self.pip.version_info
        self.assertIsInstance(version_info, pip_runner.version_info)
        self.assertEqual(version_info, pip_runner.version_info("24.0.1"))
        self.assertEqual(version_info.major, 24)
        self.assertEqual(version_info.minor, 0)
        self.assertEqual(version_info.micro, 1)

        mock_version.return_value = "pip 24.0"
        version_info = self.pip.version_info
        self.assertIsInstance(version_info, pip_runner.version_info)
        self.assertEqual(version_info, pip_runner.version_info("24.0"))
        self.assertEqual(version_info.major, 24)
        self.assertEqual(version_info.minor, 0)
        self.assertEqual(version_info.micro, 0)

        mock_version.return_value = "pip 24.0.1rc1 from /path/to/pip"
        version_info = self.pip.version_info
        self.assertIsInstance(version_info, pip_runner.version_info)
        self.assertEqual(version_info, pip_runner.version_info("24.0.1rc1"))
        self.assertEqual(version_info.major, 24)
        self.assertEqual(version_info.minor, 0)
        self.assertEqual(version_info.micro, 1)

    @mock.patch.object(Pip, "version", new_callable=mock.PropertyMock)
    def test_version_info_invalid_format_raises_value_error(self, mock_version):
        """Test version_info raises ValueError with invalid format."""

        mock_version.return_value = "invalid-format-no-numbers"
        with self.assertRaises(self.pip.ValueError) as context:
            _ = self.pip.version_info
        self.assertTrue(str(context.exception).startswith("Unable to parse pip version"))

        mock_version.return_value = ""
        with self.assertRaises(self.pip.ValueError) as context:
            _ = self.pip.version_info
        self.assertTrue(str(context.exception).startswith("Unable to parse pip version"))

        mock_version.return_value = "pip version something"
        with self.assertRaises(self.pip.ValueError) as context:
            _ = self.pip.version_info
        self.assertTrue(str(context.exception).startswith("Unable to parse pip version"))

    def test_pip(self):
        output = self.pip.pip(version=True, capture_output=True).stdout
        self.assertIsInstance(output, str)
        self.assertEqual(output.strip(), self.pip.version)
        output = self.pip.pip("show", "packaging", capture_output=True).stdout
        self.assertIsInstance(output, str)
        # without output capture
        output = self.pip.pip(version=True, capture_output=False).stdout
        self.assertIsNone(output)
        output = self.pip.pip("show", "packaging", capture_output=False).stdout
        self.assertIsNone(output)

    def test_help(self):
        help_text = self.pip.help()
        self.assertIsInstance(help_text, str)
        for command in self.pip_commands:
            if not self.pip.command_exists(command):
                continue  # pragma: no cover
            help_text = self.pip.help(command)
            self.assertIsInstance(help_text, str)
        # without output capture
        help_text = self.pip.help(capture_output=False)
        self.assertIsNone(help_text)
        for command in self.pip_commands:
            if not self.pip.command_exists(command):
                continue  # pragma: no cover
            help_text = self.pip.help(command, capture_output=False)
            self.assertIsNone(help_text)

    def test_install_upgrade_uninstall(self):
        try:
            install = self.pip.install("renumerate")
            self.assertIsNone(install)
        finally:
            uninstall = self.pip.uninstall("renumerate")
            self.assertIsNone(uninstall)
        # with output capture
        try:
            install = self.pip.install("renumerate", capture_output=True)
            self.assertIsNone(install)
        finally:
            uninstall = self.pip.uninstall("renumerate", capture_output=True)
            self.assertIsNone(uninstall)
        # test upgrade
        try:
            install = self.pip.install("renumerate==2.3.0")
            self.assertIsNone(install)
            upgrade = self.pip.upgrade("renumerate")
            self.assertIsNone(upgrade)
        finally:
            uninstall = self.pip.uninstall("renumerate")
            self.assertIsNone(uninstall)
        # with output capture
        try:
            install = self.pip.install("renumerate==2.3.0", capture_output=True)
            self.assertIsNone(install)
            upgrade = self.pip.upgrade("renumerate", capture_output=True)
            self.assertIsNone(upgrade)
        finally:
            uninstall = self.pip.uninstall("renumerate", capture_output=True)
            self.assertIsNone(uninstall)

    def test_download(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            download = self.pip.download("packaging", dest=temp_dir)
            self.assertIsNone(download)
        # with output capture
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            download = self.pip.download("packaging", dest=temp_dir, capture_output=True)
            self.assertIsNone(download)

    def test_lock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            try:
                lock = self.pip.lock("packaging", output=temp_dir/"pylock.toml")
            except self.pip.NotImplementedError as exc:  # pragma: no cover
                self.assertIn("command 'lock' is not implemented ", str(exc))
                logging.info(str(exc))
            else:
                self.assertIsNone(lock)
        # with output capture
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            try:
                lock = self.pip.lock("packaging", output=temp_dir/"pylock.toml",
                                     capture_output=True)
            except self.pip.NotImplementedError as exc:  # pragma: no cover
                self.assertIn("command 'lock' is not implemented ", str(exc))
                logging.info(str(exc))
            else:
                self.assertIsNone(lock)

    def test_wheel(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            wheel = self.pip.wheel("packaging", wheel_dir=temp_dir)
            self.assertIsNone(wheel)
        # with output capture
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            wheel = self.pip.wheel("packaging", wheel_dir=temp_dir, capture_output=True)
            self.assertIsNone(wheel)

    def test_installed(self):
        installed = self.pip.list(verbose=True)
        pkg = installed["packaging"]
        self.assertIsInstance(pkg.name, str)
        self.assertIsInstance(pkg.get("name"), str)
        self.assertTrue("name" in pkg)
        self.assertIsInstance(pkg.version, str)
        self.assertIsInstance(pkg.get("version"), str)
        self.assertTrue("version" in pkg)
        self.assertFalse("nonexistent_attribute" in pkg)
        self.assertIsInstance(pkg.editable, bool)
        # without output capture
        installed = self.pip.list(verbose=True, capture_output=False)
        self.assertIsNone(installed)

    def test_list(self):
        installed = self.pip.list()
        pkg = installed["packaging"]
        self.assertIsInstance(pkg.name, str)
        self.assertIsInstance(pkg.get("name"), str)
        self.assertTrue("name" in pkg)
        self.assertIsInstance(pkg.version, str)
        self.assertIsInstance(pkg.get("version"), str)
        self.assertTrue("version" in pkg)
        self.assertFalse("nonexistent_attribute" in pkg)
        self.assertIsInstance(pkg.editable, bool)
        # without output capture
        installed = self.pip.list(capture_output=False)
        self.assertIsNone(installed)

    def test_freeze(self):
        freeze_items = self.pip.freeze()
        self.assertIsInstance(freeze_items, list)
        # without output capture
        freeze_items = self.pip.freeze(capture_output=False)
        self.assertIsNone(freeze_items)

    def test_parse_freeze_simple(self):
        output = run.CompletedTextProcess(args=["python", "-m", "pip", "freeze"], returncode=0)
        output.stdout = "requests==2.31.0\nnumpy==1.27.0"
        parsed = self.pip._parse_freeze(output)
        self.assertIn("requests==2.31.0", parsed)
        self.assertIn("numpy==1.27.0", parsed)

    def test_parse_freeze_extra(self):
        output = run.CompletedTextProcess(args=["python", "-m", "pip", "freeze"], returncode=0)
        output.stdout = "editable-package @ file:///some/path\nSomeProject"
        parsed = self.pip._parse_freeze(output)
        self.assertIn("editable-package @ file:///some/path", parsed)
        self.assertIn("SomeProject", parsed)

    def test_inspect(self):
        inspect_info = self.pip.inspect()
        self.assertIsInstance(inspect_info, dict)
        # without output capture
        inspect_info = self.pip.inspect(capture_output=False)
        self.assertIsNone(inspect_info)

    def test_show(self):
        packages = self.pip.show("packaging", "pkg_about")
        self.assertEqual(packages["packaging"].name, "packaging")
        self.assertIs(packages["packaging"].editable, False)
        self.assertEqual(packages["pkg_about"].name, "pkg_about")
        self.assertIs(packages["pkg_about"].editable, False)
        packages = self.pip.show("packaging", "pkg_about", files=True)
        self.assertEqual(packages["packaging"].name, "packaging")
        self.assertIs(packages["packaging"].editable, False)
        self.assertEqual(packages["pkg_about"].name, "pkg_about")
        self.assertIs(packages["pkg_about"].editable, False)
        # for coverage only
        try:
            self.pip.install("beartype==0.22.9")
            packages = self.pip.show("beartype")
            self.assertEqual(packages["beartype"].name, "beartype")
        finally:
            self.pip.uninstall("beartype")
        # without output capture
        packages = self.pip.show("packaging", "pkg_about", capture_output=False)
        self.assertIsNone(packages)

    def test_check(self):
        output_error, output_text = self.pip.check()
        self.assertIsInstance(output_error, int)
        self.assertIsInstance(output_text, str)
        # without output capture
        output_error, output_text = self.pip.check(capture_output=False)
        self.assertIsInstance(output_error, int)
        self.assertIsNone(output_text)

    def test_config(self):
        config_list = self.pip.config_list()
        with self.assertRaises(self.pip.NotImplementedError):
            config_edit = self.pip.config_edit()
        # self.assertIsNone(config_edit)
        config_get = self.pip.config_get("global.timeout", global_=True)
        self.assertEqual(config_get, "120")
        # config_set = self.pip.config_set("option", "value")
        # self.assertIsNone(config_set)
        # config_unset = self.pip.config_unset("option")
        # self.assertIsNone(config_unset)
        config_debug = self.pip.config_debug()
        config_list1 = self.pip.config("list")
        with self.assertRaises(self.pip.NotImplementedError):
            config_edit1 = self.pip.config("edit")
        # self.assertIsNone(config_edit1)
        config_get1 = self.pip.config("get", "global.timeout", global_=True)
        self.assertEqual(config_get1, "120")
        # config_set1 = self.pip.config("set", "option", "value")
        # self.assertIsNone(config_set1)
        # config_unset1 = self.pip.config("unset", "option")
        # self.assertIsNone(config_unset1)
        config_debug1 = self.pip.config("debug")
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.config("unknown command!")
        # without output capture
        config_list = self.pip.config_list(capture_output=False)
        self.assertIsNone(config_list)
        with self.assertRaises(self.pip.NotImplementedError):
            config_edit = self.pip.config_edit(capture_output=False)
        # self.assertIsNone(config_edit)
        config_get = self.pip.config_get("global.timeout", global_=True, capture_output=False)
        self.assertIsNone(config_get)
        # config_set = self.pip.config_set("option", "value", capture_output=False)
        # self.assertIsNone(config_set)
        # config_unset = self.pip.config_unset("option", capture_output=False)
        # self.assertIsNone(config_unset)
        config_debug = self.pip.config_debug(capture_output=False)
        self.assertIsNone(config_debug)
        config_list1 = self.pip.config("list", capture_output=False)
        self.assertIsNone(config_list1)
        with self.assertRaises(self.pip.NotImplementedError):
            config_edit1 = self.pip.config("edit", capture_output=False)
        # self.assertIsNone(config_edit1)
        config_get1 = self.pip.config("get", "global.timeout", global_=True, capture_output=False)
        self.assertIsNone(config_get1)
        # config_set1 = self.pip.config("set", "option", "value", capture_output=False)
        # self.assertIsNone(config_set1)
        # config_unset1 = self.pip.config("unset", "option", capture_output=False)
        # self.assertIsNone(config_unset1)
        config_debug1 = self.pip.config("debug", capture_output=False)
        self.assertIsNone(config_debug1)
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.config("unknown command!")

    @unittest.skipIf(is_graalpy,
                     "This test is skipped on GraalPy because GraalPy has a pip bug")
    def test_cache(self):
        cache_dir = self.pip.cache_dir()
        self.assertIsInstance(cache_dir, Path)
        cache_info = self.pip.cache_info()
        self.assertIsInstance(cache_info, pip_runner.CacheInfoResult)
        cache_paths = self.pip.cache_list("packaging*")
        self.assertIsInstance(cache_paths, list)
        cache_removes = self.pip.cache_remove("pkg_about")
        self.assertIsInstance(cache_removes, pip_runner.CacheRemoveResult)
        cache_purges = self.pip.cache_purge()
        self.assertIsInstance(cache_purges, pip_runner.CacheRemoveResult)
        cache_dir1 = self.pip.cache("dir")
        self.assertIsInstance(cache_dir1, Path)
        cache_info1 = self.pip.cache("info")
        self.assertIsInstance(cache_info1, pip_runner.CacheInfoResult)
        cache_paths1 = self.pip.cache("list", "packaging*")
        self.assertIsInstance(cache_paths1, list)
        cache_removes1 = self.pip.cache("remove", "pkg_about")
        self.assertIsInstance(cache_removes1, pip_runner.CacheRemoveResult)
        cache_purges1 = self.pip.cache("purge")
        self.assertIsInstance(cache_purges1, pip_runner.CacheRemoveResult)
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.cache("unknown command!")
        # without output capture
        cache_dir = self.pip.cache_dir(capture_output=False)
        self.assertIsNone(cache_dir)
        cache_info = self.pip.cache_info(capture_output=False)
        self.assertIsNone(cache_info)
        cache_paths = self.pip.cache_list("packaging*", capture_output=False)
        self.assertIsNone(cache_paths)
        cache_removes = self.pip.cache_remove("pkg_about", capture_output=False)
        self.assertIsNone(cache_removes)
        cache_purges = self.pip.cache_purge(capture_output=False)
        self.assertIsNone(cache_purges)
        cache_dir1 = self.pip.cache("dir", capture_output=False)
        self.assertIsNone(cache_dir1)
        cache_info1 = self.pip.cache("info", capture_output=False)
        self.assertIsNone(cache_info1)
        cache_paths1 = self.pip.cache("list", "packaging*", capture_output=False)
        self.assertIsNone(cache_paths1)
        cache_removes1 = self.pip.cache("remove", "pkg_about", capture_output=False)
        self.assertIsNone(cache_removes1)
        cache_purges1 = self.pip.cache("purge", capture_output=False)
        self.assertIsNone(cache_purges1)
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.cache("unknown command!", capture_output=False)

    def test_search(self):
        with self.assertRaises(self.pip.NotImplementedError):
            self.pip.search("packaging")
        # without output capture
        with self.assertRaises(self.pip.NotImplementedError):
            self.pip.search("packaging", capture_output=False)

    def test_index(self):
        versions = self.pip.index("versions", "packaging")
        self.assertIsInstance(versions, pip_runner.PackageVersions)
        output = self.pip.pip("index", "versions", "packaging", json=False, capture_output=True)
        versions = self.pip._parse_index_versions(output)
        self.assertIsInstance(versions, pip_runner.PackageVersions)
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.index("unknown action!", "packaging")
        # without output capture
        versions = self.pip.index("versions", "packaging", capture_output=False)
        self.assertIsNone(versions)
        if self.pip.version_info >= pip_runner.version_info("25.1"):  # pragma: no branch
            versions = self.pip.index("versions", "packaging", json=True, capture_output=False)
            self.assertIsNone(versions)
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.index("unknown action!", "packaging", capture_output=False)

    def test_hash(self):
        file1 = data_dir/"file1.txt"
        file2 = data_dir/"file2.txt"
        hashes = self.pip.hash(file1, file2, algorithm="sha256")
        self.assertIsInstance(hashes, dict)
        hash1 = hashes.get(str(file1))
        hash2 = hashes.get(str(file2))
        self.assertIsInstance(hash1, pip_runner.FileHash)
        self.assertIsInstance(hash2, pip_runner.FileHash)
        hash1_expected = "3FB53178A1E506BABBD3AF1AD8D3EA5AA713FC5C5F196CDE52A211A557365FBE"
        hash2_expected = "024036C13FAF551595138539F3C1228A725B2EA89BECF1E17FDF37D85F904372"
        self.assertEqual(hash1.hash, hash1_expected.lower())
        self.assertEqual(hash2.hash, hash2_expected.lower())
        with self.assertRaises(self.pip.RuntimeError):
            self.pip.hash(file1, file2, algorithm="???")
        # without output capture
        hashes = self.pip.hash(file1, file2, algorithm="sha256", capture_output=False)
        self.assertIsNone(hashes)

    def test_completion(self):
        completion_text = self.pip.completion(powershell=True)
        self.assertIsInstance(completion_text, str)
        with self.assertRaises(self.pip.ValueError):
            self.pip.completion()
        with self.assertRaises(self.pip.ValueError):
            self.pip.completion(unknown_arg=True)
        # without output capture
        completion_text = self.pip.completion(powershell=True, capture_output=False)
        self.assertIsNone(completion_text)
        with self.assertRaises(self.pip.ValueError):
            self.pip.completion(capture_output=False)
        with self.assertRaises(self.pip.ValueError):
            self.pip.completion(unknown_arg=True, capture_output=False)

    @unittest.skipIf(is_graalpy,
                     "This test is skipped on GraalPy because GraalPy has a pip bug")
    def test_debug(self):
        debug_info = self.pip.debug()
        self.assertIsInstance(debug_info, str)
        # without output capture
        debug_info = self.pip.debug(capture_output=False)
        self.assertIsNone(debug_info)

    def test_command_exists(self):
        self.assertTrue(self.pip.command_exists("install"))
        self.assertFalse(self.pip.command_exists("nonexistent_command"))
