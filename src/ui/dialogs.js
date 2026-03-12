import { FACTIONS } from '../data/factions.js';
import { REGIONS } from '../data/regions.js';
import { ADAPTATIONS } from '../data/adaptations.js';

export function openNewGameDialog(dialog, onStart) {
  dialog.innerHTML = `<h2>Choose Pathogen Archetype</h2>
    <p class="small">Each faction has asymmetrical biology, spread routes, and immune dynamics.</p>
    <div class="faction-grid"></div>
    <button id="closeMenu">Close</button>`;

  const grid = dialog.querySelector('.faction-grid');
  for (const f of FACTIONS) {
    const card = document.createElement('article');
    card.className = 'faction-card';
    card.innerHTML = `<h4>${f.name}</h4>
      <div class="small">${f.type}</div>
      <div class="small">${f.inspiration}</div>
      <div class="small"><strong>Strengths:</strong> ${f.strengths.join('; ')}</div>
      <div class="small"><strong>Weaknesses:</strong> ${f.weaknesses.join('; ')}</div>
      <div class="small"><strong>Win style:</strong> ${f.winStyle}</div>`;
    const btn = document.createElement('button');
    btn.textContent = 'Begin Infection';
    btn.onclick = () => onStart(f);
    card.appendChild(btn);
    grid.appendChild(card);
  }

  dialog.querySelector('#closeMenu').onclick = () => dialog.close();
  dialog.showModal();
}

export function openCodexDialog(dialog) {
  dialog.innerHTML = `<h2>Host-Pathogen Codex</h2>
  <h3>Immune Model</h3><p class="small">Innate pressure scales with immune attention and tissue surveillance. Adaptive targeting rises as visibility and damage climb.</p>
  <h3>Victory Conditions</h3><p class="small">Total Dominion: 14+ regions while host viability remains above collapse threshold. Silent Mastery: stable chronic spread with high stealth.</p>
  <h3>Faction Roster</h3>${FACTIONS.map((f) => `<p class="small"><strong>${f.name}:</strong> ${f.type}. Preferred tissues: ${f.preferredTissues.join(', ')}.</p>`).join('')}
  <h3>Body Regions</h3><p class="small">${REGIONS.map((r) => r.name).join(', ')}.</p>
  <h3>Adaptation Categories</h3><p class="small">${[...new Set(ADAPTATIONS.map((a) => a.category))].join(', ')}.</p>
  <button id="closeCodex">Close</button>`;

  dialog.querySelector('#closeCodex').onclick = () => dialog.close();
  dialog.showModal();
}

export function openSettingsDialog(dialog, state, onApply) {
  dialog.innerHTML = `<h2>Settings</h2>
    <label class="small">Difficulty
      <select id="difficultySel">
        <option value="easy" ${state.difficulty === 'easy' ? 'selected' : ''}>Easy</option>
        <option value="normal" ${state.difficulty === 'normal' ? 'selected' : ''}>Normal</option>
        <option value="hard" ${state.difficulty === 'hard' ? 'selected' : ''}>Hard</option>
      </select>
    </label>
    <label class="small"><input type="checkbox" id="scanlines" ${state.modifiers.scanlines ? 'checked' : ''}/> Scanlines overlay</label>
    <label class="small"><input type="checkbox" id="crt" ${state.modifiers.crt ? 'checked' : ''}/> CRT bloom tint</label>
    <div><button id="applySet">Apply</button> <button id="closeSet">Close</button></div>`;

  dialog.querySelector('#applySet').onclick = () => {
    onApply({
      difficulty: dialog.querySelector('#difficultySel').value,
      scanlines: dialog.querySelector('#scanlines').checked,
      crt: dialog.querySelector('#crt').checked
    });
    dialog.close();
  };
  dialog.querySelector('#closeSet').onclick = () => dialog.close();
  dialog.showModal();
}
