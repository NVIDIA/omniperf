# diagnose-perf thorough test

Overall status: `pass`

| Check | Status | Detail |
|---|---|---|
| GPU snapshot command works | `pass` | NVIDIA L40, 570.158.01, 49140 MiB, 1 MiB, 25, P8, 0x0000000000000001, 0 %, 35.38 W, 300.00 W |
| CPU governor snapshot works | `pass` | schedutil |
| idle GPU classified carefully | `pass` | no workload currently running; only host facts are valid |
| red-flag logic documented | `pass` |  |
| governor changes require approval | `pass` | mutating fix must be gated |

## Evidence

```json
{
  "host": {
    "nvidia_smi": {
      "cmd": "nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,pstate,clocks_throttle_reasons.active,utilization.gpu,power.draw,power.limit --format=csv,noheader",
      "returncode": 0,
      "stdout": "NVIDIA L40, 570.158.01, 49140 MiB, 1 MiB, 25, P8, 0x0000000000000001, 0 %, 35.38 W, 300.00 W",
      "stderr": "",
      "duration_s": 0.044
    },
    "cpu_governor": {
      "cmd": "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unavailable",
      "returncode": 0,
      "stdout": "schedutil",
      "stderr": "",
      "duration_s": 0.001
    }
  }
}
```
