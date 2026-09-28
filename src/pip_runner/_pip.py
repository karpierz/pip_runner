# Copyright (c) 2026 Adam Karpierz
# SPDX-License-Identifier: Zlib

from __future__ import annotations

from typing import TypeAlias, Any, NamedTuple
from typing import List  # due to conflict with builtins.list
from typing_extensions import Self, sentinel
from os import PathLike
from dataclasses import dataclass
from pathlib import Path
import builtins
import json
from textwrap import indent, dedent
from email.parser import Parser as EmailParser
from email.policy import Compat32 as EmailPolicy

import packaging.version
from utlx import public
from utlx import run
import regex as re

from ._vendor.pypi_simple import PyPISimple
from ._vendor.pypi_simple import IndexPage
from ._vendor.pypi_simple import ProjectPage, ProjectStatus
from ._vendor.pypi_simple import DistributionPackage
from ._pip_cmd import PipCmd

StrPath: TypeAlias = str | PathLike[str]

MISSING = sentinel("missing")

version_info = packaging.version.Version
public(version_info = version_info)
public(ProjectPage = ProjectPage)
public(ProjectStatus = ProjectStatus)
public(DistributionPackage = DistributionPackage)


@public
@dataclass(kw_only=True)
class Package:
    name: str
    version: str
    location: Path | None | sentinel = MISSING
    editable_project_location: Path | None = None
    latest_version:  str | sentinel = MISSING
    latest_filetype: str | sentinel = MISSING
    installer: str | sentinel = MISSING

    def get(self, key: str, default: Any = None) -> Any:
        """Like dict.get"""
        value = getattr(self, key, default)
        return value if value is not MISSING else default

    def __contains__(self, key: str) -> bool:
        """Allows usage: 'name' in obj"""
        return hasattr(self, key) and getattr(self, key) is not MISSING

    @property
    def editable(self) -> bool:
        return self.editable_project_location is not None


@public
class PackageInfo(NamedTuple):
    name: str
    version: str
    location: Path | None
    editable_project_location: Path | None
    requires: list[str]
    required_by: list[str]
    installer: str
    metadata_version: str
    classifiers: list[str]
    summary: str
    homepage: str
    project_urls: list[str]
    author: str
    author_email: str
    license: str  # noqa: A003
    license_expression: str
    entry_points: list[str]
    files: list[str] | None

    @property
    def editable(self) -> bool:
        return self.editable_project_location is not None


@public
@dataclass
class PackageVersions:
    name: str
    versions: list[str]
    latest: str | None
    installed: str | None


@public
@dataclass
class FileHash:
    file: Path
    hash: str  # noqa: A003
    algorithm: str


@public
class ConfigIniFile(NamedTuple):
    path: Path
    exists: bool
    config: dict[str, Any]


@public
class CacheInfoResult(NamedTuple):
    cache_location: Path | None
    cache_location_old: Path | None
    http_files_number: int
    built_wheels_location: Path | None
    built_wheels_number: int


@public
class CacheRemoveResult(NamedTuple):
    files: int
    directories: int


