# profiling-api thorough test

Overall status: `pass`

| Check | Status | Detail |
|---|---|---|
| C++ macro header example | `pass` |  |
| Python profiler API example | `pass` |  |
| manual begin/end safety | `pass` | manual ranges should be exception-safe |
| metrics/plots documented | `pass` |  |
| Kit/Isaac runtime artifact test | `pass` | carb profiler runtime smoke 332833500 |

## Evidence

```json
{
  "carb_runtime_smoke": {
    "cmd": "/home/horde/venvs/isaacsim45/python.sh /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase4-thorough/profiling-api-smoke/carb_profiler_runtime_smoke.py",
    "returncode": 0,
    "stdout": "carb profiler runtime smoke 332833500",
    "stderr": "",
    "duration_s": 0.07
  }
}
```
