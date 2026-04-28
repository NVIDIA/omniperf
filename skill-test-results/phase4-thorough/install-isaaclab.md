# install-isaaclab thorough test

Overall status: `pass`

| Check | Status | Detail |
|---|---|---|
| mode selection documented | `pass` |  |
| conda availability | `pass` | /usr/local/bin/conda<br>conda 26.1.1 |
| uv availability | `pass` | /home/horde/.local/bin/uv<br>uv 0.11.8 (x86_64-unknown-linux-gnu) |
| Isaac Lab path discovery | `pass` | /home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh |
| Isaac Lab import verification | `pass` | [3g<br>H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H   <br>[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh<br>Isaac Lab OK |
| avoids conda init mutation | `pass` |  |
| env removal example is approval-gated | `pass` |  |

## Evidence

```json
{
  "discovery": {
    "isaaclab_paths": {
      "cmd": "find /home/horde /opt /data /home/horde/.openclaw/workspace/omniperf -maxdepth 5 -name isaaclab.sh 2>/dev/null | head -100",
      "returncode": 0,
      "stdout": "/home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh",
      "stderr": "",
      "duration_s": 0.109
    },
    "isaaclab_verify": {
      "cmd": "if [ -x /home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh ]; then env TERM=xterm bash -lc 'cd /home/horde/.openclaw/workspace/IsaacLab && ./isaaclab.sh -p -c \"import isaaclab; print(\\\"Isaac Lab OK\\\")\"'; else echo \"no known isaaclab.sh\"; exit 42; fi",
      "returncode": 0,
      "stdout": "\u001b[3g\n\u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH   \n[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh\nIsaac Lab OK",
      "stderr": "",
      "duration_s": 0.039
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
    }
  }
}
```
