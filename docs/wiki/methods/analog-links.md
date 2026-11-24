# Analog links and place names (T45c part 2, 24/11/2026)

## What the globe shows
**Beside the Earth map, each mission shows the Moon or Mars as a globe:**
- **Texture:**
  - Moon: the LROC WAC colour mosaic of NASA's Scientific Visualization Studio.
  - Mars: our shaded rendering of MOLA elevation (`tools/discovery/globe_texture.py`). It is not true colours: no verified whole-Mars colour map was found.
- **Dots:** the faint ones are windows of the target environment, a seeded sample of at most 4,000.
- **Drawing:** a 2D canvas, with no 3D library, to keep within the JavaScript budget of ADR-006.

## The link between the two globes (David's choice: "windows of the same slope")
Our method compares an Earth zone with the **distribution** of an environment, never with one planetary place. So no planetary "twin" of a zone exists in the data. The link shown is the one the data support:
- **Earth zone → planet:** the windows of the zone's target whose slope percentile, in the target's own distribution, is within **2.5 points** of the zone's median slope percentile.
  - The zone's median slope is taken over its windows with less than half of their ground hidden.
- **Planet point → Earth:** the nearest stored window, then the linked Earth zones whose percentile is within the same band, best typicality first (at most 20).
- **Only the best zones of each target are linked:** 60 per target. That is 420 lunar and 180 Martian zones for the current releases. 7 Mars zones have no unmasked window, and say so.

## Names
- **Earth:**
  - **Source:** [OpenStreetMap Nominatim](https://operations.osmfoundation.org/policies/nominatim/), queried once per place when a release is annotated.
  - **Usage policy:** at most 1 request per second, one thread, an application User-Agent, results cached (`earthmoon-data/names/`), never queried twice. Bulk geocoding is discouraged, so only the best zones are named; the others keep their coordinates.
  - **Licence:** names © OpenStreetMap contributors, ODbL. The annotations file is shared under the ODbL.
- **Moon and Mars:**
  - **Source:** the [IAU Gazetteer of Planetary Nomenclature](https://planetarynames.wr.usgs.gov/) (USGS, public domain per its metadata).
  - **Rule:** a window takes the smallest named feature whose extent holds it, else "near the nearest feature (distance)".
  - **Lunar pits:** they keep the names of the LROC atlas.
- **Coordinates stay** in every record and panel.

## Files and routes
- **Annotations:** `python -m discovery.analogs --release <id> --body moon|mars ...` writes `releases/annotations/<id>.json`, beside the release. Names do not change any result.
- **API:**
  - `GET /api/v3/analogs/target`;
  - `/analogs/zone/{id}`;
  - `/analogs/point`;
  - zones carry `place` and `slope_median`.
- **Checks:**
  - the polar window longitudes follow the LOLA convention, checked against Shackleton and Shoemaker (their floors fall at the windows);
  - end-to-end test TF-19 and the browser audit cover the link both ways.
