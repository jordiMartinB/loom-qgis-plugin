import ctypes
import os
import importlib.machinery
import importlib.util
import inspect
import struct
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

__all__ = ["run_topo", "run_octi", "run_loom"]

_backend_cache: Dict[str, Any] = {}  # key: backend_name -> module


def _backend_name() -> str:
    """Read LOOM_BACKEND_MODULE at call time (allows tests to change env)."""
    return os.environ.get("LOOM_BACKEND_MODULE", "loom")


def _find_backend_so() -> Path:
    """Locate the loom extension module matching the running Python version.

    Prefers an exact version match (e.g. loom.cpython-314-x86_64-linux-gnu.so)
    and falls back to any loom*.so / loom*.pyd found in lib/.
    """
    lib_dir = Path(__file__).parent / "lib"
    ext = ".pyd" if sys.platform == "win32" else ".so"

    # Build version-specific prefix:
    #   Linux/macOS: cpython-314   Windows: cp314
    vi = sys.version_info
    if sys.platform == "win32":
        version_tag = f"cp{vi.major}{vi.minor}"
    else:
        version_tag = f"cpython-{vi.major}{vi.minor}"

    # 1. Exact version match
    exact = list(lib_dir.glob(f"loom.{version_tag}*{ext}"))
    if exact:
        return exact[0]

    # 2. Any loom extension (different Python version bundled)
    fallback = list(lib_dir.glob(f"loom*{ext}"))
    if fallback:
        return fallback[0]

    raise FileNotFoundError(
        f"loom extension module (*{ext}) not found in {lib_dir}. "
        f"Looked for Python {vi.major}.{vi.minor} ({version_tag})."
    )


def _get_pe_imports(path: str) -> List[str]:
    """Parse the PE import table and return imported DLL names (best-effort)."""
    try:
        with open(path, "rb") as f:
            data = f.read()

        if data[:2] != b"MZ":
            return []
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_offset : pe_offset + 4] != b"PE\0\0":
            return []

        num_sections   = struct.unpack_from("<H", data, pe_offset + 6)[0]
        opt_hdr_size   = struct.unpack_from("<H", data, pe_offset + 20)[0]
        opt_offset     = pe_offset + 24
        magic          = struct.unpack_from("<H", data, opt_offset)[0]

        # Correct offset to DataDirectory[1] (Import Table RVA):
        #   PE32  (0x10B): 96 bytes of header fields => DataDirectory at opt+96
        #   PE32+ (0x20B): 112 bytes of header fields => DataDirectory at opt+112
        # DataDirectory[1] is 8 bytes after DataDirectory[0], so +8.
        dd1_offset = opt_offset + (120 if magic == 0x20B else 104)
        import_rva  = struct.unpack_from("<I", data, dd1_offset)[0]
        if import_rva == 0:
            return []

        # Build section map
        sec_base = opt_offset + opt_hdr_size
        sections = []
        for i in range(num_sections):
            base = sec_base + i * 40
            vsize  = struct.unpack_from("<I", data, base + 8)[0]
            vaddr  = struct.unpack_from("<I", data, base + 12)[0]
            rawsz  = struct.unpack_from("<I", data, base + 16)[0]
            rawoff = struct.unpack_from("<I", data, base + 20)[0]
            sections.append((vaddr, vsize, rawoff, rawsz))

        def rva_to_off(rva: int) -> int:
            for vaddr, vsize, raw_off, raw_size in sections:
                span = max(vsize, raw_size)
                if vaddr <= rva < vaddr + span:
                    return raw_off + (rva - vaddr)
            return -1

        off = rva_to_off(import_rva)
        if off < 0:
            return []

        dlls: List[str] = []
        i = 0
        while True:
            entry    = off + i * 20
            name_rva = struct.unpack_from("<I", data, entry + 12)[0]
            if name_rva == 0:
                break
            name_off = rva_to_off(name_rva)
            if name_off < 0:
                break
            end = data.index(b"\0", name_off)
            dlls.append(data[name_off:end].decode("ascii", errors="replace"))
            i += 1
        return dlls
    except Exception:
        return []


def _find_missing_dlls(pyd_path: str, search_dirs: List[Path]) -> List[str]:
    """Return imported DLL names from pyd_path that cannot be loaded."""
    if sys.platform != "win32":
        return []
    missing: List[str] = []
    for dll_name in _get_pe_imports(pyd_path):
        # Skip well-known OS / Python DLLs that are always available
        lower = dll_name.lower()
        if lower.startswith(("python", "kernel32", "ntdll", "msvcrt",
                              "api-ms-", "ucrtbase", "vcruntime")):
            continue
        # Try to load it; if it fails it's the culprit
        try:
            ctypes.WinDLL(dll_name)
        except OSError:
            # Also try from each search dir explicitly
            found = any(
                (d / dll_name).exists() or (d / dll_name.lower()).exists()
                for d in search_dirs
            )
            if not found:
                missing.append(dll_name)
    return missing


