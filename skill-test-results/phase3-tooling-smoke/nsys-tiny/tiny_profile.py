import time
for i in range(5):
    sum(j*j for j in range(200000))
    time.sleep(0.02)
print("tiny profile done")
