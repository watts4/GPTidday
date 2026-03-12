import { REGIONS } from '../data/regions.js';

export function createInitialState(faction, difficulty = 'normal') {
  const startRegion = chooseStartRegion(faction);
  const regions = Object.fromEntries(
    REGIONS.map((r) => [r.id, { ...r, controlled: r.id === startRegion, biomass: r.id === startRegion ? 8 : 0, fortress: false }])
  );

  return {
    title: 'Pathogen Dominion',
    turn: 1,
    difficulty,
    faction,
    selectedRegionId: startRegion,
    resources: {
      biomass: 8,
      replication: faction.profile.replication,
      diversity: faction.profile.diversity,
      stealth: faction.profile.stealth,
      access: 1,
      damage: faction.profile.damage,
      inflammation: 3,
      reservoir: faction.profile.persistence,
      immuneAttention: 4,
      viability: 88
    },
    researched: [],
    regionControlCount: 1,
    regions,
    log: ['Infection established. Grow, adapt, and evade.'],
    modifiers: {
      clearanceGlobal: 0,
      immuneGlobal: 0,
      treatmentPressure: 0,
      breachOpen: 0,
      crt: false,
      scanlines: false
    },
    flags: {
      dormantMode: false
    },
    outcome: null
  };
}

function chooseStartRegion(faction) {
  const map = {
    'extracellular-bacterium': 'wound',
    'intracellular-bacterium': 'deep-lung',
    'enveloped-rna-virus': 'nasal',
    'non-enveloped-virus': 'mouth',
    'fungal-pathogen': 'wound',
    'protozoan-parasite': 'blood'
  };
  return map[faction.id] || 'nasal';
}
