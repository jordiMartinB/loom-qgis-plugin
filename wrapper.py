import os
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

__all__ = ["run_topo", "run_octi", "run_transitmap", "run_loom"]

_backend_cache: Dict[str, Any] = {}  # key: backend_name -> module


def _backend_name() -> str:
    """Read LOOM_BACKEND_MODULE at call time (allows tests to change env)."""
    return os.environ.get("LOOM_BACKEND_MODULE", "loom")


def _find_backend_so() -> Path:
    """Locate libloom-python-plugin.so in the lib/ directory."""
    lib_dir = Path(__file__).parent / "lib"
    candidates = list(lib_dir.glob("libloom-python-plugin.so"))
    if not candidates:
        raise FileNotFoundError(f"libloom-python-plugin.so not found in {lib_dir}")
    return candidates[0]


def _load_backend_module(backend: str) -> Any:
    """Load the backend module by name or by .so path."""
    if backend in _backend_cache:
        return _backend_cache[backend]
    
    # Try standard import first
    try:
        mod = importlib.import_module(backend)
        _backend_cache[backend] = mod
        return mod
    except ImportError:
        pass
    
    # Fall back to loading .so by path
    try:
        so_path = _find_backend_so()
    except FileNotFoundError as e:
        raise ImportError(f"could not import backend module {backend!r}: {e}") from e
    
    spec = importlib.util.spec_from_file_location(backend, str(so_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"could not create spec from {so_path}")
    
    mod = importlib.util.module_from_spec(spec)
    sys.modules[backend] = mod
    spec.loader.exec_module(mod)
    _backend_cache[backend] = mod
    return mod


def _resolve(name: str) -> Callable:
    """Resolve backend callable by name."""
    backend = _backend_name()
    mod = _load_backend_module(backend)
    
    if hasattr(mod, name):
        fn = getattr(mod, name)
        if callable(fn):
            return fn
    
    raise AttributeError(f"function {name!r} not found in backend module {backend!r}")


def _call(name: str, *args, **kwargs) -> Any:
    """Call backend function with args/kwargs."""
    fn = _resolve(name)
    return fn(*args, **kwargs)


def run_topo(graph_json: str, config_json: str) -> str:
    """
    Run the topo topologisation stage.
    
    Args:
        graph_json: Input graph as JSON string
        config_json: Configuration as JSON string
        
    Returns:
        str: Output graph as JSON string
    """
    return _call("run_topo", [graph_json, config_json])


def run_loom(graph_json: str, config_json: str) -> str:
    """
    Run the loom line-ordering stage.
    
    Args:
        graph_json: Input graph as JSON string
        config_json: Configuration as JSON string
        
    Returns:
        str: Output graph as JSON string
    """
    return _call("run_loom", [graph_json, config_json])


def run_octi(graph_json: str, config_json: str) -> str:
    """
    Run the octi octilinear layout stage.
    
    Args:
        graph_json: Input graph as JSON string
        config_json: Configuration as JSON string
        
    Returns:
        str: Output graph as JSON string
    """
    return _call("run_octi", [graph_json, config_json])


def run_transitmap(graph_json: str, config_json: str) -> str:
    """
    Run the transitmap rendering stage.
    
    Args:
        graph_json: Input graph as JSON string
        config_json: Configuration as JSON string
        
    Returns:
        str: Rendered output (e.g. SVG) as string
    """
    return _call("run_transitmap", [graph_json, config_json])