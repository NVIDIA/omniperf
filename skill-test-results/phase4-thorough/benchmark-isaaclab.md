# benchmark-isaaclab thorough test

Overall status: `pass_with_warnings`

| Check | Status | Detail |
|---|---|---|
| benchmark scripts documented | `pass` |  |
| headless/viz guidance | `pass` |  |
| tiny env/frame params documented | `pass` |  |
| Isaac Lab install available for --help/run | `pass` | [3g<br>H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H    H   <br>[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh<br>Isaac Lab OK |
| tiny benchmark artifact run | `pass` | 2026-04-28 08:11:25 [10,177ms] [INFO] [isaacsim.benchmark.services.metrics.backend] LocalLogMetricsEvent::add_metrics TestPhase(phase_name='runtime', measurements=[DictMeasurement(name='Step Frametimes', value={'Environment step times': [43.234203, 49.244002, 4.376877, 3.562158, 3.320063, 3.317025, 3.292544, 3.370069, 3.454109, 3.497783], 'Environment step FPS': [23.129835422200337, 20.307041657580957, 228.4734069520345, 280.7287043415817, 301.19910375194684, 301.47496627248813, 303.7165182910236, 296.7298295672878, 289.5102615464654, 285.89538001642757], 'Environment step effective FPS': [370.0773667552054, 324.9126665212953, 3655.574511232552, 4491.659269465307, 4819.185660031149, 4823.599 |
| long RL training not run | `pass_with_warnings` | long RL training/convergence tests intentionally skipped; tiny non-RL benchmark artifact passed |

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
    }
  },
  "tiny_benchmark": {
    "cmd": "env TERM=xterm OMNI_KIT_ACCEPT_EULA=YES bash -lc 'cd /home/horde/.openclaw/workspace/IsaacLab && ./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py --task=Isaac-Cartpole-Direct-v0 --headless --num_frames 10 --num_envs 16 --benchmark_backend LocalLogMetrics'",
    "returncode": 0,
    "stdout": "\u001b[3g\n\u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH    \u001bH   \n[INFO] Using python from: /home/horde/.openclaw/workspace/IsaacLab/_isaac_sim/python.sh\n[INFO][AppLauncher]: Using device: cuda:0\n[INFO][AppLauncher]: Loading experience file: /home/horde/.openclaw/workspace/IsaacLab/apps/isaacsim_4_5/isaaclab.python.headless.kit\n2026-04-28 08:11:20 [5,390ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Generating formatted report = True\n2026-04-28 08:11:20 [5,390ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Using metrics backend = LocalLogMetrics\n2026-04-28 08:11:20 [5,390ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Local folder location = /tmp\n2026-04-28 08:11:20 [5,390ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Starting\n2026-04-28 08:11:20 [5,390ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Test mode = False\n[INFO]: Parsing configuration from: isaaclab_tasks.direct.cartpole.cartpole_env:CartpoleEnvCfg\n[2026-04-28 08:11:21,059][isaaclab.envs.direct_rl_env][WARNING] - Seed not set for the environment. The environment creation may not be deterministic.\n\n\u001b[36m======================================================================================\u001b[0m\n\u001b[36m\u001b[1m[INFO][IsaacLab]: Logging to file: /tmp/isaaclab/logs/isaaclab_2026-04-28_08-11-21.log\u001b[0m\n\u001b[36m======================================================================================\u001b[0m\n\n\u001b[33m08:11:21 [stage.py] WARNING: Isaac Sim < 5.0 does not support thread-local stage contexts. Skipping use_stage().\u001b[0m\n\u001b[33m08:11:21 [simulation_context.py] WARNING: The `enable_external_forces_every_iteration` parameter in the PhysxCfg is set to False. If you are experiencing noisy velocities, consider enabling this flag. You may need to slightly increase the number of velocity iterations (setting it to 1 or 2 rather than 0), together with this flag, to improve the accuracy of velocity updates.\u001b[0m\n[INFO]: Base environment:\n\tEnvironment device    : cuda:0\n\tEnvironment seed      : None\n\tPhysics step-size     : 0.008333333333333333\n\tRendering step-size   : 0.016666666666666666\n\tEnvironment step-size : 0.016666666666666666\n[INFO]: Time taken for scene creation : 0.619895 seconds\n[INFO]: Scene manager:  <class InteractiveScene>\n\tNumber of environments: 16\n\tEnvironment spacing   : 4.0\n\tSource prim name      : /World/envs/env_0\n\tGlobal prim paths     : []\n\tReplicate physics     : True\n[INFO]: Starting the simulation. This may take a few seconds. Please wait...\n\u001b[33m08:11:22 [articulation.py] WARNING: Spatial tendons are not supported in Isaac Sim < 5.0: patching spatial-tendon getter and setter to use dummy value\u001b[0m\n[INFO]: Time taken for simulation start : 0.632886 seconds\n[INFO]: Completed setting up the environment...\n2026-04-28 08:11:22 [7,008ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Starting phase: sim_runtime\n2026-04-28 08:11:25 [10,175ms] [WARNING] [isaacsim.benchmark.services.datarecorders.frametime] Unable to calculate frametime stats: mean requires at least one data point\n2026-04-28 08:11:25 [10,176ms] [WARNING] [isaacsim.benchmark.services.datarecorders.frametime] Unable to calculate frametime stats: mean requires at least one data point\n2026-04-28 08:11:25 [10,176ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Created new phase 'startup' and stored SingleMeasurement(name='App Launch Time', value=4297.178598, unit='ms', type='single')\n2026-04-28 08:11:25 [10,176ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Stored SingleMeasurement(name='Python Imports Time', value=89.168287, unit='ms', type='single') for phase 'startup'\n2026-04-28 08:11:25 [10,176ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Stored SingleMeasurement(name='Task Creation and Start Time', value=1299.96236, unit='ms', type='single') for phase 'startup'\n2026-04-28 08:11:25 [10,176ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Stored SingleMeasurement(name='Scene Creation Time', value=619.8950093239546, unit='ms', type='single') for phase 'startup'\n2026-04-28 08:11:25 [10,176ms] [INFO] [isaacsim.benchmark.services.base_isaac_benchmark] Stored SingleMeasurement(name='Simulation Start Time', value=632.8857820481062, unit='ms', type='single') for phase 'startup'\n2026-04-28 08:11
```
