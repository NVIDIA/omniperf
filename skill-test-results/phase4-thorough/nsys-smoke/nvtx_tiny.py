import nvtx, time
with nvtx.annotate('tiny_outer', color='blue'):
    for i in range(3):
        with nvtx.annotate(f'tiny_inner_{i}', color='green'):
            time.sleep(0.01)
print('tiny nvtx done')
