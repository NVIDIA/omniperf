# nvtx-python thorough test

Overall status: `pass`

| Check | Status | Detail |
|---|---|---|
| nvtx import in active Python | `pass` | nvtx import OK |
| sitecustomize instructions present | `pass` |  |
| include/exclude filters documented | `pass` |  |
| sitecustomize overwrite/backup guidance | `pass` |  |
| nsys artifact test for NVTX ranges | `pass` | requires nsys + nvtx |

## Evidence

```json
{
  "python_import_nvtx": {
    "cmd": "python3 - <<\"PY\"\ntry:\n import nvtx\n print(\"nvtx import OK\")\nexcept Exception as e:\n print(type(e).__name__ + \": \" + str(e))\n raise SystemExit(42)\nPY",
    "returncode": 0,
    "stdout": "nvtx import OK",
    "stderr": "",
    "duration_s": 0.024
  }
}
```
