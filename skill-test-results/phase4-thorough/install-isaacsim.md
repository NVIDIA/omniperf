# install-isaacsim thorough test

Overall status: `warning`

| Check | Status | Detail |
|---|---|---|
| Python version matrix present | `pass` |  |
| Isaac Sim path discovery | `pass` | /home/horde/venvs/isaacsim45/isaac-sim.sh<br>/home/horde/venvs/isaacsim45/python.sh |
| Isaac Sim verified via discovered python.sh | `pass` | Isaac Sim OK |
| Docker availability checked without starting container | `pass` | /usr/bin/docker<br>Docker version 29.1.3, build 29.1.3-0ubuntu3~22.04.1 |
| sudo/package install examples are present and need approval | `warning` |  |
| cleanup command is documented | `warning` | cleanup must stay approval-gated |

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
    "python_import_isaacsim": {
      "cmd": "python3 - <<\"PY\"\ntry:\n import isaacsim\n print(\"isaacsim import OK\")\nexcept Exception as e:\n print(type(e).__name__ + \": \" + str(e))\n raise SystemExit(42)\nPY",
      "returncode": 42,
      "stdout": "ModuleNotFoundError: No module named 'isaacsim'",
      "stderr": "",
      "duration_s": 0.012
    },
    "isaacsim_python_sh_verify": {
      "cmd": "if [ -x /home/horde/venvs/isaacsim45/python.sh ]; then OMNI_KIT_ACCEPT_EULA=YES /home/horde/venvs/isaacsim45/python.sh - <<\"PY\"\nimport isaacsim\nfrom isaacsim.simulation_app import SimulationApp\nprint(\"Isaac Sim OK\")\nPY\nelse echo \"no known isaacsim python.sh\"; exit 42; fi",
      "returncode": 0,
      "stdout": "Isaac Sim OK",
      "stderr": "",
      "duration_s": 0.109
    },
    "docker": {
      "cmd": "command -v docker && docker --version",
      "returncode": 0,
      "stdout": "/usr/bin/docker\nDocker version 29.1.3, build 29.1.3-0ubuntu3~22.04.1",
      "stderr": "",
      "duration_s": 0.014
    }
  }
}
```
