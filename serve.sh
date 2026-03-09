#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA Corporation
# SPDX-License-Identifier: Apache-2.0
PORT=8765
lsof -ti:$PORT | xargs kill -9 2>/dev/null
cd "$(dirname "$0")/docs" && python3 -m http.server $PORT
