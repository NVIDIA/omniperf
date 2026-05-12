import os
import json
from datetime import datetime, timezone

import carb
import carb.settings
import omni.kit.app

OUT = os.path.abspath(os.path.expanduser("./carb_settings.json"))

EXCEPTION_LIST = {
    "/crashreporter/data/lastCommands",
    "/crashreporter/data/lastCommand",
}
EXCLUDE_TOKENS = (
    "/Path",
    "/app/tokens",
    "/privacy",
    "/crashreporter",
    "/persistent/app/viewport/outline/shadeColor/",
    "/persistent/app/viewport/outline/color/",
    "/app/exts/foldersCore/",
    "/app/exts/folders/",
    "/app/python/sysPaths/",
    "/app/python/scriptFolders/",
    "/0/0/GL",
    "2.amazonaws",
)


def _skip(path):
    if path in EXCEPTION_LIST:
        return True
    if len(path) >= 2 and path[1].isupper():
        return True
    return any(path.startswith(t) for t in EXCLUDE_TOKENS)


def _flatten(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_flatten(v, prefix + "/" + k))
    else:
        if not _skip(prefix):
            out[prefix] = node
    return out


settings = carb.settings.get_settings()
flat = _flatten(settings.get("/"))

for var in ("PXR_WORK_THREAD_LIMIT", "OPENBLAS_NUM_THREADS",
            "GOTO_NUM_THREADS", "OMP_NUM_THREADS"):
    flat[var] = os.environ.get(var, -1)

app = omni.kit.app.get_app()
mgr = app.get_extension_manager()
exts = {}
for mod in mgr.get_enabled_extension_module_names():
    ext_id = mgr.get_extension_id_by_module(mod)
    exts.setdefault(ext_id, []).append(mod)

payload = {
    "utc_datetime": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    "app_name": app.get_app_name(),
    "app_version": app.get_app_version(),
    "kit_version": app.get_kit_version(),
    "settings": dict(sorted(flat.items())),
    "extensions": exts,
}

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    json.dump(payload, f, indent=4, default=str)

print("[dump_carb_settings] wrote {} ({} keys)".format(OUT, len(flat)))
