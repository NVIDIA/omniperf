# Phase 4 — Thorough Per-Skill Tests

| Skill | Status | Key blockers/warnings |
|---|---|---|
| `install-profilers` | `pass` | - |
| `install-isaacsim` | `pass` | - |
| `install-isaaclab` | `pass` | - |
| `benchmark-isaacsim` | `blocked_missing_prereq` | Isaac Sim benchmark scripts available locally: blocked_missing_prereq; heavy benchmark sweeps not run: blocked_needs_approval |
| `benchmark-isaaclab` | `pass_with_warnings` | long RL training not run: pass_with_warnings |
| `profiling` | `pass` | - |
| `nsys-analyze` | `pass` | - |
| `nvtx-python` | `pass` | - |
| `profiling-api` | `pass` | - |
| `tracy-memory` | `blocked_missing_prereq` | liballocwrapper exists locally: blocked_missing_prereq; real memory capture artifact test: blocked_missing_prereq |
| `diagnose-perf` | `pass` | - |
| `perf-tuning` | `blocked_needs_approval` | real before/after artifact test: blocked_needs_approval |

## Host Snapshot Used

```json
{
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
  },
  "perf_event_paranoid": {
    "cmd": "cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo unavailable",
    "returncode": 0,
    "stdout": "4",
    "stderr": "",
    "duration_s": 0.002
  },
  "python3_version": {
    "cmd": "python3 --version",
    "returncode": 0,
    "stdout": "Python 3.10.12",
    "stderr": "",
    "duration_s": 0.003
  },
  "python_import_isaacsim": {
    "cmd": "python3 - <<\"PY\"\ntry:\n import isaacsim\n print(\"isaacsim import OK\")\nexcept Exception as e:\n print(type(e).__name__ + \": \" + str(e))\n raise SystemExit(42)\nPY",
    "returncode": 42,
    "stdout": "ModuleNotFoundError: No module named 'isaacsim'",
    "stderr": "",
    "duration_s": 0.011
  },
  "isaacsim_python_sh_verify": {
    "cmd": "if [ -x /home/horde/venvs/isaacsim45/python.sh ]; then OMNI_KIT_ACCEPT_EULA=YES /home/horde/venvs/isaacsim45/python.sh - <<\"PY\"\nimport isaacsim\nfrom isaacsim.simulation_app import SimulationApp\nprint(\"Isaac Sim OK\")\nPY\nelse echo \"no known isaacsim python.sh\"; exit 42; fi",
    "returncode": 0,
    "stdout": "Isaac Sim OK",
    "stderr": "",
    "duration_s": 0.112
  },
  "isaaclab_verify": {
    "cmd": "if [ -x /home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh ]; then env TERM=xterm bash -lc 'cd /home/horde/.openclaw/workspace/IsaacLab && ./isaaclab.sh -p -c \"import isaaclab; print(\\\"Isaac Lab OK\\\")\"'; else echo \"no known isaaclab.sh\"; exit 42; fi",
    "returncode": 0,
    "stdout": "\u001b[3g\n\u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH   \n[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh\nIsaac Lab OK",
    "stderr": "",
    "duration_s": 0.039
  },
  "python_import_nvtx": {
    "cmd": "python3 - <<\"PY\"\ntry:\n import nvtx\n print(\"nvtx import OK\")\nexcept Exception as e:\n print(type(e).__name__ + \": \" + str(e))\n raise SystemExit(42)\nPY",
    "returncode": 0,
    "stdout": "nvtx import OK",
    "stderr": "",
    "duration_s": 0.022
  },
  "python_import_torch_cuda": {
    "cmd": "python3 - <<\"PY\"\ntry:\n import torch\n print(\"torch\", torch.__version__, \"cuda\", torch.cuda.is_available())\nexcept Exception as e:\n print(type(e).__name__ + \": \" + str(e))\n raise SystemExit(42)\nPY",
    "returncode": 42,
    "stdout": "ModuleNotFoundError: No module named 'torch'",
    "stderr": "",
    "duration_s": 0.011
  },
  "conda": {
    "cmd": "command -v conda && conda --version",
    "returncode": 0,
    "stdout": "/usr/local/bin/conda\nconda 26.1.1",
    "stderr": "",
    "duration_s": 0.522
  },
  "uv": {
    "cmd": "command -v uv && uv --version",
    "returncode": 0,
    "stdout": "/home/horde/.local/bin/uv\nuv 0.11.8 (x86_64-unknown-linux-gnu)",
    "stderr": "",
    "duration_s": 0.005
  },
  "docker": {
    "cmd": "command -v docker && docker --version",
    "returncode": 0,
    "stdout": "/usr/bin/docker\nDocker version 29.1.3, build 29.1.3-0ubuntu3~22.04.1",
    "stderr": "",
    "duration_s": 0.014
  },
  "python_sh_paths": {
    "cmd": "find /home/horde /opt /data /home/horde/.openclaw/workspace/omniperf -maxdepth 5 \\( -name python.sh -o -name isaac-sim.sh \\) 2>/dev/null | head -100",
    "returncode": 0,
    "stdout": "/home/horde/venvs/isaacsim45/isaac-sim.sh\n/home/horde/venvs/isaacsim45/python.sh",
    "stderr": "",
    "duration_s": 0.188
  },
  "isaaclab_paths": {
    "cmd": "find /home/horde /opt /data /home/horde/.openclaw/workspace/omniperf -maxdepth 5 -name isaaclab.sh 2>/dev/null | head -100",
    "returncode": 0,
    "stdout": "/home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh",
    "stderr": "",
    "duration_s": 0.109
  },
  "cuda_apt_repos": {
    "cmd": "ls /etc/apt/sources.list.d/*cuda* 2>/dev/null || true",
    "returncode": 0,
    "stdout": "/etc/apt/sources.list.d/cuda-ubuntu2204-x86_64.list",
    "stderr": "",
    "duration_s": 0.002
  },
  "nsight_opt": {
    "cmd": "find /opt/nvidia/nsight-systems -maxdepth 4 -type f -name nsys 2>/dev/null | head -20",
    "returncode": 0,
    "stdout": "/opt/nvidia/nsight-systems/2025.6.3/target-linux-x64/nsys",
    "stderr": "",
    "duration_s": 0.003
  },
  "allocwrapper": {
    "cmd": "find ~/.cache/packman -name liballocwrapper.so 2>/dev/null | head -20",
    "returncode": 0,
    "stdout": "",
    "stderr": "",
    "duration_s": 0.316
  }
}
```
