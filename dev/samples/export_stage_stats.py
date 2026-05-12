import asyncio
import json
import logging
import os

import omni
import omni.kit.app
import omni.ui
from pxr import UsdUtils

logger = logging.getLogger(__name__)

OUTPUT_JSON = "./stage_stats.json"


async def wait_for_frames(count: int):
    for _ in range(count):
        await omni.kit.app.get_app().next_update_async()


async def get_stage_stats() -> dict[str, dict]:
    # 1) Try to get Statistics window handle
    stats_window = omni.ui.Workspace.get_window("Statistics")
    if not stats_window:
        # If not available, enable omni.kit.window.stats extension immediately
        try:
            manager = omni.kit.app.get_app().get_extension_manager()
            manager.set_extension_enabled_immediate("omni.kit.window.stats", True)
            stats_window = omni.ui.Workspace.get_window("Statistics")
        except Exception as e:
            logger.warning(f"Failed to enable omni.kit.window.stats: {e}")

    # 2) Show the Statistics window and wait 200 frames so stats accumulate
    if stats_window:
        omni.ui.Workspace.show_window("Statistics", True)
        # Wait for frames to ensure stats are populated
        await wait_for_frames(200)

    # 3) Get the active stage
    stage = omni.usd.get_context().get_stage()
    if not stage:
        logger.warning("get_stage_stats: No stage found, won't return any data")
        return {}

    # 4) USD stats
    usd_stats = UsdUtils.ComputeUsdStageStats(stage)
    stage_stat = {"usd_stat": {}, "rtx_stat": {}, "so_stat": {}}
    if usd_stats:
        stage_stat["usd_stat"] = usd_stats

    # 5) Stats interface + scopes
    _stats_if = omni.stats.get_stats_interface()
    _scopes = _stats_if.get_scopes()

    # 6) Collect RTX Scene stats (flat)
    rtx_stat = {}
    stats = []
    _scopes_rtx = [x for x in _scopes if x["name"] in "RTX Scene"]
    for scope in _scopes_rtx:
        stats = _stats_if.get_stats(scope["scopeId"])

    for x in stats:
        name = x["name"].replace(" - ", "_")
        name = name.replace(" ", "_")
        rtx_stat[name] = x["value"]
    stage_stat["rtx_stat"] = rtx_stat

    # 7) Collect Scene Optimizer stats with nested hierarchy
    def build_hierarchy_by_level(stats_list):
        """Build hierarchical stat names based on level field"""
        result = {}
        stack = [(result, -1, "")]  # (current_dict, level, prefix)

        for stat in stats_list:
            name = stat["name"].replace(" - ", "_").replace(" ", "_")
            level = stat.get("level", 0)
            value = stat.get("value", 0)

            # Pop stack until we find the parent level
            while len(stack) > 1 and stack[-1][1] >= level:
                stack.pop()

            parent_dict, parent_level, parent_prefix = stack[-1]
            full_name = f"{parent_prefix}_{name}" if parent_prefix else name

            parent_dict[full_name] = value

            # Push this level onto stack for potential children
            stack.append((parent_dict, level, full_name))

        return result

    so_stat = {}
    _scopes_so = [x for x in _scopes if "Scene Optimizer" in x["name"]]
    for scope in _scopes_so:
        so_stats = _stats_if.get_stats_nested(scope["scopeId"])
        if so_stats:
            scope_stats = build_hierarchy_by_level(so_stats)
            so_stat.update(scope_stats)

    stage_stat["so_stat"] = so_stat

    # 8) Hide Statistics window
    if stats_window:
        omni.ui.Workspace.show_window("Statistics", False)
        await wait_for_frames(2)

    return stage_stat


async def main():
    stats = await get_stage_stats()
    print(stats)
    try:
        out_path = os.path.abspath(os.path.expanduser(OUTPUT_JSON))
        with open(out_path, "w") as f:
            json.dump(stats, f, indent=4, default=str)
        print(f"[stage_stats] wrote {out_path}")
    except Exception as e:
        print(f"[stage_stats] write failed: {e}")

asyncio.ensure_future(main())
