# Phase 1 — Host Prerequisite Snapshot

## uname

- return code: `0`

```text
Linux abaillet-horde-dgxc-14 5.15.0-113-generic #123-Ubuntu SMP Mon Jun 10 08:16:17 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
```

## os_release

- return code: `0`

```text
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
```

## disk_workspace

- return code: `0`

```text
Filesystem      Size  Used Avail Use% Mounted on
overlay         877G  680G  161G  81% /
```

## git

- return code: `0`

```text
git version 2.34.1
```

## python3

- return code: `0`

```text
Python 3.10.12
```

## python

- return code: `0`

```text

```

## pip

- return code: `0`

```text
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)
```

## conda

- return code: `0`

```text
conda 26.1.1
```

## uv

- return code: `0`

```text
uv 0.11.8 (x86_64-unknown-linux-gnu)
```

## nvidia_smi

- return code: `0`

```text
Tue Apr 28 08:12:35 2026
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 570.158.01             Driver Version: 570.158.01     CUDA Version: 12.8     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA L40                     On  |   00000000:19:00.0 Off |                  Off |
| N/A   25C    P8             35W /  300W |       1MiB /  49140MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

## nvidia_smi_query

- return code: `0`

```text
NVIDIA L40, 570.158.01, 49140 MiB, 1 MiB, 25, P8, 210 MHz, 405 MHz
```

## nsys

- return code: `0`

```text
NVIDIA Nsight Systems version 2025.6.3.541-256337736014v0
```

## sqlite3

- return code: `0`

```text
3.37.2 2022-01-06 13:25:41 872ba256cbf61d9290b571c0e6d82a20c224ca3ad82971edc46b29818d5dalt1
```

## csvexport

- return code: `0`

```text

```

## tracy_capture

- return code: `0`

```text
/usr/local/bin/tracy-capture
Usage: capture -o output.tracy [-a address] [-p port] [-f] [-s seconds] [-m memlimit]
```

## common_isaac_paths

- return code: `0`

```text
/home/horde/venvs/isaacsim45/python.sh
/home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh
```

