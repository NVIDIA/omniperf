(function () {
  "use strict";

  const DATA_BASE = "data";

  const FPS_METRIC_PRIORITY = [
    "Mean Total FPS",
    "Mean Environment step effective FPS",
    "Mean Environment + Inference + Policy update FPS",
  ];

  const PRIMARY_RUNTIME_METRICS = [
    "Mean Environment step FPS",
    "Mean Environment step effective FPS",
    "Mean Environment + Inference + Policy update FPS",
    "Mean Total FPS",
    "GPU Memory Used",
    "GPU Utilization",
    "CPU Utilization",
  ];

  const PRIMARY_STARTUP_METRICS = [
    "Total Start Time (Launch to Train)",
    "App Launch Time",
    "Scene Creation Time",
    "Task Creation and Start Time",
    "Simulation Start Time",
    "Python Imports Time",
  ];

  const METRIC_UNITS = {
    "Mean Environment step FPS": "FPS",
    "Max Environment step FPS": "FPS",
    "Min Environment step FPS": "FPS",
    "Mean Environment step effective FPS": "FPS",
    "Max Environment step effective FPS": "FPS",
    "Min Environment step effective FPS": "FPS",
    "Mean Environment step times": "ms",
    "Mean Environment + Inference + Policy update FPS": "FPS",
    "Mean Environment + Inference FPS": "FPS",
    "Mean Environment only FPS": "FPS",
    "Mean Total FPS": "FPS",
    "Mean Collection FPS": "FPS",
    "GPU Memory Used": "GB",
    "GPU Utilization": "%",
    "CPU Utilization": "%",
    "System Memory RSS": "GB",
    "System Memory USS": "GB",
    "System Memory VMS": "GB",
    "App Launch Time": "ms",
    "Python Imports Time": "ms",
    "Scene Creation Time": "ms",
    "Simulation Start Time": "ms",
    "Task Creation and Start Time": "ms",
    "Total Start Time (Launch to Train)": "ms",
  };

  const HIGHLIGHT_METRICS = new Set([
    "Mean Environment step FPS",
    "Mean Environment step effective FPS",
    "Mean Environment + Inference + Policy update FPS",
    "Mean Total FPS",
    "GPU Memory Used",
    "Total Start Time (Launch to Train)",
  ]);

  const WORKFLOW_ORDER = ["benchmark_non_rl", "benchmark_rlgames_train", "benchmark_rsl_rl_train"];
  const WORKFLOW_LABELS = {
    benchmark_non_rl: "Non-RL Simulation",
    benchmark_rlgames_train: "RL Games Training",
    benchmark_rsl_rl_train: "RSL RL Training",
  };
  const WORKFLOW_COLORS = {
    benchmark_non_rl: { line: "#58a6ff", fill: "rgba(88,166,255,0.08)" },
    benchmark_rlgames_train: { line: "#76b900", fill: "rgba(118,185,0,0.08)" },
    benchmark_rsl_rl_train: { line: "#a78bfa", fill: "rgba(167,139,250,0.08)" },
  };

  let state = {
    manifest: null,
    gpuData: {},
    currentGpu: null,
    currentTab: "overview",
    currentBenchmark: null,
    currentRunIndex: -1,
    currentSection: "runtime",
    currentMetric: null,
    detailChart: null,
    overviewCharts: [],
    tableSection: "runtime",
    overviewFilter: "",
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function getWorkflowClass(wf) {
    if (wf.includes("rlgames")) return "rlgames";
    if (wf.includes("rsl_rl")) return "rsl-rl";
    return "non-rl";
  }

  function getWorkflowLabel(wf) {
    if (wf.includes("rlgames")) return "RL Games";
    if (wf.includes("rsl_rl")) return "RSL RL";
    return "Non-RL";
  }

  function formatNumber(v) {
    if (v == null) return "—";
    if (typeof v !== "number") return String(v);
    if (Math.abs(v) >= 10000) return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
    if (Math.abs(v) >= 100) return v.toLocaleString("en-US", { maximumFractionDigits: 1 });
    if (Math.abs(v) >= 1) return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
    return v.toLocaleString("en-US", { maximumFractionDigits: 4 });
  }

  function parseBenchmarkDisplay(bench) {
    return (bench.task || bench.key) + (bench.num_envs ? ` (${bench.num_envs.toLocaleString()} envs)` : "");
  }

  function getPrimaryFPS(bench) {
    if (!bench.runtime) return { metric: null, value: null };
    for (const m of FPS_METRIC_PRIORITY) {
      if (bench.runtime[m] != null) return { metric: m, value: bench.runtime[m] };
    }
    return { metric: null, value: null };
  }

  function getSelectedRun() {
    const data = state.gpuData[state.currentGpu];
    if (!data || !data.runs.length) return null;
    const idx = state.currentRunIndex;
    if (idx >= 0 && idx < data.runs.length) return data.runs[idx];
    return data.runs[data.runs.length - 1];
  }

  async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
    return resp.json();
  }

  // ===== INIT =====
  async function init() {
    try {
      state.manifest = await fetchJSON(`${DATA_BASE}/manifest.json`);
      populateGPUSelect();
      setupEventListeners();
      if (state.manifest.datasets.length > 0) {
        await loadGPU(state.manifest.datasets[0].file);
      }
      const updatedEl = $("#lastUpdated");
      const dateStr = "Updated: " +
        new Date(state.manifest.generated_at).toLocaleDateString("en-US", {
          year: "numeric", month: "short", day: "numeric",
        });
      updatedEl.childNodes[0]
        ? (updatedEl.childNodes[0].textContent = dateStr)
        : updatedEl.insertBefore(document.createTextNode(dateStr), updatedEl.firstChild);
    } catch (e) {
      console.error("Init failed:", e);
    } finally {
      $("#loadingOverlay").classList.add("hidden");
    }
  }

  function populateGPUSelect() {
    const sel = $("#gpuSelectGlobal");
    sel.innerHTML = "";
    state.manifest.datasets.forEach((ds) => {
      const opt = document.createElement("option");
      opt.value = ds.file;
      opt.textContent = `${ds.gpu_display_name} (${ds.total_runs} runs)`;
      sel.appendChild(opt);
    });
  }

  async function loadGPU(file) {
    if (!state.gpuData[file]) {
      $("#loadingOverlay").classList.remove("hidden");
      state.gpuData[file] = await fetchJSON(`${DATA_BASE}/${file}`);
      $("#loadingOverlay").classList.add("hidden");
    }
    state.currentGpu = file;
    const data = state.gpuData[file];
    state.currentRunIndex = data.runs.length - 1;
    populateBenchmarkSelect(data);
    populateRunSelect(data);
    renderCurrentTab();
  }

  // ===== TAB SWITCHING =====
  function switchTab(tab) {
    state.currentTab = tab;
    $$(".nav-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    $$("#overviewPanel, #detailPanel").forEach((p) => p.classList.remove("active"));
    $(`#${tab}Panel`).classList.add("active");
    renderCurrentTab();
  }

  function renderCurrentTab() {
    if (state.currentTab === "overview") {
      renderOverview();
    } else {
      updateDetailAll();
    }
  }

  // ===== OVERVIEW TAB =====
  function destroyOverviewCharts() {
    state.overviewCharts.forEach((c) => c.destroy());
    state.overviewCharts = [];
  }

  function getAllBenchmarkNames() {
    const data = state.gpuData[state.currentGpu];
    if (!data || !data.runs.length) return [];
    const latest = data.runs[data.runs.length - 1];
    return latest.benchmarks.map((b) => ({
      key: b.key,
      task: b.task || b.key,
      num_envs: b.num_envs,
      workflow: b.workflow || "",
    }));
  }

  function showSuggestions(query) {
    const box = $("#searchSuggestions");
    if (!query) { box.classList.remove("visible"); box.innerHTML = ""; return; }

    const all = getAllBenchmarkNames();
    const q = query.toLowerCase();
    const matches = all.filter((b) => b.task.toLowerCase().includes(q));

    if (matches.length === 0) {
      box.innerHTML = '<div class="suggestion-item"><span class="sug-name" style="color:var(--text-muted)">No matches</span></div>';
      box.classList.add("visible");
      return;
    }

    box.innerHTML = "";
    matches.slice(0, 10).forEach((b) => {
      const item = document.createElement("div");
      item.className = "suggestion-item";

      const nameSpan = document.createElement("span");
      nameSpan.className = "sug-name";
      const idx = b.task.toLowerCase().indexOf(q);
      nameSpan.innerHTML = b.task.slice(0, idx) + "<mark>" + b.task.slice(idx, idx + q.length) + "</mark>" + b.task.slice(idx + q.length);
      item.appendChild(nameSpan);

      const tag = document.createElement("span");
      tag.className = "workflow-tag sug-tag " + getWorkflowClass(b.workflow);
      tag.textContent = getWorkflowLabel(b.workflow);
      item.appendChild(tag);

      item.addEventListener("click", () => {
        $("#overviewSearch").value = b.task;
        state.overviewFilter = b.task.toLowerCase();
        box.classList.remove("visible");
        renderOverview();
      });

      box.appendChild(item);
    });
    if (matches.length > 10) {
      const more = document.createElement("div");
      more.className = "suggestion-item";
      more.innerHTML = `<span class="sug-name" style="color:var(--text-muted)">... and ${matches.length - 10} more</span>`;
      box.appendChild(more);
    }
    box.classList.add("visible");
  }

  function renderOverview() {
    const data = state.gpuData[state.currentGpu];
    if (!data || !data.runs.length) return;

    destroyOverviewCharts();
    const container = $("#overviewGrid");
    container.innerHTML = "";

    const filter = state.overviewFilter;
    const clearBtn = $("#searchClear");
    clearBtn.style.display = filter ? "block" : "none";

    if (filter) {
      const badge = document.createElement("div");
      badge.className = "search-active-filter";
      badge.innerHTML = `Showing: "${filter}" <button id="filterClearBadge">&times;</button>`;
      container.appendChild(badge);
      badge.querySelector("button").addEventListener("click", () => {
        state.overviewFilter = "";
        $("#overviewSearch").value = "";
        clearBtn.style.display = "none";
        renderOverview();
      });
    }

    const latest = data.runs[data.runs.length - 1];
    const grouped = {};
    latest.benchmarks.forEach((b) => {
      if (filter && !(b.task || b.key).toLowerCase().includes(filter)) return;
      const wf = b.workflow || "other";
      if (!grouped[wf]) grouped[wf] = [];
      grouped[wf].push(b);
    });

    const sortedGroups = Object.keys(grouped).sort(
      (a, b) => (WORKFLOW_ORDER.indexOf(a) === -1 ? 99 : WORKFLOW_ORDER.indexOf(a)) -
                (WORKFLOW_ORDER.indexOf(b) === -1 ? 99 : WORKFLOW_ORDER.indexOf(b))
    );

    sortedGroups.forEach((wf) => {
      const benchmarks = grouped[wf].sort((a, b) => (a.task || a.key).localeCompare(b.task || b.key));

      const title = document.createElement("div");
      title.className = "overview-section-title";
      const tag = document.createElement("span");
      tag.className = "workflow-tag " + getWorkflowClass(wf);
      tag.textContent = getWorkflowLabel(wf);
      title.appendChild(tag);
      title.appendChild(document.createTextNode(" " + (WORKFLOW_LABELS[wf] || wf)));
      const count = document.createElement("span");
      count.className = "section-count";
      count.textContent = `(${benchmarks.length})`;
      title.appendChild(count);
      container.appendChild(title);

      const grid = document.createElement("div");
      grid.className = "overview-chart-grid";
      container.appendChild(grid);

      benchmarks.forEach((bench) => {
        const { metric, value } = getPrimaryFPS(bench);
        if (!metric) return;

        const card = document.createElement("div");
        card.className = "mini-card";
        card.addEventListener("click", () => {
          state.currentBenchmark = bench.key;
          state.currentSection = "runtime";
          $("#sectionSelect").value = "runtime";
          state.currentMetric = metric;
          $("#benchmarkSelect").value = bench.key;
          switchTab("detail");
          updateDetailAll();
        });

        const hdr = document.createElement("div");
        hdr.className = "mini-card-header";

        const titleEl = document.createElement("span");
        titleEl.className = "mini-card-title";
        titleEl.textContent = bench.task || bench.key;
        titleEl.title = bench.key;
        hdr.appendChild(titleEl);

        if (bench.num_envs) {
          const envs = document.createElement("span");
          envs.className = "mini-card-envs";
          envs.textContent = `${bench.num_envs.toLocaleString()} envs`;
          hdr.appendChild(envs);
        }

        const valEl = document.createElement("span");
        valEl.className = "mini-card-value";
        valEl.innerHTML = `${formatNumber(value)}<span class="mini-unit">FPS</span>`;
        hdr.appendChild(valEl);

        card.appendChild(hdr);

        const chartWrap = document.createElement("div");
        chartWrap.className = "mini-chart-container";
        const canvas = document.createElement("canvas");
        chartWrap.appendChild(canvas);
        card.appendChild(chartWrap);
        grid.appendChild(card);

        const labels = [];
        const values = [];
        data.runs.forEach((run) => {
          const b = run.benchmarks.find((x) => x.key === bench.key);
          if (!b || !b.runtime || b.runtime[metric] == null) return;
          labels.push(run.commit_sha ? run.commit_sha.slice(0, 7) : "?");
          values.push(b.runtime[metric]);
        });

        const wfColor = WORKFLOW_COLORS[wf] || { line: "#76b900", fill: "rgba(118,185,0,0.08)" };

        const chart = new Chart(canvas.getContext("2d"), {
          type: "line",
          data: {
            labels,
            datasets: [{
              data: values,
              borderColor: wfColor.line,
              backgroundColor: wfColor.fill,
              borderWidth: 1.5,
              pointRadius: 0,
              pointHoverRadius: 3,
              fill: true,
              tension: 0.3,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: "#1c2128",
                titleColor: "#e6edf3",
                bodyColor: "#e6edf3",
                borderColor: "#30363d",
                borderWidth: 1,
                padding: 8,
                displayColors: false,
                callbacks: {
                  title: (items) => `Commit: ${items[0].label}`,
                  label: (item) => `${metric}: ${formatNumber(item.raw)} FPS`,
                },
              },
            },
            scales: {
              x: { display: false },
              y: {
                display: true,
                ticks: { color: "#6e7681", font: { size: 9 }, maxTicksLimit: 3, callback: (v) => formatNumber(v) },
                grid: { color: "rgba(48,54,61,0.3)", drawBorder: false },
              },
            },
          },
        });
        state.overviewCharts.push(chart);
      });
    });
  }

  // ===== DETAIL TAB =====
  function populateBenchmarkSelect(data) {
    const sel = $("#benchmarkSelect");
    sel.innerHTML = "";
    if (!data.runs.length) return;

    const latest = data.runs[data.runs.length - 1];
    const grouped = {};
    latest.benchmarks.forEach((b) => {
      const wf = b.workflow || "other";
      if (!grouped[wf]) grouped[wf] = [];
      grouped[wf].push(b);
    });

    const sortedGroups = Object.keys(grouped).sort(
      (a, b) => (WORKFLOW_ORDER.indexOf(a) === -1 ? 99 : WORKFLOW_ORDER.indexOf(a)) -
                (WORKFLOW_ORDER.indexOf(b) === -1 ? 99 : WORKFLOW_ORDER.indexOf(b))
    );

    sortedGroups.forEach((wf) => {
      const group = document.createElement("optgroup");
      group.label = WORKFLOW_LABELS[wf] || wf;
      grouped[wf]
        .sort((a, b) => (a.task || a.key).localeCompare(b.task || b.key))
        .forEach((b) => {
          const opt = document.createElement("option");
          opt.value = b.key;
          opt.textContent = parseBenchmarkDisplay(b);
          group.appendChild(opt);
        });
      sel.appendChild(group);
    });

    const preferred = "benchmark_non_rl_Isaac-Repose-Cube-Shadow-Vision-Direct-v0_1225";
    const match = Array.from(sel.options).find((o) => o.value === preferred);
    if (match) sel.value = preferred;
    state.currentBenchmark = sel.value;
  }

  function populateRunSelect(data) {
    const sel = $("#runSelect");
    sel.innerHTML = "";
    if (!data.runs.length) return;

    for (let i = data.runs.length - 1; i >= 0; i--) {
      const run = data.runs[i];
      const sha = run.commit_sha ? run.commit_sha.slice(0, 7) : "?";
      const date = run.timestamp ? run.timestamp.split("T")[0] : "";
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = `${sha} · ${date}${i === data.runs.length - 1 ? " (latest)" : ""}`;
      sel.appendChild(opt);
    }
    sel.value = state.currentRunIndex;
  }

  function getMetricsForBenchmark(data, benchKey, section) {
    const run = getSelectedRun();
    if (!run) return [];
    const bench = run.benchmarks.find((b) => b.key === benchKey);
    if (!bench || !bench[section]) return [];
    const primary = section === "runtime" ? PRIMARY_RUNTIME_METRICS : PRIMARY_STARTUP_METRICS;
    return Object.keys(bench[section]).sort((a, b) => {
      const ai = primary.indexOf(a);
      const bi = primary.indexOf(b);
      if (ai !== -1 && bi !== -1) return ai - bi;
      if (ai !== -1) return -1;
      if (bi !== -1) return 1;
      return a.localeCompare(b);
    });
  }

  function populateMetricSelect() {
    const sel = $("#metricSelect");
    sel.innerHTML = "";
    const data = state.gpuData[state.currentGpu];
    if (!data) return;

    const metrics = getMetricsForBenchmark(data, state.currentBenchmark, state.currentSection);
    const primary = state.currentSection === "runtime" ? PRIMARY_RUNTIME_METRICS : PRIMARY_STARTUP_METRICS;

    let hasPrimary = false, hasOther = false;

    metrics.forEach((m) => {
      if (primary.includes(m)) {
        if (!hasPrimary) { const g = document.createElement("optgroup"); g.label = "Key Metrics"; sel.appendChild(g); hasPrimary = true; }
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m + (METRIC_UNITS[m] ? ` (${METRIC_UNITS[m]})` : "");
        sel.querySelector("optgroup:first-child").appendChild(opt);
      }
    });

    metrics.forEach((m) => {
      if (!primary.includes(m)) {
        if (!hasOther) { const g = document.createElement("optgroup"); g.label = "All Metrics"; sel.appendChild(g); hasOther = true; }
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m + (METRIC_UNITS[m] ? ` (${METRIC_UNITS[m]})` : "");
        sel.querySelector("optgroup:last-child").appendChild(opt);
      }
    });

    if (state.currentMetric && metrics.includes(state.currentMetric)) {
      sel.value = state.currentMetric;
    } else if (metrics.length > 0) {
      sel.value = metrics[0];
      state.currentMetric = metrics[0];
    }
  }

  function updateDetailChart() {
    const data = state.gpuData[state.currentGpu];
    if (!data || !data.runs.length) return;

    const benchKey = state.currentBenchmark;
    const section = state.currentSection;
    const metric = state.currentMetric || $("#metricSelect").value;

    const labels = [], values = [], runIndices = [];

    data.runs.forEach((run, idx) => {
      const bench = run.benchmarks.find((b) => b.key === benchKey);
      if (!bench || !bench[section] || bench[section][metric] == null) return;
      labels.push((run.commit_sha ? run.commit_sha.slice(0, 7) : "?") + "\n" + (run.timestamp ? run.timestamp.split("T")[0] : ""));
      values.push(bench[section][metric]);
      runIndices.push(idx);
    });

    const selectedChartIdx = runIndices.indexOf(state.currentRunIndex);
    const unit = METRIC_UNITS[metric] || "";

    if (state.detailChart) state.detailChart.destroy();

    state.detailChart = new Chart($("#mainChart").getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: metric,
          data: values,
          borderColor: "#76b900",
          backgroundColor: "rgba(118,185,0,0.08)",
          borderWidth: 2,
          pointRadius: values.map((_, i) => i === selectedChartIdx ? 7 : (values.length > 60 ? 0 : 3)),
          pointHoverRadius: 6,
          pointBackgroundColor: values.map((_, i) => i === selectedChartIdx ? "#ffffff" : "#76b900"),
          pointBorderColor: "#76b900",
          pointBorderWidth: values.map((_, i) => i === selectedChartIdx ? 3 : 1),
          fill: true,
          tension: 0.2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        onClick: (evt, elements) => {
          if (elements.length > 0) {
            state.currentRunIndex = runIndices[elements[0].index];
            $("#runSelect").value = state.currentRunIndex;
            updateDetailChart();
            updateSummary();
            updateOverviewTable();
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1c2128", titleColor: "#e6edf3", bodyColor: "#e6edf3",
            borderColor: "#30363d", borderWidth: 1, padding: 12, displayColors: false,
            callbacks: {
              title: (items) => { const p = items[0].label.split("\n"); return `Commit: ${p[0]}  |  ${p[1]}`; },
              label: (item) => `${metric}: ${formatNumber(item.raw)}${unit ? " " + unit : ""}`,
              afterLabel: (item) => runIndices[item.dataIndex] === state.currentRunIndex ? "▸ Selected run" : "Click to select",
            },
          },
        },
        scales: {
          x: {
            ticks: { color: "#6e7681", font: { size: 10 }, maxRotation: 45, autoSkip: true, maxTicksLimit: 20, callback: function (v) { return this.getLabelForValue(v).split("\n")[0]; } },
            grid: { color: "rgba(48,54,61,0.5)", drawBorder: false },
          },
          y: {
            ticks: { color: "#6e7681", font: { size: 11 }, callback: (v) => formatNumber(v) },
            grid: { color: "rgba(48,54,61,0.5)", drawBorder: false },
            title: { display: !!unit, text: unit, color: "#8b949e", font: { size: 11 } },
          },
        },
      },
    });

    $("#chartTitle").textContent = metric;
    $("#chartRunCount").textContent = `${values.length} data points`;
    if (data.runs.length > 0) {
      const first = data.runs[0].timestamp?.split("T")[0] || "";
      const last = data.runs[data.runs.length - 1].timestamp?.split("T")[0] || "";
      $("#chartDateRange").textContent = `${first} → ${last}`;
    }
  }

  function updateSummary() {
    const data = state.gpuData[state.currentGpu];
    if (!data || !data.runs.length) return;

    const run = getSelectedRun();
    if (!run) return;
    const bench = run.benchmarks.find((b) => b.key === state.currentBenchmark);
    if (!bench) return;

    const sha = run.commit_sha || "?";
    const date = run.timestamp ? run.timestamp.split("T")[0] : "";
    const isLatest = state.currentRunIndex === data.runs.length - 1;
    $("#summaryCommit").textContent = `${sha.slice(0, 7)} · ${date}${isLatest ? " (latest)" : ""}`;

    const versionBar = $("#versionBar");
    versionBar.innerHTML = "";
    [
      { label: "App Version", value: run.app_version },
      { label: "Isaac Lab", value: run.isaaclab_version_sha ? run.isaaclab_version_sha.slice(0, 12) : null, full: run.isaaclab_version_sha },
      { label: "Driver", value: run.driver },
      { label: "Branch", value: run.branch },
    ].forEach(({ label, value, full }) => {
      if (!value) return;
      const item = document.createElement("div");
      item.className = "version-item";
      item.innerHTML = `<span class="ver-label">${label}</span><span class="ver-value" title="${full || value}">${value}</span>`;
      versionBar.appendChild(item);
    });

    const container = $("#summaryContent");
    container.innerHTML = "";

    [{ key: "runtime" }, { key: "startup" }].forEach(({ key }) => {
      const sectionData = bench[key];
      if (!sectionData) return;
      const primary = key === "runtime" ? PRIMARY_RUNTIME_METRICS : PRIMARY_STARTUP_METRICS;
      primary.forEach((metric) => {
        if (sectionData[metric] == null) return;
        const unit = METRIC_UNITS[metric] || "";
        const div = document.createElement("div");
        div.className = "summary-item" + (HIGHLIGHT_METRICS.has(metric) ? " highlight" : "");
        div.innerHTML = `<div class="label">${metric}</div><div class="value">${formatNumber(sectionData[metric])}<span class="unit">${unit}</span></div>`;
        container.appendChild(div);
      });
    });
  }

  function updateOverviewTable() {
    const data = state.gpuData[state.currentGpu];
    if (!data || !data.runs.length) return;

    const section = state.tableSection;
    const run = getSelectedRun();
    if (!run) return;

    const allMetrics = new Set();
    run.benchmarks.forEach((b) => { if (b[section]) Object.keys(b[section]).forEach((k) => allMetrics.add(k)); });

    const primary = section === "runtime" ? PRIMARY_RUNTIME_METRICS : PRIMARY_STARTUP_METRICS;
    const displayMetrics = [...allMetrics].filter((m) => primary.includes(m)).sort((a, b) => primary.indexOf(a) - primary.indexOf(b));

    const header = $("#overviewHeader");
    header.innerHTML = '<th>Benchmark</th><th>Type</th>';
    displayMetrics.forEach((m) => {
      const th = document.createElement("th");
      th.textContent = m.replace("Mean ", "").replace(" FPS", "\nFPS").replace(" Time", "\nTime");
      th.title = m;
      th.style.textAlign = "right";
      header.appendChild(th);
    });

    const body = $("#overviewBody");
    body.innerHTML = "";

    [...run.benchmarks].sort((a, b) => {
      const wfA = WORKFLOW_ORDER.indexOf(a.workflow);
      const wfB = WORKFLOW_ORDER.indexOf(b.workflow);
      if (wfA !== wfB) return (wfA === -1 ? 99 : wfA) - (wfB === -1 ? 99 : wfB);
      return (a.task || a.key).localeCompare(b.task || b.key);
    }).forEach((bench) => {
      const tr = document.createElement("tr");
      if (bench.key === state.currentBenchmark) tr.classList.add("selected-row");
      tr.style.cursor = "pointer";
      tr.addEventListener("click", () => {
        state.currentBenchmark = bench.key;
        $("#benchmarkSelect").value = bench.key;
        populateMetricSelect();
        state.currentMetric = $("#metricSelect").value;
        updateDetailChart();
        updateSummary();
        updateOverviewTable();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });

      const tdName = document.createElement("td");
      tdName.className = "benchmark-name";
      tdName.textContent = parseBenchmarkDisplay(bench);
      tdName.title = bench.key;
      tr.appendChild(tdName);

      const tdType = document.createElement("td");
      const tag = document.createElement("span");
      tag.className = "workflow-tag " + getWorkflowClass(bench.workflow || "");
      tag.textContent = getWorkflowLabel(bench.workflow || "");
      tdType.appendChild(tag);
      tr.appendChild(tdType);

      displayMetrics.forEach((m) => {
        const td = document.createElement("td");
        td.className = "numeric";
        td.textContent = formatNumber(bench[section] ? bench[section][m] : null);
        tr.appendChild(td);
      });

      body.appendChild(tr);
    });
  }

  function updateDetailAll() {
    populateMetricSelect();
    state.currentMetric = $("#metricSelect").value;
    updateDetailChart();
    updateSummary();
    updateOverviewTable();
  }

  // ===== EVENT LISTENERS =====
  function setupEventListeners() {
    $$(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    $("#gpuSelectGlobal").addEventListener("change", (e) => loadGPU(e.target.value));

    const searchInput = $("#overviewSearch");
    searchInput.addEventListener("input", () => showSuggestions(searchInput.value));

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        state.overviewFilter = searchInput.value.toLowerCase();
        $("#searchSuggestions").classList.remove("visible");
        renderOverview();
      }
      if (e.key === "Escape") {
        searchInput.value = "";
        state.overviewFilter = "";
        $("#searchSuggestions").classList.remove("visible");
        renderOverview();
      }
    });

    $("#searchClear").addEventListener("click", () => {
      searchInput.value = "";
      state.overviewFilter = "";
      $("#searchSuggestions").classList.remove("visible");
      renderOverview();
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-bar")) {
        $("#searchSuggestions").classList.remove("visible");
      }
    });

    $("#benchmarkSelect").addEventListener("change", (e) => {
      state.currentBenchmark = e.target.value;
      populateMetricSelect();
      state.currentMetric = $("#metricSelect").value;
      updateDetailChart();
      updateSummary();
      updateOverviewTable();
    });

    $("#runSelect").addEventListener("change", (e) => {
      state.currentRunIndex = parseInt(e.target.value, 10);
      updateDetailChart();
      updateSummary();
      updateOverviewTable();
    });

    $("#sectionSelect").addEventListener("change", (e) => {
      state.currentSection = e.target.value;
      populateMetricSelect();
      state.currentMetric = $("#metricSelect").value;
      updateDetailChart();
      updateSummary();
    });

    $("#metricSelect").addEventListener("change", (e) => {
      state.currentMetric = e.target.value;
      updateDetailChart();
    });

    $$(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.tableSection = btn.dataset.section;
        updateOverviewTable();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
