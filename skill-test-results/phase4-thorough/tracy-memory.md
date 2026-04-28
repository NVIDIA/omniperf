# tracy-memory thorough test

Overall status: `blocked_missing_prereq`

| Check | Status | Detail |
|---|---|---|
| liballocwrapper discovery | `pass` |  |
| liballocwrapper exists locally | `blocked_missing_prereq` | not found |
| Tracy capture binary available | `pass` |  |
| Tracy update binary available | `pass` |  |
| LD_PRELOAD unset before capture | `pass` |  |
| strip test documented | `pass` |  |
| real memory capture artifact test | `blocked_missing_prereq` | requires Kit app + Tracy tools |

## Evidence

```json
{
  "allocwrapper": {
    "cmd": "find ~/.cache/packman -name liballocwrapper.so 2>/dev/null | head -20",
    "returncode": 0,
    "stdout": "",
    "stderr": "",
    "duration_s": 0.287
  }
}
```
