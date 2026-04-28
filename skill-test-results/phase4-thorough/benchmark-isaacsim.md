# benchmark-isaacsim thorough test

Overall status: `blocked_needs_approval`

| Check | Status | Detail |
|---|---|---|
| benchmark scripts documented | `pass` |  |
| tiny benchmark parameters possible | `pass` |  |
| Isaac Sim import available | `pass` | Isaac Sim OK |
| Isaac Sim benchmark scripts available locally | `blocked_missing_prereq` | pip install lacks standalone_examples/benchmarks scripts |
| KPI/output path guidance | `pass` |  |
| heavy benchmark sweeps not run | `blocked_needs_approval` | requires benchmark scripts and approval for workloads beyond tiny smoke |

## Evidence

```json
{
  "discovery": {
    "python_sh_paths": {
      "cmd": "find /home/horde /opt /data /home/horde/.openclaw/workspace/omniperf -maxdepth 5 \\( -name python.sh -o -name isaac-sim.sh \\) 2>/dev/null | head -100",
      "returncode": 0,
      "stdout": "/home/horde/venvs/isaacsim45/isaac-sim.sh\n/home/horde/venvs/isaacsim45/python.sh",
      "stderr": "",
      "duration_s": 0.181
    },
    "isaacsim_python_sh_verify": {
      "cmd": "if [ -x /home/horde/venvs/isaacsim45/python.sh ]; then OMNI_KIT_ACCEPT_EULA=YES /home/horde/venvs/isaacsim45/python.sh - <<\"PY\"\nimport isaacsim\nfrom isaacsim.simulation_app import SimulationApp\nprint(\"Isaac Sim OK\")\nPY\nelse echo \"no known isaacsim python.sh\"; exit 42; fi",
      "returncode": 0,
      "stdout": "Isaac Sim OK",
      "stderr": "",
      "duration_s": 0.109
    },
    "isaacsim_benchmark_scripts": {
      "cmd": "find /home/horde/venvs/isaacsim45 /home/horde/.openclaw/workspace -maxdepth 8 -path \"*standalone_examples/benchmarks*\" -type f 2>/dev/null | head -50",
      "returncode": 0,
      "stdout": "",
      "stderr": "",
      "duration_s": 0.31
    }
  }
}
```
