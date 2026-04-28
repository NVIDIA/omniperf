# profiling thorough test

Overall status: `pass`

| Check | Status | Detail |
|---|---|---|
| nsys availability | `pass` | /usr/local/bin/nsys |
| perf_event_paranoid read | `pass` | 4 |
| non-sudo default documented | `pass` |  |
| GPU metrics permission fallback documented | `pass` |  |
| Tracy capture sequence documented | `pass` |  |

## Evidence

```json
{
  "host": {
    "perf_event_paranoid": {
      "cmd": "cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo unavailable",
      "returncode": 0,
      "stdout": "4",
      "stderr": "",
      "duration_s": 0.002
    }
  },
  "tiny_nsys": {
    "cmd": "nsys profile --force-overwrite=true -o /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase4-thorough/tiny -t nvtx,osrt python3 /home/horde/.openclaw/workspace/omniperf/skill-test-results/phase4-thorough/tiny_profile.py",
    "returncode": 0,
    "stdout": "tiny\nCollecting data...\nGenerating '/tmp/nsys-report-6c48.qdstrm'\n\n[1/1] [0%                          ] tiny.nsys-rep\n[1/1] [0%                          ] tiny.nsys-rep\n[1/1] [======33%                   ] tiny.nsys-rep\n[1/1] [===============67%          ] tiny.nsys-rep\n[1/1] [====================83%     ] tiny.nsys-rep\n[1/1] [========================100%] tiny.nsys-rep\n[1/1] [========================100%] tiny.nsys-rep\nGenerated:\n\t/home/horde/.openclaw/workspace/omniperf/skill-test-results/phase4-thorough/tiny.nsys-rep",
    "stderr": "WARNING: The version of the system or its configuration does not allow enabling CPU profiling:\n- CPU IP/backtrace sampling will be disabled.\n- CPU context switch tracing will be disabled.\nTry the 'nsys status --environment' command to learn more.",
    "duration_s": 2.079
  }
}
```
