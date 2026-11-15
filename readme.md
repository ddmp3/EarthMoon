# 🛰️ Lunar Twins on Earth

**NASA Space Apps Challenge 2026 · Cyber&Space Montréal** · Challenge: [Permanent Moon Base Locations and Mars](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)

A web application that ranks Earth sites as analogs of the **lunar south pole** for a chosen mission: rover mobility testing, instrument calibration, a self-sufficient colony, or free criteria. Each site is scored criterion by criterion with open data (NASA POWER, MODIS, Copernicus DEM, USGS, Smithsonian GVP) against lunar reference values (LRO LOLA slope and roughness computed with the same 1 km method as on Earth, LRO Diviner).

Every site card shows what matches, what does not, the lunar value next to the Earth value, the source of each number, and what Earth cannot reproduce (gravity, vacuum, radiation).

**Live:** https://jolly-rock-05f5cb20f.3.azurestaticapps.net · **API docs:** https://ca-api-rtzkc5ya.bluesky-19c5e80c.canadacentral.azurecontainerapps.io/api/docs

![Home](docs/screenshots/01-home.jpg)
![Colony mission, Tunnunik Crater](docs/screenshots/02-mission-colony-tunnunik.jpg)

## The four modes

| Mode | Question it answers |
|---|---|
| **Robotics validation** | Where on Earth can a rover's mobility be tested before it goes to a lunar site? |
| **Instrument calibration** | Where can drills, wind, gas, seismic and thermal instruments be calibrated in near-lunar conditions? |
| **Self-sufficient colony** | Which sites reproduce the conditions that make a lunar site favorable to a self-sufficient base (water, energy, terrain, shelter)? |
| **Free criteria** | You choose the parameters, their intervals and their weights (only parameters our sources provide). |

Criteria and their justifications: [docs/scenarios.md](docs/scenarios.md).

## How it works

- **Scoring:** each criterion has a target interval, a tolerance and a weight. Score 1 inside the interval, linear decrease to 0 at the tolerance limit; site score is the weighted mean out of 100. A criterion with no data is excluded and shown as missing, never invented. Vegetated sites (MODIS NDVI > 0.2) are ranked last.
- **Candidates:** 37 sites: 9 known analogs, 1 negative control (Amazon) and 27 understudied sites in cold, arid or volcanic regions. Goal: not only rediscover known analogs but surface understudied ones.
- **Data:** NASA POWER, USGS and Smithsonian GVP are read live by the API; terrain (Copernicus DEM) and MODIS values are precomputed offline in `tools/precompute/`. No database, no account, no secret.
- **Lunar reference:** `data/reference/moon-south-pole.json`, with slope and roughness computed from LRO LOLA over 71,731 windows of 1 km south of 85°S.

Sources and attributions: [docs/sources.md](docs/sources.md), or `GET /api/sources`.

## Validation

Known analogs are expected in the top half of the modes they are actually used for; the Amazon control must be excluded or last. **9 of 11 expectations are met** (threshold 75%), and the Amazon is excluded in every mode. The two misses are explained by the data (Holuhraun is flat at 1 km scale, Svalbard air is humid). Method, results and limits: [docs/validation.md](docs/validation.md).

## Limits of the analogy

Earth cannot reproduce lunar gravity, vacuum, absence of wind or radiation, and no site approaches the cold of permanently shadowed craters; temperature criteria are proxies. Every site card says what the analogy does not cover. Biology and habitability are out of scope.

## Run it

```bash
docker compose up --build        # front end http://localhost:8080, API http://localhost:3001/api/docs
python3 tools/validation/e2e.py  # end-to-end tests against the running app
```

Stack: React, TypeScript, Vite, Tailwind, Leaflet · Node.js, TypeScript, Express, OpenAPI · Python (precompute, validation) · Docker, Terraform, Azure (Static Web App, Container Apps). Details: [docs/architecture.md](docs/architecture.md).

## Use of AI

The team defined the mission modes and the validation approach. Parts of the code, data processing scripts, tests and documentation were written with the help of Claude (Anthropic) and Microsoft Copilot, under the team's direction; commits made with Claude carry a `Co-Authored-By: Claude` trailer. No image, video or audio was generated with AI.

## Team

Cyber&Space Montréal: François, Jesus, Wassim, Yann, Xavier, David.
