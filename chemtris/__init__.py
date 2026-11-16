"""ChemTris: a falling-block chemistry puzzle game by Shouku Games."""
__version__ = "0.1.0"

# True when running in a web browser (pygbag / WebAssembly).
import sys as _sys
WEB = _sys.platform == "emscripten"
RELEASE_DATE = "2026-11-04"