def _dll_search_dirs() -> List[Path]:
    """Return directories to register as DLL search paths on Windows.

    Python 3.8+ no longer consults PATH for DLL resolution, so we must
    explicitly add any directory that contains native dependencies of the
    loom extension (MSVC runtime, Qt/QGIS libraries, etc.).
    """
    seen: set = set()
    candidates: List[Path] = []

    def _add(p: Path) -> None:
        if not p.is_dir():
            return
        key = str(p.resolve()).lower()
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    # 1. The plugin's own lib/ directory
    _add(Path(__file__).parent / "lib")

    # 2. Python runtime directories.
    #    sys.prefix is always the Python installation root (e.g.
    #    C:\Program Files\QGIS 3.44.4\apps\Python312) regardless of what
    #    sys.executable points to (inside QGIS it points to qgis-bin.exe).
    py_prefix = Path(sys.prefix)
    _add(py_prefix)               # python312.dll lives here
    _add(py_prefix / "DLLs")     # cpython extension helpers
    _add(py_prefix / "Library" / "bin")  # conda-layout MSVC / MinGW DLLs

    # 3. Derive QGIS root from sys.prefix:
    #    …/QGIS 3.44.4/apps/Python312  →  parent = apps  →  parent = QGIS root
    apps_dir   = py_prefix.parent        # …/apps
    qgis_root  = apps_dir.parent         # …/QGIS 3.44.4
    _add(qgis_root / "bin")              # MSVC CRT, Qt, etc.
    _add(apps_dir / "qgis" / "bin")      # QGIS core DLLs
    _add(apps_dir / "qt5" / "bin")       # Qt5 DLLs

    # 4. Every directory currently on PATH that actually exists
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        _add(Path(entry))

    return candidates


def _load_backend_module(backend: str) -> Any:
    """Load the backend module by name or by .so/.pyd path."""
    if backend in _backend_cache:
        return _backend_cache[backend]

    # On Windows, register DLL search directories *before* any import attempt
    # so that the extension's native dependencies can be resolved.
    dll_cookies = []
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        for d in _dll_search_dirs():
            try:
                dll_cookies.append(os.add_dll_directory(str(d)))
            except (OSError, ValueError):
                pass

    try:
        # Try standard import first
        try:
            mod = importlib.import_module(backend)
            _backend_cache[backend] = mod
            return mod
        except ImportError:
            pass

        # Fall back to loading .pyd / .so by path
        try:
            so_path = _find_backend_so()
        except FileNotFoundError as e:
            raise ImportError(f"could not import backend module {backend!r}: {e}") from e

        # --- Diagnostic pre-load (Windows only) ----------------------------
        # module_from_spec / create_module will raise ImportError immediately
        # if a dependent DLL is missing, before exec_module is ever reached.
        # Use ctypes.WinDLL to trigger the same failure *with a richer message*
        # so we can tell the user exactly which DLL is absent.
        if sys.platform == "win32":
            try:
                ctypes.WinDLL(str(so_path))
            except OSError as _ct_err:
                search_dirs = _dll_search_dirs()
                missing = _find_missing_dlls(str(so_path), search_dirs)
                searched = "\n  ".join(str(d) for d in search_dirs)
                missing_msg = (
                    f"Missing DLL(s): {', '.join(missing)}\n" if missing
                    else "(PE scan could not identify a specific missing DLL — "
                         "use Dependencies.exe / dumpbin for a full analysis)\n"
                )
                raise ImportError(
                    f"DLL load failed for {so_path.name}.\n"
                    f"{missing_msg}"
                    f"ctypes error: {_ct_err}\n"
                    f"Directories searched for DLLs:\n  {searched}\n\n"
                    f"Fix: copy the missing DLL(s) into the plugin's lib/ folder:\n"
                    f"  {so_path.parent}"
                ) from _ct_err
        # -------------------------------------------------------------------

        spec = importlib.util.spec_from_file_location(
            backend,
            str(so_path),
            loader=importlib.machinery.ExtensionFileLoader(backend, str(so_path)),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"could not create spec from {so_path}")

        mod = importlib.util.module_from_spec(spec)
        sys.modules[backend] = mod
        try:
            spec.loader.exec_module(mod)
        except ImportError as e:
            sys.modules.pop(backend, None)
            raise
        _backend_cache[backend] = mod
        return mod
    finally:
        # Release the DLL directory registrations
        for cookie in dll_cookies:
            try:
                cookie.close()
            except Exception:
                pass


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