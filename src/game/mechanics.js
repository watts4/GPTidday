import { EVENT_POOL } from '../data/events.js';

export function attemptSpread(state, fromId, toId) {
  const from = state.regions[fromId];
  const to = state.regions[toId];
  if (!from?.controlled || !to || to.controlled) return 'Invalid spread target.';
  if (!from.links.includes(toId)) return 'Not anatomically adjacent.';

  const hasRoute = from.routes.some((route) => {
    if (route === 'epithelial_breach' && state.modifiers.breachOpen > 0) return true;
    return state.faction.spreadRoutes.includes(route) || state.researched.some((a) => a.effects?.unlockRoutes?.includes(route));
  });
  if (!hasRoute) return 'No viable dissemination route.';

  let score = 8 + state.resources.access + state.resources.replication;
  score -= to.barrier + to.immune + Math.max(0, to.clearance + state.modifiers.clearanceGlobal - state.resources.reservoir / 2);
  if (to.pH.includes('acidic') && !state.researched.find((a) => a.id === 'acid-tolerance')) score -= 2;
  if (state.researched.find((a) => a.id === 'broad-tropism')) score += 2;

  const roll = Math.floor(Math.random() * 12) + 1;
  if (roll + score >= 12) {
    to.controlled = true;
    to.biomass = 3 + Math.floor(state.resources.replication / 2);
    state.resources.biomass += 2;
    state.resources.immuneAttention += 1.2;
    state.resources.inflammation += to.symptom * 0.4;
    state.log.unshift(`Spread success: ${from.name} -> ${to.name}.`);
    return null;
  }

  state.resources.biomass = Math.max(0, state.resources.biomass - 1);
  state.resources.immuneAttention += 0.8;
  state.log.unshift(`Spread failed toward ${to.name}.`);
  return 'Colonization repelled.';
}

export function researchAdaptation(state, adaptation) {
  if (state.researched.some((a) => a.id === adaptation.id)) return 'Already adapted.';
  if (state.resources.diversity < adaptation.cost) return 'Not enough genetic diversity.';
  state.resources.diversity -= adaptation.cost;
  state.researched.push(adaptation);
  applyAdaptationImmediate(state, adaptation);
  state.log.unshift(`Adaptation acquired: ${adaptation.name}.`);
  return null;
}

function applyAdaptationImmediate(state, adaptation) {
  const e = adaptation.effects || {};
  state.resources.stealth += e.stealth || 0;
  state.resources.reservoir += e.persistence || 0;
  state.resources.replication += e.replication || 0;
}

export function processTurn(state) {
  state.turn += 1;
  applyEconomy(state);
  immuneResponse(state);
  rollEvent(state);
  applyTradeoffs(state);
  checkOutcome(state);
  normalize(state);

  state.modifiers.clearanceGlobal = 0;
  state.modifiers.immuneGlobal = 0;
  state.modifiers.treatmentPressure = 0;
  state.modifiers.breachOpen = Math.max(0, state.modifiers.breachOpen - 1);
}

function applyEconomy(state) {
  const controlled = Object.values(state.regions).filter((r) => r.controlled);
  state.regionControlCount = controlled.length;
  const nutrientGain = controlled.reduce((sum, r) => sum + r.nutrients, 0) / 7;
  const clearanceTax = controlled.reduce((sum, r) => sum + r.clearance, 0) / 14;

  state.resources.biomass += Math.max(0, state.resources.replication + nutrientGain - clearanceTax);
  state.resources.diversity += 2 + controlled.length * 0.25 + (state.faction.id === 'enveloped-rna-virus' ? 1 : 0);
  state.resources.damage += controlled.reduce((sum, r) => sum + r.symptom, 0) / 20;
  state.resources.viability -= Math.max(0.2, state.resources.damage / 11 + state.resources.inflammation / 16 + state.faction.profile.viabilityPressure / 12);
}

function immuneResponse(state) {
  const diffMod = { easy: -1.5, normal: 0, hard: 1.6 }[state.difficulty] ?? 0;
  const attention = state.resources.immuneAttention + state.modifiers.immuneGlobal + diffMod;
  const pressure = Math.max(1, attention + state.modifiers.treatmentPressure - state.resources.stealth / 2);

  for (const region of Object.values(state.regions)) {
    if (!region.controlled) continue;
    const hit = Math.max(0, pressure + region.immune - state.resources.reservoir / 2 - (state.researched.find((a) => a.id === 'oxidative-shield') ? 2 : 0));
    region.biomass -= Math.max(0, Math.floor(hit / 4));
    if (region.biomass <= 0) {
      region.controlled = false;
      region.biomass = 0;
      state.log.unshift(`Immune clearance removed colony in ${region.name}.`);
    }
  }

  state.resources.immuneAttention = Math.max(2, state.resources.immuneAttention * 0.88 + state.resources.damage * 0.2 + state.regionControlCount * 0.15);
  state.resources.inflammation = Math.max(0, state.resources.inflammation * 0.9 + state.resources.damage * 0.22);
}

function rollEvent(state) {
  for (const event of EVENT_POOL) {
    if (Math.random() < event.chance) {
      event.apply(state);
      state.log.unshift(`Event: ${event.name} — ${event.text}`);
      break;
    }
  }
}

function applyTradeoffs(state) {
  for (const adaptation of state.researched) {
    const text = adaptation.tradeoff || '';
    if (text.includes('immune attention')) state.resources.immuneAttention += 0.4;
    if (text.includes('viability pressure')) state.resources.viability -= 0.8;
    if (text.includes('replication while active') && state.flags.dormantMode) state.resources.replication = Math.max(1, state.resources.replication - 2);
    if (text.includes('inflammation')) state.resources.inflammation += 0.5;
  }
}

function checkOutcome(state) {
  if (state.regionControlCount === 0 || state.resources.biomass <= 0) {
    state.outcome = { type: 'loss', text: 'Eradication: immune forces eliminated your core colonies.' };
  } else if (state.resources.viability <= 0 && state.regionControlCount < 9) {
    state.outcome = { type: 'loss', text: 'Pyrrhic failure: host collapsed before strategic domination.' };
  } else if (state.regionControlCount >= 14 && state.resources.viability > 18) {
    state.outcome = { type: 'win', text: 'Total Host Dominion achieved.' };
  } else if (state.turn >= 60 && state.regionControlCount >= 10 && state.resources.stealth >= 6) {
    state.outcome = { type: 'win', text: 'Silent Mastery: chronic multi-system persistence secured.' };
  }
}

function normalize(state) {
  for (const key of Object.keys(state.resources)) {
    state.resources[key] = Math.round(state.resources[key] * 10) / 10;
  }
  state.log = state.log.slice(0, 50);
}
