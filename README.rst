pip_runner
==========

| |package_bold| is a small, extendable Python wrapper around the pip command-line
  interface.
| It provides a thin, high-level API that executes `python -m pip` and parses
  commonly used outputs (freeze / list).

Overview
========

Key features
------------
- Thin wrapper using subprocess to run pip commands via Python executable.
- High-level Pip class with convenient methods like: install, uninstall,
  download, list, freeze, check, show, index, wheel, hash, completion, lock,
  config, cache, inspect, debug, help.
- Easy to extend, test and integrate with virtual environments (pass custom
  python_executable).

`PyPI record`_.

`Documentation`_.

Usage
-----

Basic usage:

.. code:: python

  from pip_runner import Pip
  pip = Pip()
  pip.install("requests")
  print(pip.list().get("requests"))

Installation
============

Prerequisites:

+ Python 3.10 or higher

  * https://www.python.org/

+ pip

  * https://pypi.org/project/pip/

To install run:

  .. parsed-literal::

    python -m pip install --upgrade |package|

Development
===========

Prerequisites:

+ Development is strictly based on *nox*. To install it run::

    python -m pip install --upgrade nox

Visit `Development page`_.

Installation from sources:

clone the sources:

  .. parsed-literal::

    git clone |respository| |package|

and run:

  .. parsed-literal::

    python -m pip install ./|package|

or on development mode:

  .. parsed-literal::

    python -m pip install --editable ./|package|

License
=======

  | |copyright|
  | Licensed under the zlib/libpng License
  | https://opensource.org/license/zlib
  | Please refer to the accompanying LICENSE file.

Authors
=======

* Adam Karpierz <adam@karpierz.net>

Sponsoring
==========

| If you would like to sponsor the development of this project, your contribution
  is greatly appreciated.
| As I am now retired, any support helps me dedicate more time to maintaining and
  improving this work.

`Donate`_

.. |package| replace:: pip_runner
.. |package_bold| replace:: **pip_runner**
.. |copyright| replace:: Copyright (c) 2026-2026 Adam Karpierz
.. |respository| replace:: https://github.com/karpierz/pip_runner
.. _Development page: https://github.com/karpierz/pip_runner
.. _PyPI record: https://pypi.org/project/pip-runner/
.. _Documentation: https://karpierz.github.io/pip_runner/
.. _Donate: https://www.paypal.com/donate/?hosted_button_id=FX8L7CJUGLW7S
