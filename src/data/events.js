export const EVENT_POOL = [
  { id: 'fever', name: 'Fever Spike', chance: 0.12, text: 'Core temperature rises; high-clearance tissues become harsher.', apply: (s) => { s.modifiers.clearanceGlobal += 1; s.log.push('Fever raises global clearance this turn.'); } },
  { id: 'injury', name: 'Tissue Injury', chance: 0.09, text: 'A minor tissue injury opens a temporary breach route.', apply: (s) => { s.modifiers.breachOpen = 2; s.log.push('Wounded Skin gateway gains easier access for 2 turns.'); } },
  { id: 'microbiome-shift', name: 'Microbiome Disruption', chance: 0.07, text: 'Competing microbes are disrupted in lower gut.', apply: (s) => { const r = s.regions['large-intestine']; r.biomass += 2; s.log.push('Large Intestine competition reduced: +2 biomass there.'); } },
  { id: 'treatment-pressure', name: 'Medical Pressure', chance: 0.1, text: 'A generalized treatment course applies class-specific pressure.', apply: (s) => { s.modifiers.treatmentPressure += 2; s.log.push('General treatment pressure increases immune damage this turn.'); } },
  { id: 'immunocompromised-window', name: 'Immunocompromised Window', chance: 0.06, text: 'Host immunity dips temporarily.', apply: (s) => { s.modifiers.immuneGlobal -= 2; s.log.push('Immune intensity reduced this turn.'); } },
  { id: 'barrier-healing', name: 'Barrier Healing', chance: 0.08, text: 'Epithelial repair tightens invasion routes.', apply: (s) => { s.modifiers.breachOpen = 0; s.log.push('Barrier healing closes breach benefits.'); } }
];
