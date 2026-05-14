---
name: kit-app-streaming-debug
description: Use when investigating Kit app livestream performance bottlenecks, WebRTC/native StreamSDK lag, freezes, dropped frames, browser WebRTC stats, copy fence timeouts, NVST_R_BUSY, disconnects, or resolution mismatch warnings in omni.kit.livestream.
---

# Kit App Streaming Debug

Debug Kit livestream performance end-to-end before jumping into generic profiling. Always collect both server-side Kit logs and browser-side WebRTC evidence, then correlate by timestamp around the lag/freeze event.

## Collect Kit Evidence

Run the Kit app with StreamSDK event tracing and verbose file logs. Keep `--no-window` for app-stream tests when resolution mismatch is suspected.

```bash
# Windows
.\repo.bat launch -- --no-window --/exts/omni.kit.livestream.app/primaryStream/enableEventTracing=true --/log/channels/omni.kit.livestream.streamsdk=verbose --/log/fileLogLevel=verbose

# Linux
./repo.sh launch -- --no-window --/exts/omni.kit.livestream.app/primaryStream/enableEventTracing=true --/log/channels/omni.kit.livestream.streamsdk=verbose --/log/fileLogLevel=verbose
```

If extension context is needed, also enable:

```bash
--/log/channels/omni.kit.livestream.webrtc=verbose
--/log/channels/omni.kit.livestream.app=verbose
```

Extract the known streaming failure markers:

```bash
rg -n -C 3 "Timeout of [0-9]+ms exceeded waiting for copy fence|Cannot stream video frame because the video stream is not connected|Still cannot stream video frame|Cannot stream video frame with resolution|NVST_R_BUSY|Client disconnected from WebRTC server" path/to/kit.log
```

Interpret them this way:

| Marker | Likely cause | Next check |
|---|---|---|
| `Timeout of 1000ms exceeded waiting for copy fence` | Renderer/GPU stall before the framebuffer copy completes | Correlate with frame time, GPU utilization, and Tracy/NSight render zones |
| `Cannot stream video frame because the video stream is not connected` | WebRTC session has not established, or video stream dropped | Check browser ICE state, connection events, and nearby disconnect logs |
| `Still cannot stream video frame...` | Connection did not recover inside the wait timeout, frame dropped | Treat as stream/session instability, not render cost by itself |
| `Cannot stream video frame with resolution ... differs...` | OS/window resize or AOV/render resolution changed after connect | Try `--no-window`, fixed resolution, disable viewport fill behavior, or use dynamic resize only if required |
| `NVST_R_BUSY` | StreamSDK is not accepting frames fast enough | If not adjacent to disconnect/reconnect, suspect encoder, network, or client backpressure |
| `Client disconnected from WebRTC server` | Client/session dropped | Align with browser ICE/NACK/PLI/freeze events |

## Collect Browser Evidence

Open `chrome://webrtc-internals` before connecting to the stream. After a lag event, use **Create dump** and inspect packet loss, jitter, frames dropped, decode time, bitrate, freezes, NACK/PLI, and the selected ICE candidate pair.

For `~/proj/ov-web-rtc`, run the dev client with `npm run dev` and capture console logs. Add or inspect an `onStreamStats` callback like:

```ts
onStreamStats: (message: StatsEvent) => {
  const s = message.data.stats;
  console.table({
    fps: s.fps,
    rtdMs: s.rtd,
    decodeMs: s.avgDecodeTime,
    frameLoss: s.frameLoss,
    packetLoss: s.packetLoss,
    bandwidthMbps: s.totalBandwidth,
    bitrateMbps: s.currentBitrate,
    utilizedPct: s.utilizedBandwidth,
    resolution: `${s.streamingResolutionWidth}x${s.streamingResolutionHeight}`,
    codec: s.codec,
  });
}
```

Browser-side interpretation:

| Symptom | Likely bottleneck |
|---|---|
| High `avgDecodeTime`, low packet loss | Client decode/GPU/display bottleneck |
| High `packetLoss`, `frameLoss`, NACK/PLI, jitter, or freezes | Network or congestion problem |
| `utilizedBandwidth` near 100%, bitrate near/above available bandwidth | Bandwidth cap or congestion control |
| Low browser FPS with clean browser stats but Kit copy-fence/NVST warnings | Server render/copy/encoder/backpressure |
| Browser resolution differs from expected Kit stream resolution | Resize/configuration mismatch |

## Profiling Follow-Up

Use Tracy only after logs indicate the server side is involved. Add the profiling args to the same Kit run:

```bash
--/app/profilerBackend=tracy --/app/profileFromStart=true --/profiler/gpu/tracyInject/enabled=true --/app/profilerMask=1 --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false --/profiler/channels/carb.events/enabled=false --/profiler/channels/carb.tasking/enabled=false --/rtx/addTileGpuAnnotations=true --/profiler/enabled=true --/profiler/gpu=true --enable omni.kit.profiler.window
```

Use the `profiling` skill for capture mechanics and `nsys-analyze` for trace analysis. Do not promise StreamSDK-internal zones when StreamSDK source is unavailable; correlate log timestamps with surrounding Kit zones such as `SharedFrameBuffer::waitForCopy`, `SharedFrameBuffer::streamBuffer`, render zones, and frame markers.

## Report Shape

Summarize:

1. Kit run args and log path.
2. Browser artifacts: console stats and `webrtc-internals` dump.
3. Timeline around the lag event.
4. Matched markers and likely bottleneck category: renderer/GPU, session/network, resize/config, StreamSDK/encoder backpressure, or client decode.
5. Next action: config fix, network/client investigation, or server-side profiling.

Source references in this workspace: `~/proj/kit-livestream` for `omni.kit.livestream.app` and `omni.kit.livestream.webrtc`; `~/proj/ov-web-rtc` for browser stats and dev client logging.
