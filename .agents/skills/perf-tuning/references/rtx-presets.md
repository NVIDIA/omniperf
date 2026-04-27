# IsaacLab RTX Preset Parameter Comparison

Full enumeration of every RTX/performance-related parameter **explicitly set** in each preset's `.kit` file (`IsaacLab/apps/rendering_modes/{performance,balanced,quality}.kit`).

`(commented)` = line present but commented out (engine default applies).

| # | Setting | quality | balanced | performance |
|---|---|---|---|---|
| 1 | `/rtx/translucency/enabled` | true | false | false |
| 2 | `/rtx/reflections/enabled` | true | false | false |
| 3 | `/rtx/reflections/denoiser/enabled` | true | true | **false** |
| 4 | `/rtx/directLighting/sampledLighting/denoisingTechnique` | *(commented)* | *(commented)* | **0** |
| 5 | `/rtx/directLighting/sampledLighting/enabled` | true | true | **false** |
| 6 | `/rtx/sceneDb/ambientLightIntensity` | 1.0 | 1.0 | 1.0 |
| 7 | `/rtx/shadows/enabled` | true | true | true |
| 8 | `/rtx/indirectDiffuse/enabled` | true | false | false |
| 9 | `/rtx/indirectDiffuse/denoiser/enabled` | true | true | **false** |
| 10 | `/rtx/domeLight/upperLowerStrategy` | *(commented, =4)* | *(commented)* | **3** |
| 11 | `/rtx/ambientOcclusion/enabled` | true | false | false |
| 12 | `/rtx/ambientOcclusion/denoiserMode` | 0 | 1 | 1 |
| 13 | `/rtx/raytracing/subpixel/mode` | 1 | 0 | 0 |
| 14 | `/rtx/raytracing/cached/enabled` | true | true | **false** |
| 15 | `/rtx-transient/dlssg/enabled` | false | false | false |
| 16 | `/rtx-transient/dldenoiser/enabled` | true | true | **false** |
| 17 | `/rtx/post/dlss/execMode` | **2** | **1** | **0** |
| 18 | `/rtx/pathtracing/maxSamplesPerLaunch` | 1000000 | 1000000 | 1000000 |
| 19 | `/rtx/viewTile/limit` | 1000000 | 1000000 | 1000000 |

Items 18–19 are common safety caps (avoid warnings in replicator/tiled-camera setups). No measurable performance impact.

## Ablation Results (ChessRTX path-traced, RTX PRO 6000 Blackwell)

- Of `isaaclab_performance`'s **+115.8%** gain, ~91% comes from `--/rtx/post/dlss/execMode=0` alone.
- `/rtx-transient/dldenoiser=false` is the second most impactful single toggle (−6% when re-enabled).
- Individual effect toggles (translucency, reflections, indirectDiffuse, AO, etc.) are ±1% noise on this scene — GPU saturated on the core path-trace loop.
- Scene-dependent: individual toggles may have larger impact on scenes where the specific effect is visually dominant.
