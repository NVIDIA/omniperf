"""PYTHONPATH-scoped NVTX function tracing hook.

Enable with NVTX_PROFILE_PYTHON=1 and put this directory on PYTHONPATH.
This avoids modifying an environment's site-packages/sitecustomize.py.

If a host (e.g. Omniverse Kit / Carb) replaces ``sys.setprofile`` after import
time, call :func:`install` again to re-arm the NVTX hook on the current thread.
"""

import os
import sys
import threading


_module_cache = {}
_pushed_frames = set()
_include = ()
_exclude = ()


def _module_enabled(module_name):
    cached = _module_cache.get(module_name)
    if cached is not None:
        return cached
    if any(module_name.startswith(prefix) for prefix in _exclude):
        enabled = False
    else:
        enabled = not _include or any(module_name.startswith(prefix) for prefix in _include)
    _module_cache[module_name] = enabled
    return enabled


def install():
    """(Re)install the NVTX profile callback on the current thread.

    Returns the installed callback on success, or ``None`` if ``nvtx`` isn't
    importable. Re-reads ``NVTX_PROFILE_INCLUDE`` / ``NVTX_PROFILE_EXCLUDE`` on
    each call, so the scope can be tightened between calls.
    """
    global _include, _exclude

    try:
        import nvtx
    except Exception as exc:
        print(f"[NVTX] install failed: {exc}", file=sys.stderr)
        return None

    _include = tuple(part.strip() for part in os.environ.get("NVTX_PROFILE_INCLUDE", "").split(",") if part.strip())
    _exclude = tuple(part.strip() for part in os.environ.get("NVTX_PROFILE_EXCLUDE", "importlib").split(",") if part.strip())
    _module_cache.clear()

    def _profile_callback(frame, event, arg):
        frame_id = id(frame)
        if event == "call":
            module_name = frame.f_globals.get("__name__", "")
            if _module_enabled(module_name):
                nvtx.push_range(f"{module_name}.{frame.f_code.co_name}")
                _pushed_frames.add(frame_id)
        elif event == "return" and frame_id in _pushed_frames:
            nvtx.pop_range()
            _pushed_frames.remove(frame_id)
        return _profile_callback

    sys.setprofile(_profile_callback)
    threading.setprofile(_profile_callback)
    return _profile_callback


if os.environ.get("NVTX_PROFILE_PYTHON") == "1":
    if install() is not None:
        print(
            f"[NVTX] Python profiling enabled (include={_include or 'all'}, exclude={_exclude})",
            file=sys.stderr,
        )
