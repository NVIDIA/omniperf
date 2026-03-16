(function () {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];

  const PRESET_COLORS = [
    "#00d4ff", "#ff3e96", "#00ff88", "#ff6b35", "#ffea00",
    "#7c4dff", "#00bcd4", "#e040fb", "#69f0ae", "#ff5722",
    "#40c4ff", "#ffab40", "#b388ff", "#76ff03", "#ff1744",
    "#18ffff", "#ff4081", "#64ffda", "#ff9100", "#d500f9",
    "#00e676", "#536dfe", "#ffc400", "#84ffff", "#ff5252",
    "#a7ffeb", "#e64a19",
  ];

  const FPS_METRICS_NON_RL = [
    "Mean Environment step FPS",
    "Mean Environment step effective FPS",
  ];
  const FPS_METRICS_RLGAMES = [
    "Mean Environment + Inference + Policy update FPS",
    "Mean Environment + Inference FPS",
    "Mean Environment only FPS",
  ];
  const FPS_METRICS_RSL_RL = [
    "Mean Total FPS",
    "Max Total FPS",
    "Min Total FPS",
  ];

  function getFpsMetrics(workflow) {
    if (workflow.includes("rlgames")) return FPS_METRICS_RLGAMES;
    if (workflow.includes("rsl_rl")) return FPS_METRICS_RSL_RL;
    return FPS_METRICS_NON_RL;
  }

  function getRepFpsMetric(workflow) {
    if (workflow.includes("rlgames")) return "Mean Environment + Inference + Policy update FPS";
    if (workflow.includes("rsl_rl")) return "Mean Total FPS";
    return "Mean Environment step effective FPS";
  }

  const ENV_SIZES = [1024, 2048, 4096, 8192, 16384, 32768];

  const state = {
    datasets: {},
    manifest: null,
    currentGpu: null,
    currentTab: "comparison",
    compRunIndex: 0,
    compTask: "",
    compWorkflow: "benchmark_rlgames_train",
    compPhysicsFilter: new Set(),
    compRendererFilter: new Set(),
    compDatatypeFilter: new Set(),
    compFilterRunIndex: -1,
    compSorts: {},
    histTask: "",
    histWorkflow: "benchmark_rlgames_train",
    histMetric: "",
    histPhysicsFilter: new Set(),
    histRendererFilter: new Set(),
    histDatatypeFilter: new Set(),
    histFilterInited: false,
    histRunDetail: -1,
    histChart: null,
    scalingRunIndex: -1,
    compEnv: "",
    compResolution: "",
    histEnv: "",
    histResolution: "",
    scalingResolution: "",
    scalingLinearX: false,
    scalingEnvFilter: new Set(ENV_SIZES.map(String)),
  };

  let compControlsInitialized = false;

  /* ─── URL State ─── */

  function readUrlState() {
    const p = new URLSearchParams(window.location.search);
    if (p.has("gpu")) state.currentGpu = p.get("gpu");
    if (p.has("tab")) state.currentTab = p.get("tab");
    if (p.has("run")) {
      state.compRunIndex = parseInt(p.get("run"), 10);
      compControlsInitialized = true;
    }
    if (p.has("task")) state.compTask = p.get("task");
    if (p.has("workflow")) state.compWorkflow = p.get("workflow");
    if (p.has("env")) state.compEnv = p.get("env");
    if (p.has("res")) state.compResolution = p.get("res");
    if (p.has("htask")) state.histTask = p.get("htask");
    if (p.has("hworkflow")) state.histWorkflow = p.get("hworkflow");
    if (p.has("hmetric")) state.histMetric = p.get("hmetric");
    if (p.has("henv")) state.histEnv = p.get("henv");
    if (p.has("hres")) state.histResolution = p.get("hres");
    if (p.has("sres")) state.scalingResolution = p.get("sres");
    if (p.has("slinear")) state.scalingLinearX = p.get("slinear") === "1";
    if (p.has("senvs")) {
      const envList = p.get("senvs").split(",").filter(Boolean);
      if (envList.length > 0) state.scalingEnvFilter = new Set(envList);
    }
    if (p.has("phys")) {
      const list = p.get("phys").split(",").filter(Boolean);
      if (list.length > 0) { state.compPhysicsFilter = new Set(list); state.compFilterFromUrl = true; }
    }
    if (p.has("rend")) {
      const list = p.get("rend").split(",").filter(Boolean);
      if (list.length > 0) { state.compRendererFilter = new Set(list); state.compFilterFromUrl = true; }
    }
    if (p.has("sorts")) {
      for (const part of p.get("sorts").split("|")) {
        const sep = part.lastIndexOf(":");
        if (sep < 0) continue;
        const metric = decodeURIComponent(part.substring(0, sep));
        const dir = part.substring(sep + 1);
        state.compSorts[metric] = dir !== "asc";
      }
    }
    if (p.has("dt")) {
      const dtList = p.get("dt").split(",").filter(Boolean);
      if (dtList.length > 0) { state.compDatatypeFilter = new Set(dtList); state.compFilterFromUrl = true; }
    }
    if (p.has("hrun")) state.histRunDetail = parseInt(p.get("hrun"), 10);
    if (p.has("hphys")) {
      state.histPhysicsFilter = new Set(p.get("hphys").split(",").filter(Boolean));
      state.histFilterInited = true;
    }
    if (p.has("hrend")) {
      state.histRendererFilter = new Set(p.get("hrend").split(",").filter(Boolean));
      state.histFilterInited = true;
    }
    if (p.has("hdt")) {
      state.histDatatypeFilter = new Set(p.get("hdt").split(",").filter(Boolean));
      state.histFilterInited = true;
    }
  }

  function syncUrlState() {
    const p = new URLSearchParams();
    if (state.currentGpu) p.set("gpu", state.currentGpu);
    if (state.currentTab && state.currentTab !== "comparison") p.set("tab", state.currentTab);
    if (state.currentTab === "comparison") {
      if (state.compRunIndex != null) p.set("run", state.compRunIndex);
      if (state.compTask) p.set("task", state.compTask);
      if (state.compWorkflow) p.set("workflow", state.compWorkflow);
      if (state.compEnv) p.set("env", state.compEnv);
      if (state.compResolution) p.set("res", state.compResolution);
      if (state.compPhysicsFilter.size > 0) p.set("phys", [...state.compPhysicsFilter].sort().join(","));
      if (state.compRendererFilter.size > 0) p.set("rend", [...state.compRendererFilter].sort().join(","));
      if (state.compDatatypeFilter.size > 0) p.set("dt", [...state.compDatatypeFilter].sort().join(","));
      const sortEntries = Object.entries(state.compSorts);
      if (sortEntries.length > 0) {
        p.set("sorts", sortEntries.map(([m, desc]) => `${m}:${desc ? "desc" : "asc"}`).join("|"));
      }
    } else if (state.currentTab === "history") {
      if (state.histTask) p.set("htask", state.histTask);
      if (state.histWorkflow) p.set("hworkflow", state.histWorkflow);
      if (state.histMetric) p.set("hmetric", state.histMetric);
      if (state.histEnv) p.set("henv", state.histEnv);
      if (state.histResolution) p.set("hres", state.histResolution);
      if (state.histRunDetail >= 0) p.set("hrun", state.histRunDetail);
      if (state.histPhysicsFilter.size > 0) p.set("hphys", [...state.histPhysicsFilter].sort().join(","));
      if (state.histRendererFilter.size > 0) p.set("hrend", [...state.histRendererFilter].sort().join(","));
      if (state.histDatatypeFilter.size > 0) p.set("hdt", [...state.histDatatypeFilter].sort().join(","));
    } else if (state.currentTab === "scaling") {
      if (state.scalingResolution) p.set("sres", state.scalingResolution);
      if (state.scalingLinearX) p.set("slinear", "1");
      if (state.scalingEnvFilter.size < ENV_SIZES.length) {
        p.set("senvs", [...state.scalingEnvFilter].sort((a, b) => a - b).join(","));
      }
    }
    const qs = p.toString();
    const newUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    history.replaceState(null, "", newUrl);
  }

  /* ─── Data Loading ─── */

  const _bustCache = `v=${Date.now()}`;

  async function loadManifest() {
    const resp = await fetch(`data/manifest.json?${_bustCache}`);
    state.manifest = await resp.json();
    return state.manifest;
  }

  async function loadGpuData(filename) {
    if (state.datasets[filename]) return state.datasets[filename];
    const resp = await fetch(`data/${filename}?${_bustCache}`);
    const data = await resp.json();
    state.datasets[filename] = data;
    return data;
  }

  function getCurrentData() {
    if (!state.manifest || !state.currentGpu) return null;
    const entry = state.manifest.datasets.find(
      (d) => d.gpu_type === state.currentGpu
    );
    return entry ? state.datasets[entry.file] : null;
  }

  /* ─── Helpers ─── */

  const DISPLAY_RENAME = { "newton_renderer": "newton_sensors" };
  const HIDDEN_PRESETS = ["default", "rsl_rl"];
  const HIDDEN_WORKFLOWS = [];

  function isHiddenPreset(preset) {
    if (!preset) return true;
    return HIDDEN_PRESETS.includes(preset);
  }

  function displayName(val) {
    return DISPLAY_RENAME[val] || val;
  }

  function parsePreset(presetStr) {
    const parts = presetStr.split(",");
    return {
      physics: parts[0] || "",
      renderer: displayName(parts[1] || ""),
      datatype: parts[2] || "",
    };
  }

  function formatNumber(v) {
    if (v == null || v === "") return "—";
    if (typeof v !== "number") return String(v);
    if (Math.abs(v) >= 1000) return v.toLocaleString("en-US", { maximumFractionDigits: 1 });
    if (Math.abs(v) >= 1) return v.toFixed(2);
    return v.toFixed(4);
  }

  function isHiddenWorkflow(workflow) {
    if (!workflow) return true;
    return HIDDEN_WORKFLOWS.some((w) => workflow.includes(w));
  }

  function getTasks(data) {
    if (!data || !data.runs.length) return [];
    const taskSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        for (const b of entry.benchmarks) {
          if (!isHiddenWorkflow(b.workflow) && b.task) taskSet.add(b.task);
        }
      }
    }
    return [...taskSet].sort();
  }

  function getWorkflows(data, task, env, resolution) {
    if (!data || !data.runs.length) return [];
    const wfSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        for (const b of entry.benchmarks) {
          if (isHiddenWorkflow(b.workflow)) continue;
          if (task && b.task !== task) continue;
          if (env && String(b.num_envs) !== String(env)) continue;
          if (resolution && String(b.resolution) !== String(resolution)) continue;
          wfSet.add(b.workflow);
        }
      }
    }
    return [...wfSet].sort();
  }

  function getEnvs(data, task) {
    if (!data || !data.runs.length) return [];
    const envSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        for (const b of entry.benchmarks) {
          if (!isHiddenWorkflow(b.workflow) && b.task === task && b.num_envs != null) {
            envSet.add(b.num_envs);
          }
        }
      }
    }
    return [...envSet].sort((a, b) => a - b);
  }

  function getResolutions(data, task, numEnvs) {
    if (!data || !data.runs.length) return [];
    const resSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        for (const b of entry.benchmarks) {
          if (isHiddenWorkflow(b.workflow)) continue;
          if (task && b.task !== task) continue;
          if (numEnvs && String(b.num_envs) !== String(numEnvs)) continue;
          if (b.resolution != null) resSet.add(b.resolution);
        }
      }
    }
    const arr = [...resSet];
    return arr.sort((a, b) => {
      if (a === "default") return -1;
      if (b === "default") return 1;
      return Number(a) - Number(b);
    });
  }

  function getRuntimeMetrics(data, workflow, task, env, resolution) {
    const metricSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        for (const b of entry.benchmarks) {
          if (b.workflow !== workflow) continue;
          if (task && b.task !== task) continue;
          if (env && String(b.num_envs) !== String(env)) continue;
          if (resolution && String(b.resolution) !== String(resolution)) continue;
          for (const section of [b.runtime, b.train]) {
            if (!section) continue;
            for (const k of Object.keys(section)) {
              metricSet.add(k);
            }
          }
        }
      }
    }
    return [...metricSet].sort();
  }

  /* ─── GPU Selector ─── */

  function populateGpuSelect(manifest) {
    const sel = $("#gpuSelectGlobal");
    sel.innerHTML = "";
    const urlGpu = state.currentGpu;
    let adaIdx = -1;
    let urlGpuFound = false;
    for (let i = 0; i < manifest.datasets.length; i++) {
      const ds = manifest.datasets[i];
      const opt = document.createElement("option");
      opt.value = ds.gpu_type;
      opt.textContent = ds.gpu_display_name;
      sel.appendChild(opt);
      if (ds.gpu_type === urlGpu) urlGpuFound = true;
      if (ds.gpu_display_name.toLowerCase().includes("ada") ||
          ds.gpu_type.toLowerCase().includes("ada")) {
        adaIdx = i;
      }
    }
    if (urlGpuFound) {
      sel.value = urlGpu;
    } else if (adaIdx >= 0) {
      sel.selectedIndex = adaIdx;
    }
    state.currentGpu = sel.value;
  }

  /* ─── Tab Switching ─── */

  function switchTab(tab) {
    state.currentTab = tab;
    $$(".nav-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    $$(".tab-panel").forEach((p) => p.classList.remove("active"));
    const panelIds = { comparison: "comparisonPanel", history: "historyPanel", scaling: "scalingPanel", info: "infoPanel" };
    const panelId = panelIds[tab] || "comparisonPanel";
    $(`#${panelId}`).classList.add("active");
    renderCurrentTab();
  }

  function renderCurrentTab() {
    if (state.currentTab === "comparison") renderComparison();
    else if (state.currentTab === "history") renderHistory();
    else if (state.currentTab === "scaling") renderScaling();
    else if (state.currentTab === "info") renderInfo();
    syncUrlState();
  }

  /* ─── Env Scaling Tab ─── */

  const scalingCharts = [];

  function renderScaling() {
    const data = getCurrentData();
    if (!data || !data.runs.length) return;

    const runSel = $("#runSelectScaling");
    runSel.innerHTML = "";
    const runs = data.runs;
    for (let i = runs.length - 1; i >= 0; i--) {
      const r = runs[i];
      const label = i === runs.length - 1
        ? `${r.commit_sha} · ${r.commit_date} (latest)`
        : `${r.commit_sha} · ${r.commit_date}`;
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = label;
      runSel.appendChild(opt);
    }
    if (state.scalingRunIndex >= 0 && runSel.querySelector(`option[value="${state.scalingRunIndex}"]`)) {
      runSel.value = state.scalingRunIndex;
    } else {
      state.scalingRunIndex = runs.length - 1;
      runSel.value = state.scalingRunIndex;
    }

    renderVersionBar(runs[state.scalingRunIndex], "#scalingVersionBar");

    const scalingResSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        for (const b of entry.benchmarks) {
          if (!isHiddenWorkflow(b.workflow) && b.num_envs && ENV_SIZES.includes(b.num_envs) && b.resolution != null) {
            scalingResSet.add(b.resolution);
          }
        }
      }
    }
    const scalingResolutions = [...scalingResSet].sort((a, b) => {
      if (a === "default") return -1;
      if (b === "default") return 1;
      return Number(a) - Number(b);
    });
    const resSel = $("#resSelectScaling");
    resSel.innerHTML = "";
    for (const r of scalingResolutions) {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = String(r);
      resSel.appendChild(opt);
    }
    if (state.scalingResolution && resSel.querySelector(`option[value="${state.scalingResolution}"]`)) {
      resSel.value = state.scalingResolution;
    } else {
      state.scalingResolution = resSel.value;
    }

    const envFilterBtn = $("#scalingEnvFilterBtn");
    const envCheckboxes = $("#scalingEnvCheckboxes");
    envCheckboxes.innerHTML = "";
    const ef = state.scalingEnvFilter;
    envFilterBtn.textContent = ef.size === ENV_SIZES.length
      ? "Env Sizes (all) \u25BC"
      : `Env Sizes (${ef.size}) \u25BC`;
    for (const envVal of ENV_SIZES) {
      const label = document.createElement("label");
      label.className = "datatype-checkbox-label";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = ef.has(String(envVal));
      input.addEventListener("change", () => {
        if (input.checked) ef.add(String(envVal));
        else ef.delete(String(envVal));
        renderScaling();
        syncUrlState();
      });
      label.appendChild(input);
      label.appendChild(document.createTextNode(` ${envVal.toLocaleString()}`));
      envCheckboxes.appendChild(label);
    }

    $("#scalingLinearToggle").checked = state.scalingLinearX;

    const activeEnvSizes = ENV_SIZES.filter((e) => ef.has(String(e)));

    for (const c of scalingCharts) c.destroy();
    scalingCharts.length = 0;

    const container = $("#scalingContent");
    container.innerHTML = "";

    const wfTaskMap = {};
    const presetValues = {};

    const selectedIdx = state.scalingRunIndex;
    for (let ri = selectedIdx; ri >= 0; ri--) {
      const run = data.runs[ri];
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        for (const b of entry.benchmarks) {
          if (isHiddenWorkflow(b.workflow)) continue;
          if (state.scalingResolution && String(b.resolution) !== state.scalingResolution) continue;
          const rawTask = b.raw_task || b.task;
          const numEnvs = b.num_envs;
          if (!numEnvs || !activeEnvSizes.includes(numEnvs)) continue;

          const wfKey = `${b.workflow}||${rawTask}`;
          if (!wfTaskMap[wfKey]) wfTaskMap[wfKey] = { workflow: b.workflow, rawTask };

          const repMetric = getRepFpsMetric(b.workflow);
          const val = b.runtime?.[repMetric] ?? b.train?.[repMetric];
          if (val == null) continue;

          const pp = parsePreset(entry.preset);
          const presetLabel = `${pp.physics} / ${pp.renderer} / ${pp.datatype}`;
          const fullKey = `${wfKey}||${presetLabel}||${numEnvs}`;
          if (!presetValues[fullKey]) {
            presetValues[fullKey] = { wfKey, presetLabel, numEnvs, val };
          }
        }
      }
    }

    const wfTaskKeys = Object.keys(wfTaskMap).sort();
    if (wfTaskKeys.length === 0) {
      container.innerHTML = '<p style="color:var(--text-secondary);padding:20px;">No scaling data available.</p>';
      return;
    }

    for (const wfKey of wfTaskKeys) {
      const { workflow, rawTask } = wfTaskMap[wfKey];
      const repMetric = getRepFpsMetric(workflow);

      const chartData = {};
      for (const fk of Object.keys(presetValues)) {
        const pv = presetValues[fk];
        if (pv.wfKey !== wfKey) continue;
        if (!chartData[pv.presetLabel]) chartData[pv.presetLabel] = {};
        chartData[pv.presetLabel][pv.numEnvs] = pv.val;
      }

      const presetLabels = Object.keys(chartData)
        .filter((pl) => Object.keys(chartData[pl]).length >= 2)
        .sort();
      if (presetLabels.length === 0) continue;

      const section = document.createElement("div");
      section.className = "card scaling-chart-card";
      const wfShort = workflow.replace("benchmark_", "").replace("_train", " (train)");
      const title = document.createElement("div");
      title.className = "scaling-chart-title";
      title.textContent = `${rawTask} — ${wfShort}`;
      section.appendChild(title);
      const metricLabel = document.createElement("div");
      metricLabel.className = "scaling-chart-metric";
      metricLabel.textContent = repMetric;
      section.appendChild(metricLabel);
      const canvasWrap = document.createElement("div");
      canvasWrap.className = "scaling-canvas-wrap";
      const canvas = document.createElement("canvas");
      canvasWrap.appendChild(canvas);
      section.appendChild(canvasWrap);
      container.appendChild(section);

      const useLinear = state.scalingLinearX;
      let chartConfig;

      if (useLinear) {
        const datasets = presetLabels.map((preset, idx) => {
          const points = activeEnvSizes
            .filter((e) => chartData[preset]?.[e] != null)
            .map((e) => ({ x: e, y: chartData[preset][e] }));
          const color = PRESET_COLORS[idx % PRESET_COLORS.length];
          return {
            label: preset,
            data: points,
            borderColor: color,
            backgroundColor: color + "40",
            borderWidth: 2.5,
            pointRadius: 6,
            pointHoverRadius: 10,
            tension: 0.3,
          };
        });
        chartConfig = {
          type: "line",
          data: { datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "nearest", intersect: true },
            plugins: {
              legend: { position: "right", labels: { color: "#8b949e", font: { size: 10 }, boxWidth: 12, padding: 8 } },
              tooltip: {
                backgroundColor: "#1c2128", titleColor: "#e6edf3", bodyColor: "#e6edf3", borderColor: "#30363d", borderWidth: 1,
                callbacks: {
                  title: (items) => `${items[0].parsed.x.toLocaleString()} envs`,
                  label: (ctx) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y)}`,
                },
              },
            },
            scales: {
              x: {
                type: "linear",
                title: { display: true, text: "Number of Environments", color: "#8b949e", font: { size: 11 } },
                afterBuildTicks: (axis) => { axis.ticks = activeEnvSizes.map((v) => ({ value: v })); },
                ticks: { color: "#8b949e", font: { size: 10 }, callback: (v) => v >= 1000 ? `${(v/1024).toFixed(0)}K` : v },
                grid: { color: "rgba(48,54,61,0.5)" },
                min: activeEnvSizes[0],
                max: activeEnvSizes[activeEnvSizes.length - 1],
              },
              y: {
                title: { display: true, text: "FPS", color: "#8b949e", font: { size: 11 } },
                ticks: { color: "#8b949e", font: { size: 11 } },
                grid: { color: "rgba(48,54,61,0.5)" },
              },
            },
          },
        };
      } else {
        const labels = activeEnvSizes.map((e) => e.toLocaleString());
        const datasets = presetLabels.map((preset, idx) => {
          const vals = activeEnvSizes.map((e) => chartData[preset]?.[e] ?? null);
          const color = PRESET_COLORS[idx % PRESET_COLORS.length];
          return {
            label: preset,
            data: vals,
            borderColor: color,
            backgroundColor: color + "40",
            borderWidth: 2.5,
            pointRadius: 6,
            pointHoverRadius: 10,
            tension: 0.3,
            spanGaps: true,
          };
        });
        chartConfig = {
          type: "line",
          data: { labels, datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "nearest", intersect: true },
            plugins: {
              legend: { position: "right", labels: { color: "#8b949e", font: { size: 10 }, boxWidth: 12, padding: 8 } },
              tooltip: {
                backgroundColor: "#1c2128", titleColor: "#e6edf3", bodyColor: "#e6edf3", borderColor: "#30363d", borderWidth: 1,
                callbacks: { label: (ctx) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y)}` },
              },
            },
            scales: {
              x: {
                title: { display: true, text: "Number of Environments", color: "#8b949e", font: { size: 11 } },
                ticks: { color: "#8b949e", font: { size: 10 } },
                grid: { color: "rgba(48,54,61,0.5)" },
              },
              y: {
                title: { display: true, text: "FPS", color: "#8b949e", font: { size: 11 } },
                ticks: { color: "#8b949e", font: { size: 11 } },
                grid: { color: "rgba(48,54,61,0.5)" },
              },
            },
          },
        };
      }

      const chart = new Chart(canvas, chartConfig);
      scalingCharts.push(chart);
    }
  }

  function renderInfo() {
    const container = $("#infoBenchmarkEnv");
    container.innerHTML = "";
    const data = getCurrentData();
    const ds = state.manifest?.datasets?.find((d) => d.gpu_type === state.currentGpu);
    const gpuName = ds?.gpu_display_name || state.currentGpu || "—";

    const run = data?.runs?.length ? data.runs[data.runs.length - 1] : null;
    const ei = run?.env_info || {};
    const items = [
      { label: "GPU", value: gpuName },
      { label: "CPU", value: ei.cpu_name || "—" },
      { label: "Hostname", value: run?.hostname || "—" },
      { label: "OS", value: run?.machine_os || "—" },
      { label: "CPU cores", value: run?.machine_cpu_cores || "—" },
      { label: "GPU Memory", value: ei.gpu_total_memory_gb ? `${ei.gpu_total_memory_gb} GB` : "—" },
      { label: "RAM", value: ei.total_ram_gb ? `${ei.total_ram_gb} GB` : "—" },
      { label: "CUDA", value: ei.cuda_version || "—" },
    ];
    for (const item of items) {
      const div = document.createElement("div");
      div.className = "info-env-item";
      div.innerHTML = `<span class="label">${item.label}</span><span class="value" title="${item.value}">${item.value}</span>`;
      container.appendChild(div);
    }
  }

  /* ─── Comparison Tab ─── */

  function populateCompControls(data) {
    const runSel = $("#runSelectComp");
    const savedIndex = state.compRunIndex;
    runSel.innerHTML = "";
    const runs = data.runs;
    for (let i = runs.length - 1; i >= 0; i--) {
      const r = runs[i];
      const label = i === runs.length - 1
        ? `${r.commit_sha} · ${r.commit_date} (latest)`
        : `${r.commit_sha} · ${r.commit_date}`;
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = label;
      runSel.appendChild(opt);
    }
    if (compControlsInitialized && runSel.querySelector(`option[value="${savedIndex}"]`)) {
      state.compRunIndex = savedIndex;
    } else {
      state.compRunIndex = runs.length - 1;
      compControlsInitialized = true;
    }
    runSel.value = state.compRunIndex;

    const taskSel = $("#taskSelectComp");
    taskSel.innerHTML = "";
    for (const t of getTasks(data)) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      taskSel.appendChild(opt);
    }
    if (state.compTask && taskSel.querySelector(`option[value="${state.compTask}"]`)) {
      taskSel.value = state.compTask;
    } else {
      state.compTask = taskSel.value;
    }

    const envSel = $("#envSelectComp");
    envSel.innerHTML = "";
    for (const e of getEnvs(data, state.compTask)) {
      const opt = document.createElement("option");
      opt.value = e;
      opt.textContent = String(e);
      envSel.appendChild(opt);
    }
    if (state.compEnv && envSel.querySelector(`option[value="${state.compEnv}"]`)) {
      envSel.value = state.compEnv;
    } else {
      state.compEnv = envSel.value;
    }

    const resSel = $("#resSelectComp");
    resSel.innerHTML = "";
    for (const r of getResolutions(data, state.compTask, state.compEnv)) {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = String(r);
      resSel.appendChild(opt);
    }
    if (state.compResolution && resSel.querySelector(`option[value="${state.compResolution}"]`)) {
      resSel.value = state.compResolution;
    } else {
      state.compResolution = resSel.value;
    }

    const wfSel = $("#workflowSelectComp");
    wfSel.innerHTML = "";
    for (const wf of getWorkflows(data, state.compTask, state.compEnv, state.compResolution)) {
      const opt = document.createElement("option");
      opt.value = wf;
      opt.textContent = wf.replace("benchmark_", "").replace("_train", " (train)");
      wfSel.appendChild(opt);
    }
    if (wfSel.querySelector(`option[value="${state.compWorkflow}"]`)) {
      wfSel.value = state.compWorkflow;
    } else {
      state.compWorkflow = wfSel.value;
    }

  }

  function renderComparison() {
    const data = getCurrentData();
    if (!data) return;

    populateCompControls(data);
    const run = data.runs[state.compRunIndex];
    if (!run) return;

    renderVersionBar(run, "#compVersionBar");

    const workflow = state.compWorkflow;
    const task = state.compTask;
    const dims = getRunPresetDims(run);
    if (state.compFilterRunIndex !== state.compRunIndex && dims.physics.length > 0) {
      if (state.compFilterFromUrl) {
        state.compFilterFromUrl = false;
      } else {
        state.compPhysicsFilter = new Set(dims.physics);
        state.compRendererFilter = new Set(dims.renderers);
        state.compDatatypeFilter = new Set(dims.datatypes);
      }
      state.compFilterRunIndex = state.compRunIndex;
    }
    populatePresetFilterUI("physics", dims.physics, state.compPhysicsFilter, "#physicsFilterBtn", "#physicsCheckboxes");
    populatePresetFilterUI("renderer", dims.renderers, state.compRendererFilter, "#rendererFilterBtn", "#rendererCheckboxes");
    populatePresetFilterUI("datatype", dims.datatypes, state.compDatatypeFilter, "#datatypeFilterBtn", "#datatypeCheckboxes");

    const container = $("#comparisonContent");
    container.innerHTML = "";

    const warnings = detectPresetMismatches(run);
    if (warnings.length > 0) {
      const banner = document.createElement("div");
      banner.className = "warning-banner";
      banner.innerHTML = warnings
        .map((w) => `<div class="warning-line">\u26A0 ${w}</div>`)
        .join("");
      container.appendChild(banner);
    }

    const presets = [];
    const metricMap = {};
    const presetNumEnvs = {};
    const presetTask = {};
    const presetRawTask = {};
    const presetRawPresets = {};
    const presetNumFrames = {};
    const presetMaxIter = {};
    const pf = state.compPhysicsFilter;
    const rf = state.compRendererFilter;
    const df = state.compDatatypeFilter;

    for (const entry of run.entries) {
      if (isHiddenPreset(entry.preset)) continue;
      const pp = parsePreset(entry.preset);
      if (pf.size === 0 || !pf.has(pp.physics)) continue;
      if (rf.size === 0 || !rf.has(pp.renderer)) continue;
      if (df.size === 0 || !df.has(pp.datatype)) continue;
      for (const b of entry.benchmarks) {
        if (b.workflow !== workflow) continue;
        if (task && b.task !== task) continue;
        if (state.compEnv && String(b.num_envs) !== state.compEnv) continue;
        if (state.compResolution && String(b.resolution) !== state.compResolution) continue;
        const preset = entry.preset;
        if (!presets.includes(preset)) presets.push(preset);
        if (b.num_envs != null) presetNumEnvs[preset] = b.num_envs;
        if (b.num_frames != null) presetNumFrames[preset] = b.num_frames;
        if (b.max_iterations != null) presetMaxIter[preset] = b.max_iterations;
        if (b.task) presetTask[preset] = b.task;
        if (b.raw_task) presetRawTask[preset] = b.raw_task;
        if (b.raw_presets) presetRawPresets[preset] = b.raw_presets;
        for (const section of [b.runtime, b.train]) {
          if (!section) continue;
          for (const [k, v] of Object.entries(section)) {
            if (typeof v !== "number") continue;
            if (!metricMap[k]) metricMap[k] = {};
            metricMap[k][preset] = v;
          }
        }
      }
    }

    if (presets.length === 0) {
      const allEmpty = pf.size === 0 || rf.size === 0 || df.size === 0;
      const msg = allEmpty
        ? "Select at least one option in each filter above."
        : "No data for this workflow in the selected run.";
      container.innerHTML = `<p style="color:var(--text-secondary);padding:20px;">${msg}</p>`;
      return;
    }

    const repMetric = getRepFpsMetric(workflow);
    const rankCard = buildFpsRankCard(repMetric, presets, metricMap, workflow, presetNumEnvs, presetTask, presetRawTask, presetRawPresets, presetNumFrames, presetMaxIter, run);
    if (rankCard) container.appendChild(rankCard);

    const previewSection = buildPreviewSection(run, workflow, task, pf, rf, df);
    if (previewSection) container.appendChild(previewSection);

    const fpsMetrics = getFpsMetrics(workflow);
    const trainMetrics = ["Max Rewards", "Max Episode Lengths"];
    const fpsList = fpsMetrics.filter((m) => metricMap[m]);
    const trainList = trainMetrics.filter((m) => metricMap[m]);
    const otherList = Object.keys(metricMap)
      .filter((m) => !fpsMetrics.includes(m) && !trainMetrics.includes(m))
      .sort();

    if (fpsList.length > 0) {
      container.appendChild(buildFullTable("FPS Metrics", fpsList, presets, metricMap, true));
    }
    if (trainList.length > 0) {
      container.appendChild(buildFullTable("Training Metrics", trainList, presets, metricMap, true));
    }
    if (otherList.length > 0) {
      container.appendChild(buildFullTable("Other Metrics", otherList, presets, metricMap, false));
    }
  }

  const RENDERER_MAPPING = {
    "newton_renderer": "newtonwarprenderer",
    "newton_sensors": "newtonwarprenderer",
    "isaacsim_rtx_renderer": "isaacrtxrenderer",
    "rtx": "rtxrenderer",
    "rasterizer": "rasterizer",
  };

  function rendererMatches(presetRenderer, actualRenderer) {
    const presetKey = presetRenderer.toLowerCase();
    const actualLow = actualRenderer.toLowerCase();
    const mapped = RENDERER_MAPPING[presetKey];
    if (mapped) return actualLow.includes(mapped);
    const presetBase = presetKey.replace(/_/g, "").replace("renderer", "");
    return actualLow.includes(presetBase);
  }

  function getRunPresetDims(run) {
    const physSet = new Set(), rendSet = new Set(), dtSet = new Set();
    for (const entry of run.entries) {
      if (isHiddenPreset(entry.preset)) continue;
      const p = parsePreset(entry.preset);
      if (p.physics) physSet.add(p.physics);
      if (p.renderer) rendSet.add(p.renderer);
      if (p.datatype) dtSet.add(p.datatype);
    }
    return { physics: [...physSet].sort(), renderers: [...rendSet].sort(), datatypes: [...dtSet].sort() };
  }

  function getFilterSetByDim(dim) {
    if (dim === "physics") return state.compPhysicsFilter;
    if (dim === "renderer") return state.compRendererFilter;
    return state.compDatatypeFilter;
  }

  function populatePresetFilterUI(dim, items, filterSet, btnSel, boxSel) {
    const btn = $(btnSel);
    const box = $(boxSel);
    box.innerHTML = "";
    const labels = { physics: "Physics", renderer: "Renderer", datatype: "Data types" };
    const displayLabel = labels[dim] || dim;

    if (items.length === 0) {
      btn.textContent = `${displayLabel} (no data)`;
      return;
    }
    btn.textContent = filterSet.size === items.length
      ? `${displayLabel} (all)`
      : `${displayLabel} (${filterSet.size} selected)`;

    for (const val of items) {
      const label = document.createElement("label");
      label.className = "datatype-checkbox-label";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = filterSet.has(val);
      input.addEventListener("change", () => {
        if (input.checked) filterSet.add(val);
        else filterSet.delete(val);
        populatePresetFilterUI(dim, items, filterSet, btnSel, boxSel);
        renderComparison();
      });
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + val));
      box.appendChild(label);
    }
  }

  function detectPresetMismatches(run) {
    const warnings = [];
    for (const entry of run.entries) {
      if (!entry.preset || isHiddenPreset(entry.preset)) continue;
      const p = parsePreset(entry.preset);
      const actualPhys = (entry.actual_physics || "").toLowerCase();
      const actualRend = entry.actual_renderer || "";
      if (!actualPhys && !actualRend) continue;

      const presetPhys = p.physics.toLowerCase();

      if (actualPhys && presetPhys && actualPhys !== presetPhys) {
        warnings.push(
          `Preset <strong>${entry.preset}</strong> configured physics as <strong>${p.physics}</strong>, but <strong>${entry.actual_physics}</strong> was actually used.`
        );
      }
      if (actualRend && p.renderer && !rendererMatches(p.renderer, actualRend)) {
        warnings.push(
          `Preset <strong>${entry.preset}</strong> configured renderer as <strong>${p.renderer}</strong>, but <strong>${actualRend}</strong> was actually used.`
        );
      }
    }
    return warnings;
  }

  function showToast(msg) {
    let container = $("#toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = msg;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function buildShellCmd(workflow, rawTask, numEnvs, rawPreset, numFrames, maxIterations) {
    let script;
    if (workflow.includes("rlgames")) script = "scripts/benchmarks/benchmark_rlgames.py";
    else if (workflow.includes("rsl_rl")) script = "scripts/benchmarks/benchmark_rsl_rl.py";
    else script = "scripts/benchmarks/benchmark_non_rl.py";
    const envs = numEnvs || 512;
    let cmd = `./isaaclab.sh -p ${script} --task=${rawTask} --headless --enable_cameras --num_envs=${envs}`;
    if (workflow.includes("rlgames") && maxIterations) {
      cmd += ` --max_iterations=${maxIterations}`;
    } else if (workflow.includes("rsl_rl") && maxIterations) {
      cmd += ` --max_iterations=${maxIterations}`;
    } else if (numFrames) {
      cmd += ` --num_frames=${numFrames}`;
    }
    if (rawPreset && rawPreset !== "default") cmd += ` presets=${rawPreset}`;
    return cmd;
  }

  function buildFpsRankCard(repMetric, presets, metricMap, workflow, presetNumEnvs, presetTask, presetRawTask, presetRawPresets, presetNumFrames, presetMaxIter, run) {
    const values = metricMap[repMetric];
    if (!values) return null;

    const vramMetric = metricMap["GPU Memory Used"] ? "GPU Memory Used" : "GPU 0 Memory Used";
    const vramValues = metricMap[vramMetric] || {};
    const gpuTotalGb = run?.env_info?.gpu_total_memory_gb || 0;

    const ranked = presets
      .map((p) => ({ preset: p, value: values[p] }))
      .filter((x) => x.value != null && typeof x.value === "number")
      .sort((a, b) => b.value - a.value);

    if (ranked.length === 0) return null;

    const card = document.createElement("div");
    card.className = "card rank-card";
    const title = document.createElement("div");
    title.className = "rank-card-title";
    title.textContent = "Representative FPS ranking (this run)";
    card.appendChild(title);
    const sub = document.createElement("div");
    sub.className = "rank-card-metric";
    sub.textContent = repMetric;
    card.appendChild(sub);
    const list = document.createElement("ol");
    list.className = "rank-list";
    ranked.forEach((item) => {
      const li = document.createElement("li");
      const p = parsePreset(item.preset);
      const label = `${p.physics} / ${p.renderer} / ${p.datatype}`;
      const numEnvs = presetNumEnvs[item.preset];
      const rawTask = presetRawTask[item.preset] || presetTask[item.preset] || "";
      const rawPreset = presetRawPresets[item.preset] || item.preset;
      const nf = presetNumFrames[item.preset];
      const mi = presetMaxIter[item.preset];
      const cmd = buildShellCmd(workflow, rawTask, numEnvs, rawPreset, nf, mi);
      const vram = vramValues[item.preset];
      let vramStr = "";
      if (vram != null) {
        const pct = gpuTotalGb ? ((vram / gpuTotalGb) * 100).toFixed(1) : null;
        vramStr = pct
          ? ` <span class="rank-vram">${formatNumber(vram)} GB / ${pct}% VRAM</span>`
          : ` <span class="rank-vram">${formatNumber(vram)} GB VRAM</span>`;
      }
      li.innerHTML = `<button class="copy-cmd-btn" title="Copy run command">&#x1F4CB;</button><span class="rank-label">${label}${numEnvs ? ` <span class="rank-envs">(${numEnvs} envs)</span>` : ""}${vramStr}</span><span class="rank-value">${formatNumber(item.value)}</span>`;
      li.querySelector(".copy-cmd-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        const btn = e.currentTarget;
        function onSuccess() {
          btn.textContent = "\u2705";
          setTimeout(() => { btn.innerHTML = "&#x1F4CB;"; }, 1500);
          showToast("Copied: " + cmd);
        }
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(cmd).then(onSuccess);
        } else {
          const ta = document.createElement("textarea");
          ta.value = cmd;
          ta.style.cssText = "position:fixed;left:-9999px";
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
          onSuccess();
        }
      });
      list.appendChild(li);
    });
    card.appendChild(list);
    return card;
  }

  function buildPreviewSection(run, workflow, task, pf, rf, df) {
    const items = [];
    for (const entry of run.entries) {
      if (isHiddenPreset(entry.preset)) continue;
      const pp = parsePreset(entry.preset);
      if (pf.size === 0 || !pf.has(pp.physics)) continue;
      if (rf.size === 0 || !rf.has(pp.renderer)) continue;
      if (df.size === 0 || !df.has(pp.datatype)) continue;
      for (const b of entry.benchmarks) {
        if (b.workflow !== workflow) continue;
        if (task && b.task !== task) continue;
        if (state.compEnv && String(b.num_envs) !== state.compEnv) continue;
        if (state.compResolution && String(b.resolution) !== state.compResolution) continue;
        if (b.preview) {
          items.push({
            label: `${pp.physics} / ${pp.renderer} / ${pp.datatype}`,
            src: `data/${b.preview}`,
          });
        }
      }
    }
    if (items.length === 0) return null;

    const section = document.createElement("div");
    section.className = "heatmap-section";
    const heading = document.createElement("div");
    heading.className = "heatmap-section-title";
    heading.textContent = "Preview";
    section.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "preview-grid";
    for (const item of items) {
      const card = document.createElement("div");
      card.className = "preview-card";
      const lbl = document.createElement("div");
      lbl.className = "preview-label";
      lbl.textContent = item.label;
      card.appendChild(lbl);
      const img = document.createElement("img");
      img.className = "preview-thumb";
      img.src = item.src;
      img.alt = item.label;
      img.loading = "lazy";
      img.addEventListener("click", () => openLightbox(item.src, item.label));
      card.appendChild(img);
      grid.appendChild(card);
    }
    section.appendChild(grid);
    return section;
  }

  function openLightbox(src, label) {
    let overlay = $("#lightboxOverlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "lightboxOverlay";
      overlay.className = "lightbox-overlay";
      overlay.addEventListener("click", () => { overlay.classList.remove("show"); });
      overlay.innerHTML = '<div class="lightbox-content"><div class="lightbox-label" id="lightboxLabel"></div><img class="lightbox-img" id="lightboxImg"></div>';
      document.body.appendChild(overlay);
      overlay.querySelector(".lightbox-content").addEventListener("click", (e) => e.stopPropagation());
    }
    $("#lightboxImg").src = src;
    $("#lightboxLabel").textContent = label;
    overlay.classList.add("show");
  }

  function buildFullTable(title, metrics, presets, metricMap, isFps) {
    const section = document.createElement("div");
    section.className = "heatmap-section";

    const heading = document.createElement("div");
    heading.className = "heatmap-section-title";
    heading.textContent = title;
    section.appendChild(heading);

    const wrapper = document.createElement("div");
    wrapper.className = "heatmap-wrapper";

    const table = document.createElement("table");
    table.className = "heatmap-table";

    let currentOrder = presets.slice();

    const activeSortMetric = metrics.find((m) => state.compSorts[m] != null);
    if (activeSortMetric) {
      const desc = state.compSorts[activeSortMetric];
      const vals = metricMap[activeSortMetric] || {};
      currentOrder = presets.slice().sort((a, b) => {
        const va = vals[a] ?? (desc ? -Infinity : Infinity);
        const vb = vals[b] ?? (desc ? -Infinity : Infinity);
        return desc ? vb - va : va - vb;
      });
    }

    function applySort(metric) {
      const prev = state.compSorts[metric];
      for (const m of metrics) delete state.compSorts[m];

      if (prev == null) {
        state.compSorts[metric] = true;
      } else if (prev === true) {
        state.compSorts[metric] = false;
      } else {
        currentOrder = presets.slice();
        renderTable();
        syncUrlState();
        return;
      }

      const desc = state.compSorts[metric];
      const vals = metricMap[metric] || {};
      currentOrder = presets.slice().sort((a, b) => {
        const va = vals[a] ?? (desc ? -Infinity : Infinity);
        const vb = vals[b] ?? (desc ? -Infinity : Infinity);
        return desc ? vb - va : va - vb;
      });
      renderTable();
      syncUrlState();
    }

    function renderTable() {
      table.innerHTML = "";

      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");
      const cornerTh = document.createElement("th");
      cornerTh.innerHTML = 'Metric <span class="sort-hint">(click to sort)</span>';
      headerRow.appendChild(cornerTh);

      for (const preset of currentOrder) {
        const th = document.createElement("th");
        const p = parsePreset(preset);
        th.innerHTML = `<div class="preset-header-cell">
          <span class="preset-part physics">${p.physics}</span>
          <span class="preset-part renderer">${p.renderer}</span>
          <span class="preset-part datatype">${p.datatype}</span>
        </div>`;
        headerRow.appendChild(th);
      }
      thead.appendChild(headerRow);
      table.appendChild(thead);

      const tbody = document.createElement("tbody");
      for (const metric of metrics) {
        const tr = document.createElement("tr");
        const tdLabel = document.createElement("td");
        tdLabel.className = "metric-label-sortable";
        const isActive = state.compSorts[metric] != null;
        if (isActive) tdLabel.classList.add("sort-active");
        const arrow = isActive ? (state.compSorts[metric] ? " \u25BC" : " \u25B2") : "";
        tdLabel.textContent = metric + arrow;
        tdLabel.addEventListener("click", () => applySort(metric));
        tr.appendChild(tdLabel);

        const values = currentOrder.map((p) => metricMap[metric]?.[p]);
        const numericVals = values.filter((v) => v != null && typeof v === "number");
        const maxVal = numericVals.length ? Math.max(...numericVals) : null;
        const minVal = numericVals.length ? Math.min(...numericVals) : null;
        const isHigherBetter = isFps || metric.toLowerCase().includes("fps");

        for (let i = 0; i < currentOrder.length; i++) {
          const td = document.createElement("td");
          const v = values[i];
          if (v == null) {
            td.textContent = "—";
            td.className = "cell-na";
          } else {
            td.textContent = formatNumber(v);
            if (numericVals.length > 1 && maxVal !== minVal) {
              if (isHigherBetter) {
                if (v === maxVal) td.className = "cell-best";
                if (v === minVal) td.className = "cell-worst";
              } else {
                if (v === minVal) td.className = "cell-best";
                if (v === maxVal) td.className = "cell-worst";
              }
              const range = maxVal - minVal;
              if (range > 0) {
                const ratio = isHigherBetter
                  ? (v - minVal) / range
                  : (maxVal - v) / range;
                const r = Math.round(248 - ratio * 200);
                const g = Math.round(80 + ratio * 120);
                const b2 = Math.round(80 - ratio * 30);
                td.style.backgroundColor = `rgba(${r},${g},${b2},0.12)`;
              }
            }
          }
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
    }

    renderTable();
    wrapper.appendChild(table);
    section.appendChild(wrapper);
    return section;
  }

  /* ─── Version Bar ─── */

  function renderVersionBar(run, selector) {
    const bar = $(selector);
    bar.innerHTML = "";
    const ei = run.env_info || {};
    const items = [
      { label: "Commit", value: run.commit_sha },
      { label: "Commit Date", value: run.commit_date },
      { label: "Isaac Sim", value: run.isaac_sim_version || "—" },
      { label: "Isaac Lab SHA", value: (run.isaaclab_version_sha || "").substring(0, 12) },
      { label: "Warp", value: ei.warp_version || "—" },
      { label: "Newton", value: ei.newton_version || "—" },
      { label: "OVrtx", value: ei.ovrtx_version || "—" },
      { label: "PyTorch", value: ei.torch_version || "—" },
      { label: "Driver", value: run.driver || "—" },
    ];
    for (const item of items) {
      const div = document.createElement("div");
      div.className = "version-item";
      div.innerHTML = `<span class="version-label">${item.label}</span><span class="version-value" title="${item.value}">${item.value}</span>`;
      bar.appendChild(div);
    }
  }

  /* ─── History Tab ─── */

  function populateHistControls(data) {
    const taskSel = $("#taskSelectHist");
    taskSel.innerHTML = "";
    for (const t of getTasks(data)) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      taskSel.appendChild(opt);
    }
    if (state.histTask && taskSel.querySelector(`option[value="${state.histTask}"]`)) {
      taskSel.value = state.histTask;
    } else {
      state.histTask = taskSel.value;
    }

    const envSelH = $("#envSelectHist");
    envSelH.innerHTML = "";
    for (const e of getEnvs(data, state.histTask)) {
      const opt = document.createElement("option");
      opt.value = e;
      opt.textContent = String(e);
      envSelH.appendChild(opt);
    }
    if (state.histEnv && envSelH.querySelector(`option[value="${state.histEnv}"]`)) {
      envSelH.value = state.histEnv;
    } else {
      state.histEnv = envSelH.value;
    }

    const resSelH = $("#resSelectHist");
    resSelH.innerHTML = "";
    for (const r of getResolutions(data, state.histTask, state.histEnv)) {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = String(r);
      resSelH.appendChild(opt);
    }
    if (state.histResolution && resSelH.querySelector(`option[value="${state.histResolution}"]`)) {
      resSelH.value = state.histResolution;
    } else {
      state.histResolution = resSelH.value;
    }

    const wfSel = $("#workflowSelectHist");
    wfSel.innerHTML = "";
    for (const wf of getWorkflows(data, state.histTask, state.histEnv, state.histResolution)) {
      const opt = document.createElement("option");
      opt.value = wf;
      opt.textContent = wf.replace("benchmark_", "").replace("_train", " (train)");
      wfSel.appendChild(opt);
    }
    if (wfSel.querySelector(`option[value="${state.histWorkflow}"]`)) {
      wfSel.value = state.histWorkflow;
    } else {
      state.histWorkflow = wfSel.value;
    }

    populateHistMetrics(data);
  }

  function populateHistMetrics(data) {
    const metSel = $("#metricSelectHist");
    metSel.innerHTML = "";
    const metrics = getRuntimeMetrics(data, state.histWorkflow, state.histTask, state.histEnv, state.histResolution);

    const fpsMetrics = getFpsMetrics(state.histWorkflow);

    const fpsFirst = fpsMetrics.filter((m) => metrics.includes(m));
    const rest = metrics.filter((m) => !fpsMetrics.includes(m));
    const ordered = [...fpsFirst, ...rest];

    for (const m of ordered) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m;
      metSel.appendChild(opt);
    }

    if (state.histMetric && metSel.querySelector(`option[value="${state.histMetric}"]`)) {
      metSel.value = state.histMetric;
    } else {
      state.histMetric = metSel.value;
    }
  }

  function getHistPresetDims(data) {
    const physSet = new Set(), rendSet = new Set(), dtSet = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        const p = parsePreset(entry.preset);
        if (p.physics) physSet.add(p.physics);
        if (p.renderer) rendSet.add(p.renderer);
        if (p.datatype) dtSet.add(p.datatype);
      }
    }
    return { physics: [...physSet].sort(), renderers: [...rendSet].sort(), datatypes: [...dtSet].sort() };
  }

  function getHistFilterSet(dim) {
    if (dim === "physics") return state.histPhysicsFilter;
    if (dim === "renderer") return state.histRendererFilter;
    return state.histDatatypeFilter;
  }

  function populateHistPresetFilterUI(dim, items, filterSet, btnSel, boxSel) {
    const btn = $(btnSel);
    const box = $(boxSel);
    box.innerHTML = "";
    const labels = { physics: "Physics", renderer: "Renderer", datatype: "Data types" };
    const displayLabel = labels[dim] || dim;

    if (items.length === 0) {
      btn.textContent = `${displayLabel} (no data)`;
      return;
    }
    btn.textContent = filterSet.size === items.length
      ? `${displayLabel} (all)`
      : `${displayLabel} (${filterSet.size} selected)`;

    for (const val of items) {
      const label = document.createElement("label");
      label.className = "datatype-checkbox-label";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = filterSet.has(val);
      input.addEventListener("change", () => {
        if (input.checked) filterSet.add(val);
        else filterSet.delete(val);
        populateHistPresetFilterUI(dim, items, filterSet, btnSel, boxSel);
        renderHistChart(getCurrentData());
        syncUrlState();
      });
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + val));
      box.appendChild(label);
    }
  }

  function renderHistory() {
    const data = getCurrentData();
    if (!data) return;

    populateHistControls(data);

    const hdims = getHistPresetDims(data);
    if (!state.histFilterInited && hdims.physics.length > 0) {
      state.histPhysicsFilter = new Set(hdims.physics);
      state.histRendererFilter = new Set(hdims.renderers);
      state.histDatatypeFilter = new Set(hdims.datatypes);
      state.histFilterInited = true;
    }
    populateHistPresetFilterUI("physics", hdims.physics, state.histPhysicsFilter, "#physicsFilterBtnHist", "#physicsCheckboxesHist");
    populateHistPresetFilterUI("renderer", hdims.renderers, state.histRendererFilter, "#rendererFilterBtnHist", "#rendererCheckboxesHist");
    populateHistPresetFilterUI("datatype", hdims.datatypes, state.histDatatypeFilter, "#datatypeFilterBtnHist", "#datatypeCheckboxesHist");

    renderHistChart(data);
    if (state.histRunDetail >= 0 && state.histRunDetail < data.runs.length) {
      showHistRunDetail(data, state.histRunDetail);
    } else if (data.runs.length > 0) {
      showHistRunDetail(data, data.runs.length - 1);
    } else {
      $("#histRunDetail").style.display = "none";
    }

    renderAllTasksOverview(data);
    renderBenchmarkStatusGrid(data);
  }

  function renderHistChart(data) {
    const workflow = state.histWorkflow;
    const metric = state.histMetric;
    const task = state.histTask;

    if (!metric) {
      $("#histChartTitle").textContent = "Select a metric";
      $("#histRunCount").textContent = "";
      $("#histRangeSummary").textContent = "";
      $("#histRangeSummary").style.display = "none";
      return;
    }

    $("#histChartTitle").textContent = metric;

    const hpf = state.histPhysicsFilter;
    const hrf = state.histRendererFilter;
    const hdf = state.histDatatypeFilter;
    const presetsSeen = new Set();
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        const pp = parsePreset(entry.preset);
        if (hpf.size === 0 || !hpf.has(pp.physics)) continue;
        if (hrf.size === 0 || !hrf.has(pp.renderer)) continue;
        if (hdf.size === 0 || !hdf.has(pp.datatype)) continue;
        for (const b of entry.benchmarks) {
          if (b.workflow !== workflow) continue;
          if (task && b.task !== task) continue;
          if (state.histEnv && String(b.num_envs) !== state.histEnv) continue;
          if (state.histResolution && String(b.resolution) !== state.histResolution) continue;
          presetsSeen.add(entry.preset);
        }
      }
    }
    const presets = [...presetsSeen].sort();

    const labels = data.runs.map((r) => r.commit_sha);
    const datasets = presets.map((preset, idx) => {
      const values = data.runs.map((run) => {
        const entry = run.entries.find((e) => e.preset === preset);
        if (!entry) return null;
        const bench = entry.benchmarks.find((b) =>
          b.workflow === workflow && (!task || b.task === task) &&
          (!state.histEnv || String(b.num_envs) === state.histEnv) &&
          (!state.histResolution || String(b.resolution) === state.histResolution)
        );
        if (!bench) return null;
        return bench.runtime?.[metric] ?? bench.train?.[metric] ?? null;
      });

      const color = PRESET_COLORS[idx % PRESET_COLORS.length];
      const p = parsePreset(preset);

      return {
        label: `${p.physics} / ${p.renderer} / ${p.datatype}`,
        data: values,
        borderColor: color,
        backgroundColor: color + "40",
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 6,
        tension: 0.3,
        spanGaps: true,
      };
    });

    const hasAnyData = datasets.some((ds) => ds.data.some((v) => v != null));
    if (!hasAnyData) {
      $("#histChartTitle").textContent = `${metric} — No data`;
      $("#histRunCount").textContent = "";
      $("#histRangeSummary").textContent = "";
      $("#histRangeSummary").style.display = "none";
      if (state.histChart) { state.histChart.destroy(); state.histChart = null; }
      return;
    }

    $("#histRunCount").textContent = `${data.runs.length} commits · ${presets.length} presets`;

    const firstDate = data.runs[0]?.commit_date || "";
    const lastDate = data.runs[data.runs.length - 1]?.commit_date || "";
    const dateRange = firstDate && lastDate ? `${firstDate.split(" ")[0]} ~ ${lastDate.split(" ")[0]}` : "";
    $("#histRangeSummary").textContent = dateRange;
    $("#histRangeSummary").style.display = dateRange ? "inline-block" : "none";

    if (state.histChart) state.histChart.destroy();

    const yAxisLabel = metric.toLowerCase().includes("fps") ? "FPS" : metric;

    const selectedLinePlugin = {
      id: "selectedLine",
      afterDraw(chart) {
        if (state.histRunDetail < 0) return;
        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data[state.histRunDetail]) return;
        const x = meta.data[state.histRunDetail].x;
        const { top, bottom } = chart.chartArea;
        const ctx = chart.ctx;
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#76b900";
        ctx.setLineDash([6, 4]);
        ctx.stroke();
        ctx.restore();
      },
    };

    state.histChart = new Chart($("#histChart"), {
      type: "line",
      data: { labels, datasets },
      plugins: [selectedLinePlugin],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "nearest", intersect: true },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1c2128",
            titleColor: "#e6edf3",
            bodyColor: "#e6edf3",
            borderColor: "#30363d",
            borderWidth: 1,
            callbacks: {
              title: (items) => {
                const idx = items[0].dataIndex;
                const run = data.runs[idx];
                return `${run.commit_sha} · ${run.commit_date}`;
              },
              label: (ctx) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y)}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: "#8b949e", font: { size: 10, family: "monospace" } },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
          y: {
            title: { display: true, text: yAxisLabel, color: "#8b949e", font: { size: 11 } },
            ticks: { color: "#8b949e", font: { size: 11 } },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
        },
        onClick: (evt, elements) => {
          if (elements.length > 0) {
            const idx = elements[0].index;
            showHistRunDetail(data, idx);
            state.histChart.draw();
          }
        },
      },
    });
  }

  function showHistRunDetail(data, runIndex) {
    const run = data.runs[runIndex];
    if (!run) return;

    state.histRunDetail = runIndex;
    syncUrlState();

    const detail = $("#histRunDetail");
    detail.style.display = "block";
    $("#histCommitBadge").textContent = `${run.commit_sha} · ${run.commit_date}`;
    renderVersionBar(run, "#histVersionBar");

    const content = $("#histSummaryContent");
    content.innerHTML = "";

    const workflow = state.histWorkflow;
    const metric = state.histMetric;
    const task = state.histTask;

    for (const entry of run.entries) {
      if (isHiddenPreset(entry.preset)) continue;
      const bench = entry.benchmarks.find((b) =>
        b.workflow === workflow && (!task || b.task === task) &&
        (!state.histEnv || String(b.num_envs) === state.histEnv) &&
        (!state.histResolution || String(b.resolution) === state.histResolution)
      );
      if (!bench) continue;

      const val = bench.runtime?.[metric] ?? bench.train?.[metric];
      if (val == null) continue;

      const p = parsePreset(entry.preset);
      const div = document.createElement("div");
      div.className = "summary-metric";
      div.innerHTML = `
        <div class="label">${p.physics} / ${p.renderer} / ${p.datatype}</div>
        <div class="value">${formatNumber(val)}</div>
      `;
      content.appendChild(div);
    }
  }

  /* ─── All Tasks Overview ─── */

  const allTasksCharts = [];

  function renderAllTasksOverview(data) {
    const container = $("#allTasksOverview");
    container.innerHTML = "";
    for (const c of allTasksCharts) c.destroy();
    allTasksCharts.length = 0;

    if (!data || !data.runs.length) return;

    const heading = document.createElement("h2");
    heading.className = "all-tasks-heading";
    heading.textContent = "All Tasks Overview";
    container.appendChild(heading);

    const hpf = state.histPhysicsFilter;
    const hrf = state.histRendererFilter;
    const hdf = state.histDatatypeFilter;

    const wfTaskMap = {};
    for (const run of data.runs) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        const pp = parsePreset(entry.preset);
        if (hpf.size === 0 || !hpf.has(pp.physics)) continue;
        if (hrf.size === 0 || !hrf.has(pp.renderer)) continue;
        if (hdf.size === 0 || !hdf.has(pp.datatype)) continue;
        for (const b of entry.benchmarks) {
          if (isHiddenWorkflow(b.workflow)) continue;
          if (state.histEnv && String(b.num_envs) !== state.histEnv) continue;
          if (state.histResolution && String(b.resolution) !== state.histResolution) continue;
          if (!wfTaskMap[b.workflow]) wfTaskMap[b.workflow] = new Set();
          wfTaskMap[b.workflow].add(b.task);
        }
      }
    }

    const workflows = Object.keys(wfTaskMap).sort();
    for (const wf of workflows) {
      const wfSection = document.createElement("div");
      wfSection.className = "all-tasks-wf-section";
      const wfTitle = document.createElement("h3");
      wfTitle.className = "all-tasks-wf-title";
      wfTitle.textContent = wf.replace("benchmark_", "").replace("_train", " (train)");
      wfSection.appendChild(wfTitle);

      const tasks = [...wfTaskMap[wf]].sort();
      const repMetric = getRepFpsMetric(wf);

      const grid = document.createElement("div");
      grid.className = "all-tasks-grid";

      for (const task of tasks) {
        const card = document.createElement("div");
        card.className = "card all-tasks-chart-card";
        const title = document.createElement("div");
        title.className = "all-tasks-chart-title";
        title.textContent = task;
        card.appendChild(title);
        const sub = document.createElement("div");
        sub.className = "all-tasks-chart-metric";
        sub.textContent = repMetric;
        card.appendChild(sub);
        const canvasWrap = document.createElement("div");
        canvasWrap.className = "all-tasks-canvas-wrap";
        const canvas = document.createElement("canvas");
        canvasWrap.appendChild(canvas);
        card.appendChild(canvasWrap);
        grid.appendChild(card);

        const presetsSeen = new Set();
        for (const run of data.runs) {
          for (const entry of run.entries) {
            if (isHiddenPreset(entry.preset)) continue;
            const pp = parsePreset(entry.preset);
            if (hpf.size === 0 || !hpf.has(pp.physics)) continue;
            if (hrf.size === 0 || !hrf.has(pp.renderer)) continue;
            if (hdf.size === 0 || !hdf.has(pp.datatype)) continue;
            for (const b of entry.benchmarks) {
              if (b.workflow !== wf || b.task !== task) continue;
              if (state.histEnv && String(b.num_envs) !== state.histEnv) continue;
              if (state.histResolution && String(b.resolution) !== state.histResolution) continue;
              presetsSeen.add(entry.preset);
            }
          }
        }
        const presets = [...presetsSeen].sort();
        const labels = data.runs.map((r) => r.commit_sha);

        const datasets = presets.map((preset, idx) => {
          const values = data.runs.map((run) => {
            const entry = run.entries.find((e) => e.preset === preset);
            if (!entry) return null;
            const bench = entry.benchmarks.find((b) =>
              b.workflow === wf && b.task === task &&
              (!state.histEnv || String(b.num_envs) === state.histEnv) &&
              (!state.histResolution || String(b.resolution) === state.histResolution)
            );
            if (!bench) return null;
            return bench.runtime?.[repMetric] ?? bench.train?.[repMetric] ?? null;
          });
          const color = PRESET_COLORS[idx % PRESET_COLORS.length];
          const p = parsePreset(preset);
          return {
            label: `${p.physics} / ${p.renderer} / ${p.datatype}`,
            data: values,
            borderColor: color,
            backgroundColor: color + "40",
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 5,
            tension: 0.3,
            spanGaps: true,
          };
        });

        const hasData = datasets.some((ds) => ds.data.some((v) => v != null));
        if (!hasData) {
          const noData = document.createElement("div");
          noData.className = "all-tasks-no-data";
          noData.textContent = "No data";
          card.appendChild(noData);
          continue;
        }

        const chart = new Chart(canvas, {
          type: "line",
          data: { labels, datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "nearest", intersect: true },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: "#1c2128",
                titleColor: "#e6edf3",
                bodyColor: "#e6edf3",
                borderColor: "#30363d",
                borderWidth: 1,
                callbacks: {
                  title: (items) => {
                    const idx = items[0].dataIndex;
                    const run = data.runs[idx];
                    return `${run.commit_sha} · ${run.commit_date}`;
                  },
                  label: (ctx) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y)}`,
                },
              },
            },
            scales: {
              x: {
                display: false,
              },
              y: {
                ticks: { color: "#8b949e", font: { size: 10 } },
                grid: { color: "rgba(48,54,61,0.5)" },
              },
            },
          },
        });
        allTasksCharts.push(chart);
      }

      wfSection.appendChild(grid);
      container.appendChild(wfSection);
    }
  }

  /* ─── Benchmark Status Grid ─── */

  function renderBenchmarkStatusGrid(data) {
    const container = $("#benchmarkStatusGrid");
    container.innerHTML = "";
    if (!data || !data.runs.length) return;

    const recentRuns = data.runs.slice(-10).reverse();

    const allWfTasks = {};
    const presetJobMap = {};

    for (const run of recentRuns) {
      for (const entry of run.entries) {
        if (isHiddenPreset(entry.preset)) continue;
        const hasJob = !!entry.ci_job_id;
        for (const b of entry.benchmarks) {
          if (isHiddenWorkflow(b.workflow)) continue;
          if (state.histEnv && String(b.num_envs) !== state.histEnv) continue;
          if (state.histResolution && String(b.resolution) !== state.histResolution) continue;
          const col = `${b.workflow}|${b.task}`;
          allWfTasks[col] = { workflow: b.workflow, task: b.task };
        }
        const pKey = entry.preset;
        if (!presetJobMap[run.commit_sha]) presetJobMap[run.commit_sha] = {};
        if (!presetJobMap[run.commit_sha][pKey]) {
          presetJobMap[run.commit_sha][pKey] = { hasJob, benchKeys: new Set() };
        }
        for (const b of entry.benchmarks) {
          if (isHiddenWorkflow(b.workflow)) continue;
          if (state.histEnv && String(b.num_envs) !== state.histEnv) continue;
          if (state.histResolution && String(b.resolution) !== state.histResolution) continue;
          const col = `${b.workflow}|${b.task}`;
          presetJobMap[run.commit_sha][pKey].benchKeys.add(col);
        }
      }
    }

    const columns = Object.keys(allWfTasks).sort();
    if (columns.length === 0) return;

    const allPresets = new Set();
    for (const run of recentRuns) {
      for (const entry of run.entries) {
        if (!isHiddenPreset(entry.preset)) allPresets.add(entry.preset);
      }
    }
    const presets = [...allPresets].sort();

    const outer = document.createElement("div");
    outer.className = "status-outer collapsed";

    const heading = document.createElement("div");
    heading.className = "status-heading-toggle";
    heading.innerHTML = '<span class="status-toggle-arrow">\u25B6</span> Benchmark Status (last 10 commits)';
    heading.addEventListener("click", () => outer.classList.toggle("collapsed"));
    outer.appendChild(heading);

    const body = document.createElement("div");
    body.className = "status-body";

    const legend = document.createElement("div");
    legend.className = "status-legend";
    legend.innerHTML = '<span class="status-pass">\u2705 Pass</span> <span class="status-fail">\u274C Fail (job ran, no data)</span> <span class="status-not-run">\u2014 Not run</span>';
    body.appendChild(legend);

    for (const preset of presets) {
      const pp = parsePreset(preset);
      const section = document.createElement("div");
      section.className = "status-section";

      const title = document.createElement("div");
      title.className = "status-preset-title";
      title.textContent = `${pp.physics} / ${pp.renderer} / ${pp.datatype}`;
      section.appendChild(title);

      const wrapper = document.createElement("div");
      wrapper.className = "heatmap-wrapper";
      const table = document.createElement("table");
      table.className = "status-table";

      const thead = document.createElement("thead");
      const hRow = document.createElement("tr");
      const cornerTh = document.createElement("th");
      cornerTh.textContent = "Commit";
      hRow.appendChild(cornerTh);
      for (const col of columns) {
        const info = allWfTasks[col];
        const th = document.createElement("th");
        const wfShort = info.workflow.replace("benchmark_", "").replace("_train", "");
        th.innerHTML = `<div class="status-col-header"><span>${wfShort}</span><span class="status-task-name">${info.task}</span></div>`;
        hRow.appendChild(th);
      }
      thead.appendChild(hRow);
      table.appendChild(thead);

      const tbody = document.createElement("tbody");
      for (const run of recentRuns) {
        const tr = document.createElement("tr");
        const tdSha = document.createElement("td");
        tdSha.className = "status-sha";
        tdSha.textContent = run.commit_sha;
        tr.appendChild(tdSha);

        const runPreset = presetJobMap[run.commit_sha]?.[preset];
        const jobExists = !!runPreset?.hasJob;

        const pp = parsePreset(preset);
        const dtHasNum = /\d+$/.test(pp.datatype);

        for (const col of columns) {
          const td = document.createElement("td");
          td.className = "status-cell";
          const colTask = allWfTasks[col].task;
          const isDexsuite = colTask.toLowerCase().includes("dexsuite");
          const incompatible = (isDexsuite && !dtHasNum) || (!isDexsuite && dtHasNum);

          if (incompatible || !runPreset) {
            td.textContent = "—";
            td.classList.add("status-not-run");
            td.title = incompatible ? "Not applicable for this task" : "Not run";
          } else if (runPreset.benchKeys.has(col)) {
            td.textContent = "\u2705";
            td.classList.add("status-pass");
            td.title = "Pass";
          } else {
            td.textContent = "\u274C";
            td.classList.add("status-fail");
            td.title = "Fail (job ran but no data)";
          }
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      wrapper.appendChild(table);
      section.appendChild(wrapper);
      body.appendChild(section);
    }

    outer.appendChild(body);
    container.appendChild(outer);
  }

  /* ─── Init & Events ─── */

  async function init() {
    try {
      readUrlState();
      const manifest = await loadManifest();
      populateGpuSelect(manifest);

      const selectedDs = manifest.datasets.find((d) => d.gpu_type === state.currentGpu) || manifest.datasets[0];
      await loadGpuData(selectedDs.file);

      $("#lastUpdated").textContent = `Updated: ${new Date(manifest.generated_at).toLocaleDateString()}`;

      switchTab(state.currentTab || "comparison");
    } catch (err) {
      console.error("Init error:", err);
    } finally {
      $("#loadingOverlay").classList.add("hidden");
    }
  }

  $$(".nav-tab").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  $("#gpuSelectGlobal").addEventListener("change", async (e) => {
    state.currentGpu = e.target.value;
    state.compFilterRunIndex = -1;
    state.compEnv = "";
    state.compResolution = "";
    state.histEnv = "";
    state.histResolution = "";
    state.scalingResolution = "";
    compControlsInitialized = false;
    state.histFilterInited = false;
    state.histRunDetail = -1;
    const entry = state.manifest.datasets.find((d) => d.gpu_type === state.currentGpu);
    if (entry) {
      await loadGpuData(entry.file);
      renderCurrentTab();
    }
  });

  $("#runSelectComp").addEventListener("change", (e) => {
    state.compRunIndex = parseInt(e.target.value, 10);
    state.compFilterRunIndex = -1;
    renderComparison();
  });

  $("#taskSelectComp").addEventListener("change", (e) => {
    state.compTask = e.target.value;
    state.compEnv = "";
    state.compResolution = "";
    state.compFilterRunIndex = -1;
    renderComparison();
  });

  $("#envSelectComp").addEventListener("change", (e) => {
    state.compEnv = e.target.value;
    state.compResolution = "";
    state.compFilterRunIndex = -1;
    renderComparison();
  });

  $("#resSelectComp").addEventListener("change", (e) => {
    state.compResolution = e.target.value;
    state.compFilterRunIndex = -1;
    renderComparison();
  });

  $("#workflowSelectComp").addEventListener("change", (e) => {
    state.compWorkflow = e.target.value;
    renderComparison();
  });

  $("#runSelectScaling").addEventListener("change", (e) => {
    state.scalingRunIndex = parseInt(e.target.value, 10);
    renderScaling();
    syncUrlState();
  });

  $("#resSelectScaling").addEventListener("change", (e) => {
    state.scalingResolution = e.target.value;
    renderScaling();
    syncUrlState();
  });

  $("#scalingLinearToggle").addEventListener("change", (e) => {
    state.scalingLinearX = e.target.checked;
    renderScaling();
    syncUrlState();
  });

  initDropdownToggle("#scalingEnvFilterBtn", "#scalingEnvFilterPanel");

  $("#scalingEnvSelectAll").addEventListener("click", () => {
    state.scalingEnvFilter = new Set(ENV_SIZES.map(String));
    renderScaling();
    syncUrlState();
  });
  $("#scalingEnvDeselectAll").addEventListener("click", () => {
    state.scalingEnvFilter.clear();
    renderScaling();
    syncUrlState();
  });


  function initDropdownToggle(btnSel, panelSel) {
    $(btnSel).addEventListener("click", (e) => {
      e.stopPropagation();
      const panel = $(panelSel);
      const isOpen = panel.getAttribute("aria-hidden") !== "true";
      panel.setAttribute("aria-hidden", isOpen ? "true" : "false");
      panel.style.display = isOpen ? "none" : "block";
    });
    $(panelSel).addEventListener("click", (e) => e.stopPropagation());
  }

  initDropdownToggle("#physicsFilterBtn", "#physicsFilterPanel");
  initDropdownToggle("#rendererFilterBtn", "#rendererFilterPanel");
  initDropdownToggle("#datatypeFilterBtn", "#datatypeFilterPanel");

  document.addEventListener("click", () => {
    ["#physicsFilterPanel", "#rendererFilterPanel", "#datatypeFilterPanel",
     "#physicsFilterPanelHist", "#rendererFilterPanelHist", "#datatypeFilterPanelHist",
     "#scalingEnvFilterPanel"].forEach((sel) => {
      const panel = $(sel);
      if (panel && panel.getAttribute("aria-hidden") !== "true") {
        panel.setAttribute("aria-hidden", "true");
        panel.style.display = "none";
      }
    });
  });

  function initSelectDeselectAll(selectSel, deselectSel, dim) {
    $(selectSel).addEventListener("click", () => {
      const data = getCurrentData();
      if (!data) return;
      const run = data.runs[state.compRunIndex];
      if (!run) return;
      const dims = getRunPresetDims(run);
      const items = dim === "physics" ? dims.physics : dim === "renderer" ? dims.renderers : dims.datatypes;
      const filterSet = getFilterSetByDim(dim);
      items.forEach((v) => filterSet.add(v));
      renderComparison();
    });
    $(deselectSel).addEventListener("click", () => {
      const filterSet = getFilterSetByDim(dim);
      filterSet.clear();
      renderComparison();
    });
  }

  initSelectDeselectAll("#physicsSelectAll", "#physicsDeselectAll", "physics");
  initSelectDeselectAll("#rendererSelectAll", "#rendererDeselectAll", "renderer");
  initSelectDeselectAll("#datatypeSelectAll", "#datatypeDeselectAll", "datatype");

  $("#taskSelectHist").addEventListener("change", (e) => {
    state.histTask = e.target.value;
    state.histEnv = "";
    state.histResolution = "";
    state.histFilterInited = false;
    const data = getCurrentData();
    if (data) renderHistory();
  });

  $("#envSelectHist").addEventListener("change", (e) => {
    state.histEnv = e.target.value;
    state.histResolution = "";
    const data = getCurrentData();
    if (data) renderHistory();
  });

  $("#resSelectHist").addEventListener("change", (e) => {
    state.histResolution = e.target.value;
    const data = getCurrentData();
    if (data) renderHistory();
  });

  $("#workflowSelectHist").addEventListener("change", (e) => {
    state.histWorkflow = e.target.value;
    const data = getCurrentData();
    if (data) {
      populateHistMetrics(data);
      state.histMetric = $("#metricSelectHist").value;
      renderHistChart(data);
      syncUrlState();
    }
  });

  $("#metricSelectHist").addEventListener("change", (e) => {
    state.histMetric = e.target.value;
    const data = getCurrentData();
    if (data) {
      renderHistChart(data);
      syncUrlState();
    }
  });

  initDropdownToggle("#physicsFilterBtnHist", "#physicsFilterPanelHist");
  initDropdownToggle("#rendererFilterBtnHist", "#rendererFilterPanelHist");
  initDropdownToggle("#datatypeFilterBtnHist", "#datatypeFilterPanelHist");

  function initHistSelectDeselectAll(selectSel, deselectSel, dim) {
    $(selectSel).addEventListener("click", () => {
      const data = getCurrentData();
      if (!data) return;
      const hdims = getHistPresetDims(data);
      const items = dim === "physics" ? hdims.physics : dim === "renderer" ? hdims.renderers : hdims.datatypes;
      const filterSet = getHistFilterSet(dim);
      items.forEach((v) => filterSet.add(v));
      renderHistory();
      syncUrlState();
    });
    $(deselectSel).addEventListener("click", () => {
      getHistFilterSet(dim).clear();
      renderHistory();
      syncUrlState();
    });
  }

  initHistSelectDeselectAll("#physicsSelectAllHist", "#physicsDeselectAllHist", "physics");
  initHistSelectDeselectAll("#rendererSelectAllHist", "#rendererDeselectAllHist", "renderer");
  initHistSelectDeselectAll("#datatypeSelectAllHist", "#datatypeDeselectAllHist", "datatype");

  function initScrollHints() {
    $$(".heatmap-wrapper").forEach((wrapper) => {
      const hasOverflow = wrapper.scrollWidth > wrapper.clientWidth;
      wrapper.classList.toggle("has-overflow", hasOverflow);
      wrapper.classList.remove("scrolled-end");

      wrapper.addEventListener("scroll", () => {
        if (wrapper.scrollLeft > 0) wrapper.classList.add("scrolled-end");
        else wrapper.classList.remove("scrolled-end");
      });
    });
  }

  const origRenderComp = renderComparison;
  renderComparison = function () {
    origRenderComp();
    syncUrlState();
    requestAnimationFrame(initScrollHints);
  };

  init();
})();
