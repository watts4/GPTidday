# Project Plan

## Architecture Overview
- `src/data`: data-driven definitions for factions, body regions, adaptations, and events.
- `src/game`: state creation, turn simulation, spread resolution, immune AI, save/load.
- `src/ui`: canvas rendering and modal/dialog orchestration.
- `styles`: retro pixel-inspired SNES UI chrome.
- `docs`: scientific mapping notes and planning artifacts.

## Core Data Model
- `GameState`: turn index, faction, resources, map regions, research inventory, event log, difficulty/modifiers, outcome.
- `RegionState`: static tissue properties + dynamic control/biomass.
- `FactionDefinition`: baseline biology profile, route permissions, strengths/weaknesses.
- `Adaptation`: costed mutation card with effects and explicit tradeoff text.
- `Event`: probabilistic host/treatment context shifts applied each turn.

## Implementation Phases
1. Foundation and static layout (menu, map, side panels, dialogs).
2. Data modules (regions/factions/adaptations/events).
3. Core loop (spread actions, turn processing, immune response, victory/loss).
4. Persistence (localStorage + import/export JSON).
5. Codex and science notes.
6. Polish pass (retro styling, UX text, balancing defaults).
