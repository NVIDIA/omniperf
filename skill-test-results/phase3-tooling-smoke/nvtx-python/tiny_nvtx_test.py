import time
try:
    import nvtx
except Exception as e:
    print(f"NVTX_IMPORT_FAILED: {e!r}")
    raise SystemExit(42)

@nvtx.annotate("tiny_work", color="blue")
def tiny_work():
    total = 0
    for i in range(10000):
        total += i*i
    time.sleep(0.01)
    return total

print("RESULT", tiny_work())
