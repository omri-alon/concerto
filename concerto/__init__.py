"""Concerto: Orchestrate Claude Code agents driven by GUS work items."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("concerto")
except PackageNotFoundError:
    __version__ = "0.0.0"  # not installed as a package
