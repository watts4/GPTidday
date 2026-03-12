import { ADAPTATIONS } from '../data/adaptations.js';

export function renderAll(state, els) {
  renderMap(state, els.mapCanvas);
  renderHostPanel(state, els.hostPanel);
  renderFactionPanel(state, els.factionPanel);
  renderRegionPanel(state, els.regionPanel);
  renderResearchPanel(state, els.researchPanel, els.onResearch);
  renderLog(state, els.logPanel);
}

function renderMap(state, canvas) {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#10122f';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = '#384089';
  for (const region of Object.values(state.regions)) {
    for (const targetId of region.links) {
      const t = state.regions[targetId];
      if (!t) continue;
      ctx.beginPath();
      ctx.moveTo(region.x, region.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    }
  }

  for (const region of Object.values(state.regions)) {
    const selected = state.selectedRegionId === region.id;
    ctx.fillStyle = region.controlled ? '#74ff9c' : '#7082c9';
    if (selected) ctx.fillStyle = '#ffd166';
    ctx.fillRect(region.x - 8, region.y - 8, 16, 16);
    ctx.fillStyle = '#f6f7ff';
    ctx.font = '10px monospace';
    ctx.fillText(region.name, region.x + 10, region.y + 3);
    if (region.controlled) {
      ctx.fillStyle = '#0f1028';
      ctx.fillText(String(Math.floor(region.biomass)), region.x - 4, region.y + 3);
    }
  }

  if (state.modifiers.scanlines) {
    ctx.strokeStyle = 'rgba(0,0,0,0.25)';
    for (let y = 0; y < canvas.height; y += 4) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }
}

function renderHostPanel(state, el) {
  const r = state.resources;
  el.innerHTML = `<h3>Host Status</h3><div class="stat-grid">
    <div>Turn</div><div>${state.turn}</div>
    <div>Host Viability</div><div class="${r.viability < 25 ? 'danger' : ''}">${r.viability}</div>
    <div>Immune Attention</div><div>${r.immuneAttention}</div>
    <div>Inflammation</div><div>${r.inflammation}</div>
    <div>Damage Burden</div><div>${r.damage}</div>
    <div>Controlled Regions</div><div>${state.regionControlCount}</div>
  </div>`;
}

function renderFactionPanel(state, el) {
  const r = state.resources;
  el.innerHTML = `<h3>${state.faction.name}</h3>
    <div class="small">${state.faction.type}</div>
    <div class="small">${state.faction.inspiration}</div>
    <div class="stat-grid" style="margin-top:6px;">
      <div>Biomass</div><div>${r.biomass}</div>
      <div>Replication</div><div>${r.replication}</div>
      <div>Diversity</div><div>${r.diversity}</div>
      <div>Stealth</div><div>${r.stealth}</div>
      <div>Reservoir Stability</div><div>${r.reservoir}</div>
      <div>Access</div><div>${r.access}</div>
    </div>`;
}

function renderRegionPanel(state, el) {
  const region = state.regions[state.selectedRegionId];
  if (!region) return;
  el.innerHTML = `<h3>Region Intel: ${region.name}</h3>
    <div class="small">${region.system}</div>
    <div class="stat-grid">
      <div>Barrier</div><div>${region.barrier}</div>
      <div>Immune Pressure</div><div>${region.immune}</div>
      <div>Clearance</div><div>${region.clearance}</div>
      <div>Nutrients</div><div>${region.nutrients}</div>
      <div>pH</div><div>${region.pH}</div>
      <div>Routes</div><div>${region.routes.join(', ')}</div>
      <div>Status</div><div>${region.controlled ? 'Controlled' : 'Uncontrolled'}</div>
    </div>`;
}

function renderResearchPanel(state, el, onResearch) {
  const available = ADAPTATIONS.filter((a) => !state.researched.some((r) => r.id === a.id));
  el.innerHTML = '<h3>Adaptation Tree</h3>';
  for (const a of available.slice(0, 5)) {
    const node = document.createElement('div');
    node.className = 'research-item';
    const canBuy = state.resources.diversity >= a.cost;
    node.innerHTML = `<strong>${a.name}</strong> <span class="small">(${a.category})</span>
      <div class="small">${a.description}</div>
      <div class="small warn">Tradeoff: ${a.tradeoff}</div>
      <div class="small">Cost: ${a.cost} diversity</div>`;
    const btn = document.createElement('button');
    btn.textContent = canBuy ? 'Mutate' : 'Insufficient Diversity';
    btn.disabled = !canBuy;
    btn.onclick = () => onResearch(a);
    node.appendChild(btn);
    el.appendChild(node);
  }
}

function renderLog(state, el) {
  el.innerHTML = '<h3>Event Feed</h3>';
  const list = document.createElement('ul');
  list.className = 'log-list';
  for (const item of state.log.slice(0, 10)) {
    const li = document.createElement('li');
    li.textContent = item;
    list.appendChild(li);
  }
  el.appendChild(list);
}
