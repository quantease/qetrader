# -*- coding: utf-8 -*-
"""
Public PyPI plugin compatibility helpers.

qetrader 1.1.0 removed the legacy private plugin downloader from the public
distribution. PyPI releases must contain transparent, reviewable source code and
must not download customer-specific closed plugins at runtime.
"""


class PluginInstallDisabled(RuntimeError):
    """Raised when legacy private plugin installation is requested."""


def installPlugin(plugin_name, version="latest"):
    """Reject runtime installation of private plugins in the public package.

    The function is kept for import compatibility with older user code, but it
    intentionally performs no network access, file writes, dynamic import, or
    extraction.
    """

    raise PluginInstallDisabled(
        "Runtime plugin installation is disabled in the public PyPI build of "
        "qetrader. Install transparent, reviewable extensions as separate "
        "packages or use a private distribution channel outside PyPI."
    )


def downloadFile(plugin, token, filename, version):
    """Reject legacy direct plugin downloads in the public package."""

    raise PluginInstallDisabled(
        "Direct plugin downloads are disabled in the public PyPI build of "
        "qetrader."
    )