@public
class Pip:
    """High-level API for pip CLI (thin wrapper)."""

    cmd: PipCmd

    def __new__(cls, python_executable: str | None = None) -> Self:
        """Constructor"""
        self = super().__new__(cls)
        self.cmd = PipCmd(python_executable)
        return self

    ## High-level API ##

    @property
    def version(self) -> str:
        """Gets the pip version."""
        output = self.pip(version=True, capture_output=True)
        return output.stdout.strip()

    @property
    def version_info(self) -> version_info:
        """Gets the pip version info."""
        version = self.version
        match = re.match(r"((\w|\d)*\s+)*(?P<version>\d+\.\d+(\.\d+)?\S*)\s*", version)
        if match is None:
            raise self.ValueError(f"Unable to parse pip version: '{version}'")
        return packaging.version.parse(match.group("version"))

    def pip(self, *args: Any, **kwargs: Any) -> run.CompletedTextProcess:
        """Run raw pip executable."""
        self._update_capture(kwargs, False)
        try:
            # result=self.cmd.pip(*args, text=bool(kwargs["capture_output"]), **kwargs)
            result = self.cmd.pip(*args, text=True, **kwargs)
        except run.CalledProcessError as exc:
            self._handle_exception(exc)
        return result

    def help(self, command: str | None = None, **kwargs: Any) -> str | None:  # noqa: A003
        """Gets the help information for pip and pip commands."""
        self._omit_kwargs(kwargs, "help")
        self._update_capture(kwargs, True)
        if not command:
            output = self.pip("help", **kwargs)
        else:
            # output=self.pip(command, help=True, **kwargs)
            output = self.pip("help", command, **kwargs)
        return self._parse_output_help(output)

    def install(self, *packages: str,
                target: StrPath | bool = False,
                root: StrPath | bool = False,
                editable: StrPath | str | bool = False,
                prefix: StrPath | bool = False,
                report: StrPath | bool = False,
                # extra_args: List[str] | None = None,  # ???
                **kwargs: Any) -> None:
        """Install packages."""
        self._update_capture(kwargs, False)
        # if extra_args: args.extend(extra_args)  # ???
        self.pip("install", *packages,
                 target=target, root=root, editable=editable, prefix=prefix,
                 report=report, **kwargs)  # extra_args=extra_args, **kwargs)

    def upgrade(self, *packages: str,
                target: StrPath | bool = False,
                root: StrPath | bool = False,
                editable: StrPath | str | bool = False,
                prefix: StrPath | bool = False,
                report: StrPath | bool = False,
                # extra_args: List[str] | None = None,  # ???
                **kwargs: Any) -> None:
        """Upgrade packages."""
        self._omit_kwargs(kwargs, "upgrade")
        self._update_capture(kwargs, False)
        # if extra_args: args.extend(extra_args)  # ???
        self.pip("install", *packages, upgrade=True,
                 target=target, root=root, editable=editable, prefix=prefix,
                 report=report, **kwargs)  # extra_args=extra_args, **kwargs)

    def download(self, *packages: str,
                 dest: StrPath | bool = False,
                 src: StrPath | bool = False, **kwargs: Any) -> None:
        """Download packages."""
        self._update_capture(kwargs, False)
        self.pip("download", *packages, dest=dest, src=src, **kwargs)

    def lock(self, *packages: str,
             output: StrPath | bool = False,
             editable: StrPath | str | bool = False,
             src: StrPath | bool = False, **kwargs: Any) -> None:
        """Generate a lock file."""
        if not self.command_exists("lock"):  # pragma: no cover
            raise self.NotImplementedError("command 'lock' is not implemented for "
                                           f"this version of pip: {self.version_info}")
        self._update_capture(kwargs, False)
        self.pip("lock", *packages,
                 output=output, editable=editable, src=src, **kwargs)

    def wheel(self, *packages: str,
              wheel_dir: StrPath | bool = False,
              editable: StrPath | str | bool = False,
              src: StrPath | bool = False, **kwargs: Any) -> None:
        """Build wheels from your requirements."""
        self._update_capture(kwargs, False)
        self.pip("wheel", *packages,
                 wheel_dir=wheel_dir, editable=editable, src=src, **kwargs)

    def uninstall(self, *packages: str, **kwargs: Any) -> None:
        """Uninstall packages."""
        self._update_kwarg(kwargs, "yes", True)
        self._update_capture(kwargs, False)
        self.pip("uninstall", *packages, **kwargs)

    def list(self, **kwargs: Any) -> dict[str, Package] | None:  # noqa: A003
        """List installed packages, including editables."""
        self._update_capture(kwargs, True)
        if kwargs["capture_output"]:
            kwargs["format"] = "json"
        output = self.pip("list", **kwargs)
        return self._parse_list_json(output)

    def freeze(self, **kwargs: Any) -> List[str] | None:
        """Output installed packages in requirements format."""
        self._update_capture(kwargs, True)
        output = self.pip("freeze", **kwargs)
        return self._parse_freeze(output)

    def inspect(self, **kwargs: Any) -> dict[str, Any] | None:
        """Inspect the python environment."""
        self._update_capture(kwargs, True)
        output = self.pip("inspect", **kwargs)
        return self._parse_inspect(output)

    def show(self, *packages: str, **kwargs: Any) -> dict[str, PackageInfo] | None:
        """Show information about one or more installed packages."""
        self._omit_kwargs(kwargs, "verbose")
        self._update_capture(kwargs, True)
        output = self.pip("show", *packages, verbose=True, **kwargs)
        return self._parse_show(output)

    def check(self, **kwargs: Any) -> tuple[int, str | None]:
        """Verify installed packages have compatible dependencies."""
        self._update_capture(kwargs, True)
        output = self.pip("check", check=False, **kwargs)
        return (output.returncode, self._parse_output_str(output))

    def config(self, command: str, *args: Any, **kwargs: Any) \
               -> dict[str, Any] | str | None:
        """Manage local and global configuration."""
        match command:
            case "list":
                return self.config_list(*args, **kwargs)
            case "edit":
                self.config_edit(*args, **kwargs)
                return None  # pragma: no cover
            case "get":
                return self.config_get(*args, **kwargs)
            case "set":
                self.config_set(*args, **kwargs)
                return None
            case "unset":
                self.config_unset(*args, **kwargs)
                return None
            case "debug":
                return self.config_debug(*args, **kwargs)
            case _:
                self._update_capture(kwargs, True)
                output = self.pip("config", command, *args, **kwargs)
                return self._parse_output_str(output)  # pragma: no cover
                # raise self.RuntimeError(f"Unsupported config command: {command}")

    def config_list(self, **kwargs: Any) -> dict[str, Any] | None:
        """List the active configuration (or from the file specified)."""
        self._omit_kwargs(kwargs, "quiet")
        self._update_capture(kwargs, True)
        output = self.pip("config", "list", **kwargs)
        return self._parse_config_list(output)

    def config_edit(self, **kwargs: Any) -> None:
        """Edit the configuration file in an editor."""
        self._update_capture(kwargs, True)
        # self.pip("config", "edit", **kwargs)
        raise self.NotImplementedError("pip_runner.edit() is not implemented.")

    def config_get(self, option: str, **kwargs: Any) -> str | None:
        """Get the value associated with command.option."""
        self._omit_kwargs(kwargs, "quiet")
        self._update_capture(kwargs, True)
        output = self.pip("config", "get", option, **kwargs)
        return self._parse_config_get(output)

    def config_set(self, option: str, value: str, **kwargs: Any) -> None:
        """Set the command.option=value."""
        self._update_capture(kwargs, True)
        self.pip("config", "set", option, value, **kwargs)

    def config_unset(self, option: str, **kwargs: Any) -> None:
        """Unset the value associated with command.option."""
        self._update_capture(kwargs, True)
        self.pip("config", "unset", option, **kwargs)

    def config_debug(self, **kwargs: Any) -> dict[str, Any] | None:
        """List the configuration files and values defined under them."""
        self._omit_kwargs(kwargs, "quiet")
        self._update_capture(kwargs, True)
        output = self.pip("config", "debug", **kwargs)
        return self._parse_config_debug(output)

    def cache(self, command: str, *args: Any, **kwargs: Any) \
              -> Path | CacheInfoResult | List[Path] | CacheRemoveResult | str | None:
        """Inspect and manage pip's wheel cache."""
        self._update_kwarg(kwargs, "verbose", True)
        match command:
            case "dir":
                return self.cache_dir(*args, **kwargs)
            case "info":
                return self.cache_info(*args, **kwargs)
            case "list":
                return self.cache_list(*args, **kwargs)
            case "remove":
                return self.cache_remove(*args, **kwargs)
            case "purge":
                return self.cache_purge(*args, **kwargs)
            case _:
                self._update_capture(kwargs, True)
                output = self.pip("cache", command, *args, **kwargs)
                return self._parse_output_str(output)  # pragma: no cover
                # raise self.RuntimeError(f"Unsupported cache command: {command}")

    def cache_dir(self, **kwargs: Any) -> Path | None:
        """Show the cache directory."""
        self._update_kwarg(kwargs, "verbose", True)
        self._update_capture(kwargs, True)
        output = self.pip("cache", "dir", **kwargs)
        return self._parse_cache_dir(output)

    def cache_info(self, **kwargs: Any) -> CacheInfoResult | None:
        """Show information about the cache."""
        self._update_kwarg(kwargs, "verbose", True)
        self._update_capture(kwargs, True)
        output = self.pip("cache", "info", **kwargs)
        return self._parse_cache_info(output)

    def cache_list(self, pattern: str | None = None, **kwargs: Any) -> List[Path] | None:
        """List filenames of packages stored in the cache.

        <pattern> - can be a glob expression or a package name.
        """
        # pip cache list [<pattern>] [--format=[human, abspath]]
        self._update_kwarg(kwargs, "format", "abspath")
        self._update_kwarg(kwargs, "verbose", True)
        self._update_capture(kwargs, True)
        if pattern is None:  # pragma: no cover
            output = self.pip("cache", "list", **kwargs)
        else:
            output = self.pip("cache", "list", pattern, **kwargs)
        return self._parse_cache_list(output)

    def cache_remove(self, pattern: str, **kwargs: Any) -> CacheRemoveResult | None:
        """Remove one or more package from the cache.

        <pattern> - can be a glob expression or a package name.
        """
        self._update_kwarg(kwargs, "verbose", True)
        self._update_capture(kwargs, True)
        output = self.pip("cache", "remove", pattern, **kwargs)
        return self._parse_cache_remove(output)

    def cache_purge(self, **kwargs: Any) -> CacheRemoveResult | None:
        """Remove all items from the cache."""
        self._update_kwarg(kwargs, "verbose", True)
        self._update_capture(kwargs, True)
        output = self.pip("cache", "purge", **kwargs)
        return self._parse_cache_remove(output)

    def search(self, *query: str, **kwargs: Any) -> dict[str, ProjectPage] | List[str] | None:
        """Search PyPI for packages."""
        if "index" in kwargs:
            raise self.NotImplementedError("pip_runner.search() does not support "
                                           "the 'index' option.")
        no_query = not query
        project_pages = []
        try:
            with PyPISimple() as client:
                if no_query:  # pragma: no cover
                    index_page: IndexPage = client.get_index_page(**kwargs)
                else:
                    for qq in query:
                        project_pages.append(client.get_project_page(qq, **kwargs))
        except Exception as exc:
            self._handle_exception(exc)
        if no_query:  # pragma: no cover
            return index_page.projects
        else:
            # self._update_capture(kwargs, True)
            # output = self._pip_search(query, **kwargs)
            return self._parse_search(project_pages)  # pragma: no cover

    # def _pip_search(self, *query: str, **kwargs: Any) -> run.CompletedTextProcess:
    #     raise self.NotImplementedError("pip_runner.search() is not implemented for now."
    #                                    "Please be patient.")

    def index(self, action: str, package: str, **kwargs: Any) -> PackageVersions | str | None:
        """Inspect information available from package indexes."""
        self._update_capture(kwargs, True)
        match action:
            case "versions":  # pragma: no branch
                if kwargs["capture_output"]:
                    kwargs["json"] = (self.version_info >= version_info("25.1"))
        output = self.pip("index", action, package, **kwargs)
        match action:
            case "versions":
                if kwargs.get("json", False):
                    return self._parse_index_versions_json(output)
                else:
                    return self._parse_index_versions(output)
            case _:  # pragma: no cover
                return self._parse_output_str(output)

    def hash(self, *files: StrPath, **kwargs: Any) -> dict[str, FileHash] | None:  # noqa: A003
        """Compute hashes of package archives."""
        self._update_capture(kwargs, True)
        output = self.pip("hash", *files, **kwargs)
        return self._parse_hashes(output)

    def completion(self, **kwargs: Any) -> str | None:
        """A helper command used for command completion."""
        self._update_capture(kwargs, True)
        if not any((opt in kwargs) for opt in ("bash", "fish", "powershell", "zsh",)):
            raise self.ValueError("You must pass --bash or --fish or --powershell or --zsh")
        output = self.pip("completion", **kwargs)
        return self._parse_output_str(output)

    def debug(self, **kwargs: Any) -> str | None:
        """Show information useful for debugging."""
        self._update_capture(kwargs, True)
        output = self.pip("debug", **kwargs)
        return self._parse_debug(output)

    def command_exists(self, command: str) -> bool:
        try:
            self.help(command)
            return True
        except self.RuntimeError:
            return False

    # Exceptions

    class Error(Exception):
        """pip error."""

    class TypeError(builtins.TypeError, Error):  # noqa: A001
        """Type error."""

    class ValueError(builtins.ValueError, Error):  # noqa: A001
        """Value error."""

    class RuntimeError(builtins.RuntimeError, Error):  # noqa: A001
        """Runtime error."""

    class NotImplementedError(builtins.NotImplementedError, Error):  # noqa: A001
        """Not implemented error."""

    # ---- Helpers and internals ---- #

    def _parse_output_str(self, output: run.CompletedTextProcess) -> str | None:
        out = output.stdout
        if out is None: return None
        return out

    def _parse_output_help(self, output: run.CompletedTextProcess) -> str | None:
        out = output.stdout
        if out is None: return None
        return out.lstrip()

    def _parse_output_lines(self, output: run.CompletedTextProcess) -> List[str] | None:
        out = output.stdout
        if out is None: return None
        return out.splitlines()

    def _parse_list_json(self, output: run.CompletedTextProcess) -> dict[str, Package] | None:
        out = output.stdout
        if out is None: return None
        pkgs: dict[str, Package] = {}
        for pkg_dict in json.loads(out):
            pkg_name, version = pkg_dict["name"], pkg_dict["version"]
            pkgs[pkg_name] = pkg = Package(name=pkg_name, version=version)
            optional_attributes = [
                "location",
                "editable_project_location",
                "latest_version",
                "latest_filetype",
                "installer",
            ]
            for attr_name in optional_attributes:
                if attr_name in pkg_dict:
                    value = pkg_dict[attr_name]
                    match attr_name:
                        case "location" | "editable_project_location":
                            value = Path(value.strip()) if value.strip() else None
                    setattr(pkg, attr_name, value)
        return pkgs

    def _parse_freeze(self, output: run.CompletedTextProcess) -> List[str] | None:
        out = output.stdout
        if out is None: return None
        result: List[str] = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # pragma: no cover
            result.append(line)
        return result

    def _parse_inspect(self, output: run.CompletedTextProcess) -> dict[str, Any] | None:
        out = output.stdout
        if out is None: return None
        out = self._sanitize_string(out)
        result: dict[str, Any] = json.loads(out)
        return result

    def _parse_show(self, output: run.CompletedTextProcess) -> dict[str, PackageInfo] | None:
        out = output.stdout
        if out is None: return None
        supported_keys = (
            "Name",
            "Version",
            "Summary",
            "Home-page",
            "Author",
            "Author-email",
            "License-Expression",
            "License",
            "Location",
            "Editable project location",
            "Editable-project-location",  # because spaces transform
            "Requires",
            "Required-by",
            "Metadata-Version",
            "Installer",
            "Classifiers",
            "Entry-points",
            "Project-URLs",
            "Files",
        )
        supported_keys_regex = "|".join((key[0]+"(?i:"+key[1:]+")").replace("-", r"[\-_]")
                                        for key in supported_keys)
        supported_keys_pattern = re.compile(supported_keys_regex)
        key_regex = supported_keys_regex + "|" + r"[A-Z][A-Za-z0-9\-_]*"
        policy = EmailPolicy(max_line_length=None)
        # policy_strict = policy.clone(raise_on_defect=True)

        pkgs: dict[str, PackageInfo] = {}
        for info_str in re.split(r"\n---\n(?=Name:)", out):
            # print(f"\n@@@@@ info_str:\n{info_str}")
            info_str = self._preparse_email(info_str, key_regex=key_regex)
            # print(f"\n@@@@@ info_str preparsed:\n{info_str}")
            pkg_info = EmailParser(policy=policy).parsestr(info_str, headersonly=True)
            # print(f"\n@@@@@ pkg_info:\n{pkg_info.items()}")
            params: dict[str, Any] = dict(
                editable_project_location=None,
                license="",
                license_expression="",
                files=None,
            )
            for key, val in pkg_info.items():
                if not supported_keys_pattern.match(key):
                    # omit unsupported keys
                    continue  # pragma: no cover
                value: Any = str(val)
                attr_name = key.lower().replace("-", "_").replace(" ", "_")
                match attr_name:
                    case "home_page":
                        attr_name = attr_name.replace("_", "")
                    case "location" | "editable_project_location":
                        value = Path(value.strip()) if value.strip() else None
                    case "requires" | "required_by":
                        value = [line.strip() for line in value.split(",") if line.strip()]
                    case "classifiers" | "entry_points" | "project_urls":
                        value = [line.lstrip() for line in value.splitlines() if line.strip()]
                    case "files":
                        if value.strip().lower() == "cannot locate record or installed-files.txt":
                            continue  # pragma: no cover
                        value = [line.lstrip() for line in value.splitlines() if line.strip()]
                params[attr_name] = value
            pkg = PackageInfo(**params)
            pkgs[pkg.name] = pkg

        return pkgs

    def _parse_config_list(self, output: run.CompletedTextProcess) -> dict[str, Any] | None:
        out = output.stdout
        if out is None: return None
        return self._parse_config_string(out)

    def _parse_config_get(self, output: run.CompletedTextProcess) -> str | None:
        out = self._parse_output_str(output)
        if out is None: return None
        return out.rstrip("\n")

    def _parse_config_debug(self, output: run.CompletedTextProcess) -> dict[str, Any] | None:
        out = output.stdout
        if out is None: return None
        key_regex = r"[\w\-]+"
        section_pattern = re.compile(rf"(^|\n)(?P<head>({key_regex})):"
                                     rf"(?P<body>[\s\S]*?)((?=\n({key_regex}):)|$)")
        key_regex = r"([\h\S]+),\h*exists\h*:\h*(?i:(True|False))"
        file_pattern = re.compile(rf"(^|\n)({key_regex})"
                                  rf"(?P<body>[\s\S]*?)((?=\n({key_regex}))|$)")

        debug_info: dict[str, Any] = {}
        for match in section_pattern.finditer(out):
            head = match.group("head").strip()
            body = dedent(match.group("body").removeprefix("\n"))
            if head.lower() == "env_var":
                head = head.lower()
                options = self._parse_config_string(body)
            elif not body.strip():
                options = {}
            else:
                files = []
                for match in file_pattern.finditer(body):
                    path = Path(match.group(3).strip())
                    exists = (match.group(4).capitalize()  == "True")
                    body = dedent(match.group("body").removeprefix("\n"))
                    config = self._parse_config_string(body,
                                                       option_regex=r"^(?P<key>[^:]+):"
                                                                    r"\s*(?P<value>.*)\s*$")
                    files.append(ConfigIniFile(path=path, exists=exists, config=config))
                options = {"files": files} if files else {}
            debug_info[head] = options

        return debug_info

    @classmethod
    def _parse_config_string(cls, config_string: str, *,
                             option_regex: str = r"^(?P<key>[^=]+)="
                                                 r"\s*(['\"])(?P<value>.*)\2\s*$") \
                             -> dict[str, Any]:
        """Parses a string of the format: key.subkey='value'"""
        option_pattern = re.compile(option_regex)

        config: dict[str, Any] = {}
        for line in config_string.strip().splitlines():
            line = line.lstrip()
            if not line or line.startswith("#"):
                continue  # pragma: no cover

            # Regex: key='value' or key="value"
            match = option_pattern.match(line)
            if not match:
                continue  # pragma: no cover

            key_path = [key.strip() for key in match.group("key").split(".")]
            value = match.group("value")

            # Attempts to cast to an float and integer
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass

            # Creates a nested structure
            current = config
            for key in key_path[:-1]:
                current = current.setdefault(key, {})
            current[key_path[-1]] = value

        return config

    def _parse_cache_dir(self, output: run.CompletedTextProcess) -> Path | None:
        path = self._parse_output_str(output)
        if path is None: return None
        return Path(path.strip())

    def _parse_cache_info(self, output: run.CompletedTextProcess) -> CacheInfoResult | None:
        out = output.stdout
        if out is None: return None
        outlines = [line.strip() for line in out.strip().splitlines()]
        beg_line = "Package index page cache location (pip "
        cache_loc = next((line.split(":", maxsplit=1)[1].strip()
                          for line in outlines if line.startswith(beg_line)), None)
        beg_line = "Package index page cache location (older pip"
        cache_loc_old = next((line.split(":", maxsplit=1)[1].strip()
                              for line in outlines if line.startswith(beg_line)), None)
        beg_line = "Number of HTTP files:"
        http_files = next((line.removeprefix(beg_line).strip()
                           for line in outlines if line.startswith(beg_line)), None)
        beg_line = "Locally built wheels location:"
        wheels_loc = next((line.removeprefix(beg_line).strip()
                           for line in outlines if line.startswith(beg_line)), None)
        beg_line = "Number of locally built wheels:"
        built_wheels = next((line.removeprefix(beg_line).strip()
                             for line in outlines if line.startswith(beg_line)), None)
        return CacheInfoResult(cache_location=Path(cache_loc) if cache_loc else None,
                               cache_location_old=Path(cache_loc_old) if cache_loc_old else None,
                               http_files_number=int(http_files) if http_files else -1,
                               built_wheels_location=Path(wheels_loc) if wheels_loc else None,
                               built_wheels_number=int(built_wheels) if built_wheels else -1)

    def _parse_cache_list(self, output: run.CompletedTextProcess) -> List[Path] | None:
        lines = self._parse_output_lines(output)
        if lines is None: return None
        return [Path(line.strip()) for line in lines if line is not None and line.strip()]

    def _parse_cache_remove(self, output: run.CompletedTextProcess) -> CacheRemoveResult | None:
        out = output.stdout
        if out is None: return None
        outlines = [line.strip() for line in out.strip().splitlines()]
        # Files removed: 4538 (965.4 MB)
        # Directories removed: 87
        beg_line = "Files removed:"
        files = next((line.removeprefix(beg_line).strip()
                      for line in outlines if line.startswith(beg_line)), None)
        beg_line = "Directories removed:"
        dirs = next((line.removeprefix(beg_line).strip()
                     for line in outlines if line.startswith(beg_line)), None)
        return CacheRemoveResult(files=int(files.split()[0]) if files else -1,
                                 directories=int(dirs.split()[0])  if dirs  else -1)

    # NOK
    def _parse_search(self, project_pages: List[ProjectPage]) -> dict[str, ProjectPage] | None:
        result: dict[str, ProjectPage] = {}
        for page in project_pages:
            if not page: continue  # pragma: no cover
            result[page.project] = page
        return dict(result)

    def _parse_index_versions_json(self, output: run.CompletedTextProcess) \
                                   -> PackageVersions | None:
        out = output.stdout
        if out is None: return None
        pkg_index = json.loads(out)
        return PackageVersions(name=pkg_index["name"],
                               versions=pkg_index["versions"],
                               latest=pkg_index["latest"] or None,
                               installed=pkg_index.get("installed_version"))

    def _parse_index_versions(self, output: run.CompletedTextProcess) \
                              -> PackageVersions | None:
        out = output.stdout
        if out is None: return None
        option_pattern = re.compile(r"^(?P<key>[^:]+):\s*(?P<value>.*)\s*$", re.MULTILINE)
        head, body = out.strip().split("\n", maxsplit=1)
        pkg_versions = PackageVersions(name=head.split("(", maxsplit=1)[0].strip(),
                                       versions=[], latest=None, installed=None)
        for match in option_pattern.finditer(body):
            key   = match.group("key").strip()
            value = match.group("value").strip()
            match key.lower():
                case "available versions":
                    pkg_versions.versions = [ver.strip() for ver in value.split(", ")]
                case "latest":
                    pkg_versions.latest = value.split("(", maxsplit=1)[0].strip() or None
                case "installed":  # pragma: no branch
                    pkg_versions.installed = value.split("(", maxsplit=1)[0].strip() or None
                    if "(latest" in value:  # pragma: no cover  # due to pip bug
                        pkg_versions.latest = pkg_versions.installed
        return pkg_versions

    def _parse_hashes(self, output: run.CompletedTextProcess) -> dict[str, FileHash] | None:
        out = output.stdout
        if out is None: return None
        # result is of the form:
        # <filename>:\n--hash=<algorithm>:<hash>\n
        hashes: dict[str, FileHash] = {}
        outlines = out.strip().splitlines()
        for line1, line2 in list(zip(*[iter(outlines)]*2)):
            line1, line2 = line1.strip(), line2.strip()
            file = line1.removesuffix(":")
            algo, _, hval = line2.removeprefix("--hash=").partition(":")
            hashes[file] = FileHash(file=Path(file), hash=hval, algorithm=algo)
        return hashes

    def _parse_debug(self, output: run.CompletedTextProcess) -> str | None:
        return self._parse_output_str(output)

    def _handle_exception(self, exc: BaseException, **kwargs: Any) -> None:
        if isinstance(exc, run.CalledProcessError):
            msg = exc.stderr.strip() if exc.stderr is not None else str(exc)
        else:  # pragma: no cover
            msg = str(exc)
        raise self.RuntimeError(msg) from None

    # Utils

    @classmethod  # pragma: no cover # not in use
    def _normalize_newlines(cls, text: str) -> str:
        """Standardizes line endings to <LF>"""
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        """Replace non-ASCII characters with '?'."""
        return text.encode("ascii", errors="replace").decode("ascii")

    @classmethod
    def _preparse_email(cls, text: str, *,
                        key_regex: str = r"[A-Z][A-Za-z0-9\-_]*") -> str:
        preparse_pattern = re.compile(rf"(?P<head>(^|\n)({key_regex}):)"
                                      rf"(?P<body>[\s\S]*?)((?=\n({key_regex}):)|$)")
        head_pattern = re.compile(r"(?<=\S)\s+(?=\S)")

        preparsed = ""
        for match in preparse_pattern.finditer(text):
            head = match.group("head")
            body = match.group("body")
            # print(f"HEAD: |{head}|")
            # print(f"BODY: |{body}|")
            head = head_pattern.sub("-", head)
            if "\n" in body:
                indent_count = cls._get_indent(body)
                if indent_count == 0:  # if body == dedent(body):
                    prefix = "  "
                    body = indent(body, prefix, lambda line: True)
                    if body.endswith("\n"): body += prefix
                else:
                    lines = body.splitlines(True)
                    if lines:  # pragma: no branch
                        prefix = " "
                        body = lines[0] + "".join((prefix + line) if len(line) == 1
                                                  else line for line in lines[1:])
                        if body.endswith("\n"): body += prefix
            preparsed += head + body

        return preparsed

    @classmethod
    def _get_indent(cls, text: str) -> int:
        non_empty_lines = [line.expandtabs(4)
                           for line in text.splitlines() if line.strip()]
        return min(len(line) - len(line.lstrip())
                   for line in non_empty_lines) if non_empty_lines else 0

    @classmethod
    def _omit_kwargs(cls, kwargs: dict[str, Any], *unnecessary: str) -> None:
        for omit in unnecessary:
            kwargs.pop(omit, None)

    @classmethod
    def _update_kwarg(cls, kwargs: dict[str, Any], key: str, default: Any) -> None:
        if key not in kwargs:
            kwargs[key] = default

    @classmethod
    def _update_capture(cls, kwargs: dict[str, Any], default: bool) -> None:
        cls._update_kwarg(kwargs, "capture_output", default)
