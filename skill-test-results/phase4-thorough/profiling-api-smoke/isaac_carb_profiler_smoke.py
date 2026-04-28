from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})
try:
    import carb.profiler
    profiler = carb.profiler.acquire_profiler_interface()
    mask = 1
    old_mask = profiler.get_capture_mask()
    profiler.set_capture_mask(mask)
    profiler.begin(mask, "profiling_api_smoke_manual")
    try:
        total = sum(i * i for i in range(1000))
        profiler.value_int(mask, total, "profiling_api_smoke_value")
        profiler.instant(mask, carb.profiler.InstantType.THREAD, "profiling_api_smoke_instant")
        profiler.frame(mask, "profiling_api_smoke_frame")
        for _ in range(3):
            simulation_app.update()
    finally:
        profiler.end(mask)
        profiler.set_capture_mask(old_mask)
    print("profiling api smoke OK", flush=True)
finally:
    simulation_app.close()
