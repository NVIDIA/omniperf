# Phase 3 — Tooling Smoke Tests

## install-profilers

| Tool | Status | Detail |
|---|---|---|
| `nsys` | pass | `/usr/local/bin/nsys` |
| `sqlite3` | pass | `/usr/bin/sqlite3` |
| `csvexport` | pass | `/usr/local/bin/csvexport` |
| `tracy-capture` | pass | `/usr/local/bin/tracy-capture` |
| `tracy-update` | pass | `/usr/local/bin/tracy-update` |

## diagnose-perf

```json
{
  "gpu_query": {
    "cmd": "nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,pstate,clocks_throttle_reasons.active,utilization.gpu,power.draw,power.limit --format=csv,noheader",
    "returncode": 0,
    "stdout": "NVIDIA L40, 570.158.01, 49140 MiB, 1 MiB, 25, P8, 0x0000000000000001, 0 %, 35.65 W, 300.00 W\n",
    "stderr": "",
    "duration_s": 0.069
  },
  "cpu_model": {
    "cmd": "lscpu | grep -E 'Model name|Socket|Core|Thread|NUMA'",
    "returncode": 0,
    "stdout": "Model name:                         Intel(R) Xeon(R) Platinum 8362 CPU @ 2.80GHz\nThread(s) per core:                 2\nCore(s) per socket:                 32\nSocket(s):                          2\nNUMA node(s):                       2\nNUMA node0 CPU(s):                  0-31,64-95\nNUMA node1 CPU(s):                  32-63,96-127\n",
    "stderr": "",
    "duration_s": 0.069
  },
  "cpu_governor": {
    "cmd": "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unavailable",
    "returncode": 0,
    "stdout": "schedutil\n",
    "stderr": "",
    "duration_s": 0.002
  },
  "memory": {
    "cmd": "free -h",
    "returncode": 0,
    "stdout": "               total        used        free      shared  buff/cache   available\nMem:           1.0Ti        48Gi       533Gi       301Mi       425Gi       952Gi\nSwap:             0B          0B          0B\n",
    "stderr": "",
    "duration_s": 0.002
  }
}
```

## nvtx-python

```json
{
  "import_and_run": {
    "cmd": "python3 /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nvtx-python/tiny_nvtx_test.py",
    "returncode": 0,
    "stdout": "RESULT 333283335000\n",
    "stderr": "",
    "duration_s": 0.034
  }
}
```

## profiling

```json
{
  "nsys_profile_tiny_python": {
    "cmd": "nsys profile --force-overwrite=true -o /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nsys-tiny/tiny_python -t nvtx,osrt python3 /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nsys-tiny/tiny_profile.py",
    "returncode": 0,
    "stdout": "tiny profile done\nCollecting data...\nGenerating '/tmp/nsys-report-5068.qdstrm'\n\n[1/1] [0%                          ] tiny_python.nsys-rep\n[1/1] [0%                          ] tiny_python.nsys-rep\n[1/1] [======33%                   ] tiny_python.nsys-rep\n[1/1] [===============66%          ] tiny_python.nsys-rep\n[1/1] [===================82%      ] tiny_python.nsys-rep\n[1/1] [========================100%] tiny_python.nsys-rep\n[1/1] [========================100%] tiny_python.nsys-rep\nGenerated:\n\t/home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nsys-tiny/tiny_python.nsys-rep\n",
    "stderr": "WARNING: The version of the system or its configuration does not allow enabling CPU profiling:\n- CPU IP/backtrace sampling will be disabled.\n- CPU context switch tracing will be disabled.\nTry the 'nsys status --environment' command to learn more.\n\n",
    "duration_s": 2.171
  },
  "artifact": {
    "path": "/home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nsys-tiny/tiny_python.nsys-rep",
    "size_bytes": 66458,
    "committed": false
  }
}
```

## nsys-analyze

```json
{
  "export_sqlite": {
    "cmd": "nsys export --force-overwrite=true --type sqlite --output /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nsys-tiny/tiny_python.sqlite /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase3-tooling-smoke/nsys-tiny/tiny_python.nsys-rep",
    "returncode": 0,
    "stdout": "Processing 268 events: \n",
    "stderr": "\n[1%                                                                            ]\n[2%                                                                            ]\n[3%                                                                            ]\n[=4%                                                                           ]\n[=5%                                                                           ]\n[==6%                                                                          ]\n[===7%                                                                         ]\n[====8%                                                                        ]\n[=====9%                                                                       ]\n[====10%                                                                       ]\n[=====11%                                                                      ]\n[======12%                                                                     ]\n[=======13%                                                                    ]\n[=======14%                                                                    ]\n[========15%                                                                   ]\n[=========16%                                                                  ]\n[==========17%                                                                 ]\n[===========18%                                                                ]\n[===========19%                                                                ]\n[============20%                                                               ]\n[=============21%                                                              ]\n[==============22%                                                             ]\n[==============23%                                                             ]\n[===============24%                                                            ]\n[================25%                                                           ]\n[=================26%                                                          ]\n[==================27%                                                         ]\n[==================28%                                                         ]\n[===================29%                                                        ]\n[====================30%                                                       ]\n[=====================31%                                                      ]\n[=====================32%                                                      ]\n[======================33%                                                     ]\n[=======================34%                                                    ]\n[========================35%                                                   ]\n[=========================36%                                                  ]\n[=========================37%                                                  ]\n[==========================38%                                                 ]\n[===========================39%                                                ]\n[============================40%                                               ]\n[============================41%                                               ]\n[=============================42%                                              ]\n[==============================43%                                             ]\n[===============================44%                                         
```

## profiling-api

```json
{
  "static_doc_check": {
    "has_cpp_macro": true,
    "has_python_api": true,
    "status": "pass"
  }
}
```

## tracy-memory

```json
{
  "allocwrapper_candidates": [],
  "tracy_capture_available": true,
  "status": "blocked_missing_prereq"
}
```

