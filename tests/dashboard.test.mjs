// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA Corporation
// SPDX-License-Identifier: Apache-2.0

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

// A DOM recorder for the synchronous renderers. It deliberately does not parse
// HTML: benchmark values must reach text nodes, with presentation nodes retained.
function loadDashboard() {
  const htmlWrites = [];
  class Element {
    constructor(tagName) {
      this.tagName = tagName;
      this.children = [];
      this.className = '';
      this.style = {};
      this.listeners = {};
      this.classList = {
        add: (...names) => { this.className += ' ' + names.join(' '); },
        toggle: () => {},
      };
    }
    set textContent(value) { this.children = []; this.text = String(value); }
    get textContent() { return (this.text ?? '') + this.children.map(child => child.textContent).join(''); }
    set innerHTML(value) { this.children = []; this.text = ''; this.html = value; htmlWrites.push(value); }
    get innerHTML() { return this.html ?? ''; }
    appendChild(child) { this.children.push(child); return child; }
    append(...children) {
      for (const child of children) {
        if (typeof child === 'string') {
          const text = new Element('#text');
          text.textContent = child;
          this.appendChild(text);
        } else this.appendChild(child);
      }
    }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    querySelectorAll(selector) {
      const matches = node => selector.startsWith('.')
        ? node.className.split(/\s+/).includes(selector.slice(1))
        : node.tagName === selector;
      return this.children.flatMap(child => [
        ...(matches(child) ? [child] : []), ...child.querySelectorAll(selector),
      ]);
    }
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] ?? null;
    }
  }
  const roots = new Map();
  const document = {
    createElement: tag => new Element(tag),
    createTextNode: text => { const node = new Element('#text'); node.textContent = text; return node; },
    querySelector: selector => {
      if (!roots.has(selector)) roots.set(selector, new Element('div'));
      return roots.get(selector);
    },
  };
  const context = vm.createContext({ document, URLSearchParams,
    window: { location: { pathname: '/' } }, history: { replaceState() {} },
  });
  const source = readFileSync(new URL('../docs/js/dashboard.js', import.meta.url), 'utf8');
  const marker = '  /* ─── Init & Events ─── */';
  assert.ok(source.includes(marker));
  vm.runInContext(source.slice(0, source.indexOf(marker)) + `
    globalThis.dashboard = { state, renderInfo, renderVersionBar, detectPresetMismatches,
      buildFullTable, buildFpsRankCard, showHistRunDetail, renderBenchmarkStatusGrid };
  })();`, context);
  return { ...context.dashboard, document, htmlWrites };
}

const label = 'Team A & B "release"';
const preset = `${label},Renderer,RGB`;
const run = {
  commit_sha: 'abc123', commit_date: '2026-01-01', isaac_sim_version: label,
  hostname: label, env_info: {}, entries: [{ preset, ci_job_id: '123',
    actual_physics: 'Physics & Simulation', benchmarks: [{
      workflow: 'benchmark_non_rl', task: label, runtime: { FPS: 12 },
    }],
  }],
};

test('environment values retain their literal text and titles', () => {
  const d = loadDashboard();
  d.state.currentGpu = 'gpu';
  d.state.manifest = { datasets: [{ gpu_type: 'gpu', file: 'gpu' }] };
  d.state.datasets.gpu = { runs: [run] };
  d.renderInfo();
  const values = d.document.querySelector('#infoBenchmarkEnv').querySelectorAll('.value');
  assert.ok(values.some(value => value.textContent === label && value.title === label));
  assert.ok(!d.htmlWrites.some(html => html.includes(label)));
});

test('version values retain their literal text and titles', () => {
  const d = loadDashboard();
  d.renderVersionBar(run, '#versions');
  const values = d.document.querySelector('#versions').querySelectorAll('.version-value');
  assert.ok(values.some(value => value.textContent === label && value.title === label));
});

test('mismatch warnings keep emphasis around literal preset and engine names', () => {
  const d = loadDashboard();
  const warning = d.detectPresetMismatches(run)[0];
  assert.equal(warning.textContent, `⚠ Preset ${preset} configured physics as ${label}, but Physics & Simulation was actually used.`);
  assert.equal(warning.querySelectorAll('strong').length, 3);
  assert.equal(warning.className, 'warning-line');
});

test('table headings preserve the preset parts as styled text', () => {
  const d = loadDashboard();
  const table = d.buildFullTable('FPS', ['FPS'], [preset], { FPS: { [preset]: 12 } }, true);
  const physics = table.querySelector('.physics');
  assert.equal(physics?.textContent, label);
  assert.equal(table.querySelector('.renderer')?.textContent, 'Renderer');
  assert.equal(table.querySelector('.datatype')?.textContent, 'RGB');
});

test('ranking text retains environment and memory details plus the copy action', () => {
  const d = loadDashboard();
  const card = d.buildFpsRankCard('FPS', [preset], {
    FPS: { [preset]: 12 }, 'GPU Memory Used': { [preset]: 2 },
  }, 'benchmark_non_rl', { [preset]: 512 }, {}, {}, {}, {}, {}, run);
  assert.ok(card.querySelector('.rank-label')?.textContent.includes(label));
  assert.equal(card.querySelector('.rank-envs')?.textContent, '(512 envs)');
  assert.equal(card.querySelector('.rank-vram')?.textContent, '2.00 GB VRAM');
  assert.equal(typeof card.querySelector('.copy-cmd-btn')?.listeners.click, 'function');
});

test('history summary values and labels are text', () => {
  const d = loadDashboard();
  d.state.histWorkflow = 'benchmark_non_rl';
  d.state.histMetric = 'FPS';
  d.showHistRunDetail({ runs: [run] }, 0);
  const summary = d.document.querySelector('#histSummaryContent');
  assert.equal(summary.querySelector('.label')?.textContent, `${label} / Renderer / RGB`);
  assert.equal(summary.querySelector('.value')?.textContent, '12.00');
});

test('status columns retain literal task names and their header structure', () => {
  const d = loadDashboard();
  d.renderBenchmarkStatusGrid({ runs: [run] });
  const grid = d.document.querySelector('#benchmarkStatusGrid');
  assert.equal(grid.querySelector('.status-task-name')?.textContent, label);
  assert.equal(grid.querySelector('.status-col-header')?.children.length, 2);
});
