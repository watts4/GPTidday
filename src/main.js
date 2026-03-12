import { createInitialState } from './game/state.js';
import { attemptSpread, processTurn, researchAdaptation } from './game/mechanics.js';
import { exportSave, importSave, loadGame, saveGame } from './game/storage.js';
import { renderAll } from './ui/render.js';
import { openCodexDialog, openNewGameDialog, openSettingsDialog } from './ui/dialogs.js';

const els = {
  mapCanvas: document.getElementById('mapCanvas'),
  hostPanel: document.getElementById('hostPanel'),
  factionPanel: document.getElementById('factionPanel'),
  regionPanel: document.getElementById('regionPanel'),
  researchPanel: document.getElementById('researchPanel'),
  logPanel: document.getElementById('logPanel'),
  endTurnBtn: document.getElementById('endTurnBtn'),
  menuDialog: document.getElementById('menuDialog'),
  codexDialog: document.getElementById('codexDialog'),
  settingsDialog: document.getElementById('settingsDialog')
};

let state = loadGame();
if (!state) {
  openNewGameDialog(els.menuDialog, (faction) => {
    state = createInitialState(faction);
    els.menuDialog.close();
    boot();
  });
} else {
  boot();
}

function boot() {
  els.onResearch = (adaptation) => {
    const err = researchAdaptation(state, adaptation);
    if (err) state.log.unshift(err);
    refresh();
  };

  bindUI();
  refresh();
}

function bindUI() {
  document.getElementById('newGameBtn').onclick = () => openNewGameDialog(els.menuDialog, (f) => {
    state = createInitialState(f, state?.difficulty || 'normal');
    els.menuDialog.close();
    refresh();
  });
  document.getElementById('saveBtn').onclick = () => saveGame(state);
  document.getElementById('loadBtn').onclick = () => {
    const loaded = loadGame();
    if (loaded) {
      state = loaded;
      refresh();
    }
  };
  document.getElementById('exportBtn').onclick = () => exportSave(state);
  document.getElementById('importInput').onchange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      state = await importSave(file);
      refresh();
    } catch {
      state.log.unshift('Import failed: invalid save JSON.');
      refresh();
    }
  };
  document.getElementById('codexBtn').onclick = () => openCodexDialog(els.codexDialog);
  document.getElementById('settingsBtn').onclick = () => openSettingsDialog(els.settingsDialog, state, (updated) => {
    state.difficulty = updated.difficulty;
    state.modifiers.scanlines = updated.scanlines;
    state.modifiers.crt = updated.crt;
    refresh();
  });

  els.endTurnBtn.onclick = () => {
    if (state.outcome) return;
    processTurn(state);
    if (state.outcome) state.log.unshift(`${state.outcome.type.toUpperCase()}: ${state.outcome.text}`);
    refresh();
  };

  els.mapCanvas.onclick = (event) => {
    const rect = els.mapCanvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * els.mapCanvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * els.mapCanvas.height;
    const region = nearestRegion(x, y);
    if (!region) return;

    if (event.shiftKey) {
      const err = attemptSpread(state, state.selectedRegionId, region.id);
      if (err) state.log.unshift(err);
    }
    state.selectedRegionId = region.id;
    refresh();
  };
}

function nearestRegion(x, y) {
  let best = null;
  let dist = Infinity;
  for (const region of Object.values(state.regions)) {
    const d = Math.hypot(region.x - x, region.y - y);
    if (d < 20 && d < dist) {
      dist = d;
      best = region;
    }
  }
  return best;
}

function refresh() {
  if (state.modifiers.crt) document.body.style.filter = 'contrast(1.05) saturate(1.1)';
  else document.body.style.filter = 'none';

  renderAll(state, els);
  saveGame(state);
}
