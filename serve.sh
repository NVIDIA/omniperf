#!/usr/bin/env bash
PORT=8765
lsof -ti:$PORT | xargs kill -9 2>/dev/null
cd "$(dirname "$0")/docs" && python3 -m http.server $PORT
