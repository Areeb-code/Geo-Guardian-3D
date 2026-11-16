import { initGlobe, flyToAOI, toggleHorizonTilt, updateGEELayers, bindLayerControls } from './globe_layers.js';

const API_BASE = 'http://127.0.0.1:8000/api';

let currentMode = 'live';
let currentCenter = [74.325, 31.49];

// 1. Populate Year Dropdowns (1984 to 2026)
function populateYearSelectors() {
  const selectA = document.getElementById('year-a');
  const selectB = document.getElementById('year-b');
  for (let y = 2026; y >= 1984; y--) {
    selectA.add(new Option(y, y, y === 2015, y === 2015));
    selectB.add(new Option(y, y, y === 2025, y === 2025));
  }
}

// 2. Animated Sliding Pill Tabs
function setupSlidingTabs() {
  const tabContainer = document.querySelector('.segmented-tabs');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const panes = {
    live: document.getElementById('panel-live'),
    compare: document.getElementById('panel-compare'),
  };

  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      if (target === currentMode) return;

      currentMode = target;
      tabContainer.dataset.active = target;

      tabButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      Object.entries(panes).forEach(([key, pane]) => {
        pane.classList.toggle('active', key === target);
      });
    });
  });
}

// 3. Collapsible Glass Docks (Contract into Floating Icons & Expand Back)
function setupCollapsibleDocks() {
  const leftDock = document.getElementById('left-dock');
  const rightDock = document.getElementById('right-dock');
  const btnCloseLeft = document.getElementById('btn-close-left');
  const btnOpenLeft = document.getElementById('btn-open-left');
  const btnCloseRight = document.getElementById('btn-close-right');
  const btnOpenRight = document.getElementById('btn-open-right');

  btnCloseLeft.addEventListener('click', () => {
    leftDock.classList.add('collapsed');
    btnOpenLeft.classList.remove('hidden');
  });

  btnOpenLeft.addEventListener('click', () => {
    leftDock.classList.remove('collapsed');
    btnOpenLeft.classList.add('hidden');
  });

  btnCloseRight.addEventListener('click', () => {
    rightDock.classList.add('collapsed');
    btnOpenRight.classList.remove('hidden');
  });

  btnOpenRight.addEventListener('click', () => {
    rightDock.classList.remove('collapsed');
    btnOpenRight.classList.add('hidden');
  });
}

// 4. Loading Toast Helper
function setLoading(isLoading, message = 'Querying Google Earth Engine...') {
  const toast = document.getElementById('loading-toast');
  const text = document.getElementById('loading-text');
  const btns = document.querySelectorAll('.btn-primary');

  text.innerText = message;
  toast.classList.toggle('hidden', !isLoading);
  btns.forEach((b) => (b.disabled = isLoading));
}

// 5. Fetch Data Sequentially From FastAPI & Update 3D Globe
async function runAnalysis(forceRefresh = false) {
  const location = document.getElementById('location-input').value.trim() || 'Lahore';
  const params = new URLSearchParams({
    location,
    mode: currentMode,
    refresh: forceRefresh ? 'true' : 'false',
  });

  if (currentMode === 'live') {
    const smogDate = document.getElementById('live-smog-date').value;
    if (smogDate) params.set('smog_date', smogDate);
  } else {
    const yearA = document.getElementById('year-a').value;
    const yearB = document.getElementById('year-b').value;
    params.set('year_a', yearA);
    params.set('year_b', yearB);
  }

  setLoading(true, `Analyzing ${location} via Earth Engine (5-8s)...`);

  try {
    // Step A: Fetch metrics first (computes & caches result on backend)
    const metricsRes = await fetch(`${API_BASE}/metrics?${params.toString()}`);
    if (!metricsRes.ok) {
      const errData = await metricsRes.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error (${metricsRes.status})`);
    }
    const metrics = await metricsRes.json();

    // Step B: Fetch tiles second (instant 0ms cache read on backend)
    params.set('refresh', 'false');
    const tilesRes = await fetch(`${API_BASE}/tiles?${params.toString()}`);
    if (!tilesRes.ok) {
      throw new Error(`Tile fetch error (${tilesRes.status})`);
    }
    const tiles = await tilesRes.json();

    // Update Telemetry Cards
    document.getElementById('ui-aoi-name').innerText = metrics.aoi;
    document.getElementById('ui-total-area').innerText = `${metrics.total_area_sqkm} km²`;
    document.getElementById('ui-converted').innerText = `${metrics.converted_sqkm} km²`;
    document.getElementById('ui-loss-pct').innerText = `${metrics.loss_pct}% farmland converted`;

    document.getElementById('ui-smog-status').innerText = metrics.smog_status;
    const smogValText = metrics.smog_b_index !== null ? metrics.smog_b_index : 'N/A';
    document.getElementById('ui-smog-index').innerText = `UV Aerosol Index: ${smogValText}`;

    document.getElementById('ui-label-a').innerText = metrics.year_a_label;
    document.getElementById('ui-built-a').innerText = `${metrics.built_a_sqkm} km² built`;
    document.getElementById('ui-veg-a').innerText = `Veg: ${metrics.veg_a_sqkm} km²`;

    document.getElementById('ui-label-b').innerText = metrics.year_b_label;
    document.getElementById('ui-built-b').innerText = `${metrics.built_b_sqkm} km² built`;
    document.getElementById('ui-veg-b').innerText = `Veg: ${metrics.veg_b_sqkm} km²`;

    document.getElementById('tag-rgb-a').innerText = metrics.year_a_label.split(' ')[0];
    document.getElementById('tag-rgb-b').innerText = metrics.year_b_label.split(' ')[0];
    document.getElementById('ui-window-info').innerText = `Smog Window: ${metrics.smog_date_window}`;

    // Fly 3D Camera & Render Satellite Overlays
    currentCenter = metrics.center;
    flyToAOI(currentCenter, false);
    updateGEELayers(tiles);
  } catch (err) {
    console.error(err);
    document.getElementById('ui-window-info').innerText = `Error: ${err.message}`;
  } finally {
    setLoading(false);
  }
}

// 6. Bootstrap Application
window.addEventListener('DOMContentLoaded', () => {
  initGlobe();
  populateYearSelectors();
  setupSlidingTabs();
  setupCollapsibleDocks();
  bindLayerControls();

  document.getElementById('location-form').addEventListener('submit', (e) => {
    e.preventDefault();
    runAnalysis(false);
  });

  document.getElementById('btn-run-live').addEventListener('click', () => runAnalysis(true));
  document.getElementById('btn-run-compare').addEventListener('click', () => runAnalysis(false));

  document.getElementById('btn-clear-date').addEventListener('click', () => {
    document.getElementById('live-smog-date').value = '';
    runAnalysis(false);
  });

  document.getElementById('btn-fly-aoi').addEventListener('click', () => flyToAOI(currentCenter, false));
  document.getElementById('btn-tilt-3d').addEventListener('click', () => toggleHorizonTilt(currentCenter));

  // Initial load flies from space into Lahore
  runAnalysis(false);
});