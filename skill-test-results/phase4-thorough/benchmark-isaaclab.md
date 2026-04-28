# benchmark-isaaclab thorough test

Overall status: `blocked_needs_approval`

| Check | Status | Detail |
|---|---|---|
| benchmark scripts documented | `pass` |  |
| headless/viz guidance | `pass` |  |
| tiny env/frame params documented | `pass` |  |
| Isaac Lab install available for --help/run | `pass` | [3g<br>H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H   <br>[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh<br>Isaac Lab OK |
| long RL training not run | `blocked_needs_approval` | requires installed Isaac Lab and explicit approval |

## Evidence

```json
{
  "discovery": {
    "isaaclab_paths": {
      "cmd": "find /home/horde /opt /data /home/horde/.openclaw/workspace/omniperf -maxdepth 5 -name isaaclab.sh 2>/dev/null | head -100",
      "returncode": 0,
      "stdout": "/home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh",
      "stderr": "",
      "duration_s": 0.114
    },
    "isaaclab_verify": {
      "cmd": "if [ -x /home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh ]; then env TERM=xterm bash -lc 'cd /home/horde/.openclaw/workspace/IsaacLab && ./isaaclab.sh -p -c \"import isaaclab; print(\\\"Isaac Lab OK\\\")\"'; else echo \"no known isaaclab.sh\"; exit 42; fi",
      "returncode": 0,
      "stdout": "\u001b[3g\n\u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH   \n[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh\nIsaac Lab OK",
      "stderr": "",
      "duration_s": 0.042
    }
  }
}
```
