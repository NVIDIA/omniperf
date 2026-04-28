# install-profilers thorough test

Overall status: `warning`

| Check | Status | Detail |
|---|---|---|
| tool on PATH: nsys | `pass` | /usr/local/bin/nsys |
| tool on PATH: sqlite3 | `pass` | /usr/bin/sqlite3 |
| tool on PATH: csvexport | `pass` | /usr/local/bin/csvexport |
| tool on PATH: tracy-capture | `pass` | /usr/local/bin/tracy-capture |
| tool on PATH: tracy-update | `pass` | /usr/local/bin/tracy-update |
| tool on PATH: update | `pass` | /usr/local/bin/update |
| tool on PATH: capture | `pass` | /usr/local/bin/capture |
| tool on PATH: capture-release | `pass` | /usr/local/bin/capture-release |
| CUDA apt repo check is non-mutating | `pass` | /etc/apt/sources.list.d/cuda-ubuntu2204-x86_64.list |
| /opt Nsight check is non-mutating | `pass` | /opt/nvidia/nsight-systems/2025.6.3/target-linux-x64/nsys |
| skill says install only missing tools | `pass` | looked for install-only-missing guidance |
| privileged install commands present but documented | `warning` | sudo install examples require approval gating |

## Evidence

```json
{
  "tool_versions": {
    "nsys": {
      "cmd": "nsys --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "NVIDIA Nsight Systems version 2025.6.3.541-256337736014v0",
      "stderr": "",
      "duration_s": 0.05
    },
    "sqlite3": {
      "cmd": "sqlite3 --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "3.37.2 2022-01-06 13:25:41 872ba256cbf61d9290b571c0e6d82a20c224ca3ad82971edc46b29818d5dalt1",
      "stderr": "",
      "duration_s": 0.002
    },
    "csvexport": {
      "cmd": "csvexport --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "Extract statistics from a trace to a CSV format\nUsage:\n  extract [OPTION...] <trace file>\n\n  -h, --help        Print usage",
      "stderr": "",
      "duration_s": 0.003
    },
    "tracy-capture": {
      "cmd": "tracy-capture --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "Usage: capture -o output.tracy [-a address] [-p port] [-f] [-s seconds] [-m memlimit]",
      "stderr": "",
      "duration_s": 0.004
    },
    "tracy-update": {
      "cmd": "tracy-update --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "Usage: update [options] input.tracy output.tracy\n\n  -4: enable LZ4 compression\n  -h: enable LZ4HC compression\n  -e: enable extreme LZ4HC compression (very slow)",
      "stderr": "",
      "duration_s": 0.002
    },
    "update": {
      "cmd": "update --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "Usage: update [options] input.tracy output.tracy\n\n  -4: enable LZ4 compression\n  -h: enable LZ4HC compression\n  -e: enable extreme LZ4HC compression (very slow)",
      "stderr": "",
      "duration_s": 0.003
    },
    "capture": {
      "cmd": "capture --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "Usage: capture -o output.tracy [-a address] [-p port] [-f] [-s seconds] [-m memlimit]",
      "stderr": "",
      "duration_s": 0.003
    },
    "capture-release": {
      "cmd": "capture-release --version 2>&1 | head -5",
      "returncode": 0,
      "stdout": "Usage: capture -o output.tracy [-a address] [-p port] [-f] [-s seconds] [-m memlimit]",
      "stderr": "",
      "duration_s": 0.003
    }
  }
}
```
