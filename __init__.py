import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).parent.resolve()

# ---------------------------------------------------------------------------
# 1. Development: inject .venv site-packages so `import loom` resolves to
#    the locally installed .so.
# ---------------------------------------------------------------------------
_VENV_SITE = _PLUGIN_DIR / ".venv" / "lib"
for _py_dir in _VENV_SITE.glob("python*/site-packages"):
    _py_dir_str = str(_py_dir)
    if _py_dir_str not in sys.path:
        sys.path.insert(0, _py_dir_str)

# ---------------------------------------------------------------------------
# 2. Installed from zip: the .so lives in lib/ next to this file.
#    Add it to sys.path so `import loom` finds it there as a fallback.
# ---------------------------------------------------------------------------
_LIB_DIR = str(_PLUGIN_DIR / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

# ---------------------------------------------------------------------------
# 3. Ensure the plugin directory itself is on sys.path so that the plugin's
#    own modules (wrapper, loom_algorithms, loom_provider, plugin) can be
#    imported with plain absolute imports by QGIS's Python environment.
# ---------------------------------------------------------------------------
_PLUGIN_DIR_STR = str(_PLUGIN_DIR)
if _PLUGIN_DIR_STR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR_STR)


def classFactory(iface):  # noqa: N802  (QGIS requires this exact name)
    """QGIS plugin entry point."""
    from .plugin import LoomQGISPlugin
    return LoomQGISPlugin(iface)
