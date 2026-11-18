# 🛰️ Lunar Twins on Earth

**NASA Space Apps Challenge 2026 · Cyber&Space Montréal** · Challenge: [Permanent Moon Base Locations and Mars](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)

Ce repo est un clone du repo https://github.com/ddmp3/nasa-space-app-challenge-2026-cyber-space qui ne doit pas être modifier car en cours d'évaluation par le jury de la nasa.
le repo https://github.com/ddmp3/EarthMoon sert a faire une v2 du projet afin de traiter les limitations rencontrées durant le challenge de 48h.

les sites ci-dessous peuvent être consulté mais non modifié pour les même raisons que ci-dessus (évaluation nasa).

**Live (v1, under NASA evaluation):** https://jolly-rock-05f5cb20f.3.azurestaticapps.net · **API docs:** https://ca-api-rtzkc5ya.bluesky-19c5e80c.canadacentral.azurecontainerapps.io/api/docs

![Home](docs/screenshots/01-home.jpg)

## What it does today (v2)

It ranks 37 Earth sites as analogs of the **lunar south pole** for a chosen mission:
- rover mobility;
- instrument calibration;
- a base;
- your own criteria.

Each criterion says whether it measures similarity to lunar data, an operational requirement or an Earth proxy. Missing data is shown, never scored. Each rank comes with a confidence level.

It is a **screening tool**: "worth a closer look", not "approved test site".

## Where it is going (v3)

From ranking known sites to **discovering** analogs anywhere on Earth, for several lunar and Martian environments. Each dimension (terrain, geology, thermal, ice, operations) is mapped separately, with the uncertainty shown and the regions without data marked. Plan and status: [docs/plan/README.md](docs/plan/README.md). History of changes: [CHANGELOG.md](CHANGELOG.md).

## Documentation

| Page | Content |
|---|---|
| [docs/METHOD.md](docs/METHOD.md) | How scores are computed, and why |
| [docs/DATA.md](docs/DATA.md) | Sources, processing, attributions |
| [docs/VALIDATION.md](docs/VALIDATION.md) | What was checked and the results, including the misses |
| [docs/SCENARIOS.md](docs/SCENARIOS.md) | v3 scenarios: targets, similarity, requirements, limits |
| [docs/LIMITS.md](docs/LIMITS.md) | What results do not mean; decisions that need experts |
| [docs/REFERENCES.md](docs/REFERENCES.md) | Scientific references and their verification status |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, quality gate, infrastructure |
| [docs/wiki/](docs/wiki/README.md) | Long material: full v2 audit, inventories, run reports (mirrored to the GitHub wiki) |

**v2 in numbers:**
- evaluation grid: 15/39 for v1, 28/39 for v2;
- team expectations met: 8/11, below the 75% threshold, not retuned;
- tests: API 154, web 13, Python 56; end-to-end 15/15.

## Run it

```bash
docker compose up --build        # front end http://localhost:8080, API http://localhost:3001/api/docs
tools/check.sh all               # every test, dependency audit, end-to-end and browser audit (Docker only)
```

Stack: React, TypeScript, Vite, Tailwind, Leaflet · Node.js, TypeScript, Express, OpenAPI · Python · Docker. The Terraform and Azure deployment is frozen during the NASA evaluation.

## Use of AI

The team defined the missions and the validation approach. Parts of the code, data processing, tests and documentation were written with the help of Claude (Anthropic) and Microsoft Copilot, under the team's direction. Commits made with Claude carry a `Co-Authored-By: Claude` trailer. No image, video or audio was generated with AI.

## Team

Cyber&Space Montréal: François, Jesus, Wassim, Yann, Xavier, David.
