# Copyright (c) 2026 Adam Karpierz
# SPDX-License-Identifier: Zlib

from __future__ import annotations

"""Low-level pip API"""

import typing
from typing import TypeAlias, Any
from typing_extensions import Self
from collections.abc import Callable
from functools import partialmethod
import sys
import os
from keyword import iskeyword

from utlx import public
from utlx import run
from utlx import issequence

CompletedProcessCallable: TypeAlias = Callable[..., run.CompletedTextProcess]


@public
class PipCmd:
    """Low-level pip command runner (uses `python -m pip`)."""

    python: str | None

    def __new__(cls, python_executable: str | None = None) -> Self:
        """Constructor"""
        self = super().__new__(cls)
        self.python = python_executable or sys.executable
        return self

    ## Low-level pip API ##

    def py(self, *args: Any, **kwargs: Any) -> run.CompletedTextProcess:
        """Run raw python executable."""
        return self._cmd(self.python, *args, **kwargs)

    def pip(self, *args: Any, **kwargs: Any) -> run.CompletedTextProcess:
        """Run raw pip executable."""
        encoding = kwargs.pop("encoding", "utf-8")
        env  = kwargs.pop("env", os.environ).copy()
        env.update(dict(
            # PIP_YES = "true",
            PIP_DISABLE_PIP_VERSION_CHECK = "1",
            PIP_NO_PYTHON_VERSION_WARNING = "1",
            PIP_NO_COLOR = "yes",
            # COLUMNS = str(135),
            # Make sure that Python writes output in UTF-8
            PYTHONIOENCODING = "utf-8",
            PYTHONLEGACYWINDOWSSTDIO = "utf-8",
        ))
        return self._cmd(self.python, "-m", "pip", *args,
                         *self._pip_common_args,
                         encoding=encoding, env=env, **kwargs)

    # ---- Helpers and internals ---- #

    _pip_common_args: tuple[str, ...] = (
        "--disable-pip-version-check",
        "--no-python-version-warning",
        # "--no-color",
    )
    _common_args: tuple[str, ...] = ()

    @classmethod
    def _run_wrapper(cls, run_fun: CompletedProcessCallable, *args: Any,
                     __format: str = "--{}", **kwargs: Any) -> run.CompletedTextProcess:
        normal_args = [arg for arg in args if arg is not None]
        allowed_kwargs, reserved_kwargs = run.split_kwargs(kwargs, cls._run_reserved_kwargs)
        allowed_args: list[str] = []
        for key, vals in allowed_kwargs.items():
            if key.endswith("_") and iskeyword(key[:-1]): key = key[:-1]
            key = key.replace("_", "-")
            vals = list(vals) if issequence(vals) else [vals]
            allowed_args += (__format.format(key if val is True else f"{key}={val}")
                             for val in vals if val is not False)
        return run_fun(*normal_args, *allowed_args, *cls._common_args, **reserved_kwargs)

    _run_reserved_kwargs: set[str] = {
        "check", "text", "capture_output", "input", "stdin", "stdout", "stderr",
        "shell", "cwd", "timeout", "encoding", "errors", "env", "universal_newlines",
    }

    _cmd = typing.cast(CompletedProcessCallable, partialmethod(_run_wrapper, run))
