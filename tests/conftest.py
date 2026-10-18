"""Pytest configuration.

The parser tests only need the pure helper modules of the integration
(``api.py``, ``const.py``, ``data.py``). Importing them normally would
execute the package ``__init__.py``, which imports Home Assistant modules
and pulls in the whole HA runtime. This conftest therefore registers a
stub package object (with the real directory as ``__path__``) so the
submodules can be imported without Home Assistant in the loop.
"""

from __future__ import annotations

from pathlib import Path
import sys
import types

_PKG = "custom_components.gkd_bayern"
_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "gkd_bayern"

if _PKG not in sys.modules:
    stub = types.ModuleType(_PKG)
    stub.__path__ = [str(_DIR)]
    stub.__package__ = _PKG
    sys.modules[_PKG] = stub
