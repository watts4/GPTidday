# Pathogen Dominion

A static, browser-based turn-based strategy game inspired by classic empire builders, reimagined as within-host pathogen ecology.

## MVP Features
- Main menu with 6 asymmetric pathogen archetypes.
- Turn-based body-map strategy with anatomical adjacency and route-constrained spread.
- Tissue-aware colonization (barrier, clearance, immune pressure, pH context).
- Adaptation tree with explicit tradeoffs.
- Layered immune-system opposition and random host/intervention events.
- Win/loss conditions balancing domination vs host viability.
- Save/load in `localStorage` and JSON export/import.
- In-game codex and settings (difficulty + scanline/CRT toggles).

## Project Structure

```text
.
├── assets/
│   ├── faction-icons-placeholder.svg
│   └── tile-atlas-placeholder.svg
├── docs/
│   ├── project-plan.md
│   └── scientific-notes.md
├── src/
│   ├── data/
│   │   ├── adaptations.js
│   │   ├── events.js
│   │   ├── factions.js
│   │   └── regions.js
│   ├── game/
│   │   ├── mechanics.js
│   │   ├── state.js
│   │   └── storage.js
│   ├── ui/
│   │   ├── dialogs.js
│   │   └── render.js
│   └── main.js
├── styles/
│   └── main.css
└── index.html
```

## Run Locally
Any static server works.

```bash
python3 -m http.server 8080
# then open http://localhost:8080
```

## GitHub Pages Deployment
1. Push repository to GitHub.
2. In repo settings, open **Pages**.
3. Set source to **Deploy from a branch**.
4. Pick branch (`main` or your release branch) and root folder (`/`).
5. Save. GitHub Pages serves `index.html` as a static site.

No backend or runtime Node dependencies required.

## Controls
- **Click region**: inspect region.
- **Shift+Click adjacent region**: attempt colonization spread from current selected region.
- **End Turn**: process economy, immune response, events, and victory/loss checks.

## Content & Safety Notes
- Science is presented as high-level host-pathogen ecology.
- No laboratory protocols or actionable engineering content is included.
- Endgame domination is fictionalized for strategy gameplay.
