"""PYTHONPATH-scoped NVTX function tracing hook.

Enable with NVTX_PROFILE_PYTHON=1 and put this directory on PYTHONPATH.
This avoids modifying an environment's site-packages/sitecustomize.py.
"""

import os


if os.environ.get("NVTX_PROFILE_PYTHON") == "1":
    import sys
    import threading

    try:
        import nvtx

        _include = tuple(filter(None, os.environ.get("NVTX_PROFILE_INCLUDE", "").split(",")))
        _exclude = tuple(filter(None, os.environ.get("NVTX_PROFILE_EXCLUDE", "importlib").split(",")))
        _module_cache = {}
        _pushed_frames = set()

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
        print(
            f"[NVTX] Python profiling enabled (include={_include or 'all'}, exclude={_exclude})",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"[NVTX] Failed: {exc}", file=sys.stderr)
