# 🛰️ EarthMoon: Earth analogs of the Moon and Mars

**NASA Space Apps Challenge 2026 · Cyber&Space Montréal** · Challenge: [Permanent Moon Base Locations and Mars](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)

This repository continues the hackathon project to address the limits found during the 48-hour challenge.
- **The original repository is frozen** for the jury and must not be changed: https://github.com/ddmp3/nasa-space-app-challenge-2026-cyber-space
- **The live sites are frozen too, and still serve v1:**
  - site: https://jolly-rock-05f5cb20f.3.azurestaticapps.net
  - API docs: https://ca-api-rtzkc5ya.bluesky-19c5e80c.canadacentral.azurecontainerapps.io/api/docs

![Home](docs/screenshots/01-home.jpg)

## What it does (v3)
It **discovers** places on Earth whose terrain resembles a lunar or Martian environment, everywhere on land, and states the limits.
- **Moon:** polar lit highlands, permanently shadowed regions, pits, mare plains, the south polar cap. These serve scenarios A (permanent base) and B (robotic exploration).
- **Mars:** ice-rich mid-latitudes, north and south polar terrain. These serve scenario D.
- **How it compares:** the Earth DEM is resampled to the planetary pixel, and each 5 km cell gets the typicality of its slopes in the target distribution. Missing or hidden ground is shown as such, never as a bad value.
- **Beside slope** it shows geology, frozen ground and aridity, as context only.
- **Every release is frozen and reproducible,** with the provenance of every Earth tile.

It is a **screening tool**: "worth a closer look", not "an analog". No scenario has a positive validation yet.

**v3 in numbers** ([docs/VALIDATION.md](docs/VALIDATION.md)):
- 6.3 M lunar and 7.4 M Mars cells assessed;
- evaluation grid 30/39 (v1 15/39, v2 28/39), plus 13/15 on the five v3 criteria;
- 0 of 4 scenarios with a positive validation;
- 16 sources, each with its provenance and its refresh check.

## Documentation

| Page | Content |
|---|---|
| [docs/METHOD.md](docs/METHOD.md) | How the comparison works, and why |
| [docs/DATA.md](docs/DATA.md) | Sources, licences, provenance |
| [docs/SCENARIOS.md](docs/SCENARIOS.md) | Scenarios A to D: targets, requirements, what cannot be assessed |
| [docs/VALIDATION.md](docs/VALIDATION.md) | What was checked and the results, unfavourable first |
| [docs/LIMITS.md](docs/LIMITS.md) | What results do not mean; decisions that need experts |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, isolation, quality gate |
| [docs/REFERENCES.md](docs/REFERENCES.md) | Scientific references and their verification status |
| [docs/plan/README.md](docs/plan/README.md) | Plan and status of every task; [revisions after the delivery](docs/plan/revisions.md) |
| [docs/wiki/](docs/wiki/README.md) | Run reports, methods, inventories (mirrored to the GitHub wiki) |
| [CHANGELOG.md](CHANGELOG.md) | Every task, with its measured effect |

## Run it locally

```bash
docker compose up --build        # synthetic test releases; front end http://localhost:8080, API http://localhost:3001/api/docs
EARTHMOON_RELEASES=<path to earthmoon-data/releases> docker compose up --build    # real releases
tools/check.sh all               # every test, dependency audit, end-to-end and browser audit (Docker only)
```

Stack: React, TypeScript, Vite, Leaflet · Node.js, Express, OpenAPI · Python (pyarrow, numpy, rasterio, FastAPI) · Docker. The Azure deployment is frozen during the NASA evaluation.

## Use of AI
The team defined the missions and the validation approach. Parts of the code, data processing, tests and documentation were written with the help of Claude (Anthropic) and Microsoft Copilot, under the team's direction. Commits made with Claude carry a `Co-Authored-By: Claude` trailer. No image, video or audio was generated with AI.

## Team
Cyber&Space Montréal: François, Jesus, Wassim, Yann, Xavier, David.
