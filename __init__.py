import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Inject the project venv's site-packages so that `import loom` resolves to
# loom.cpython-3xx-x86_64-linux-gnu.so installed there.  The .so's RPATH
# (set by auditwheel) already points at the sibling loom_python_plugin.libs/
# directory, so no extra LD_PRELOAD or ctypes tricks are needed.
# ---------------------------------------------------------------------------
_PLUGIN_DIR = Path(__file__).parent.resolve()
_VENV_SITE = _PLUGIN_DIR / ".venv" / "lib"

# Pick up all pythonX.Y sub-directories (handles different interpreter versions)
for _py_dir in _VENV_SITE.glob("python*/site-packages"):
    _py_dir_str = str(_py_dir)
    if _py_dir_str not in sys.path:
        sys.path.insert(0, _py_dir_str)


def classFactory(iface):  # noqa: N802  (QGIS requires this exact name)
    """QGIS plugin entry point."""
    from loom_qgis_plugin import LoomQGISPlugin
    return LoomQGISPlugin(iface)
