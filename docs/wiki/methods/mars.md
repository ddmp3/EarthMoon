# Mars, first phase (T48, proposal E19)

**Status: proposal, waiting for David's decisions. Nothing is computed before.**

Mars is analysed on its own terms (mission rule): no lunar criterion is reused with new weights.

## Phase 1: what reaches the website first
Four environments of the T20 specs, all built from verified global data:

| Environment | Martian data | Earth comparison | Validation |
|---|---|---|---|
| North polar terrain | MOLA polar grid, 512 pixels per degree (about 115 m) | slope, frozen ground (as classes), aridity | negatives only |
| South polar terrain | same | same | negatives only |
| Ice-rich mid-latitudes | MOLA 128 pixels per degree (about 460 m), inside SWIM ice consistency (3 km) | slope; Martian ice against Earth permafrost, as classes (proxy, scenario D) | negatives only |
| Volcanic plains | MOLA 128 pixels per degree, inside the volcanic units of the Mars geologic map (Tanaka et al. 2014) | slope; geology: Martian volcanic units against Earth basalt (Macrostrat) | **positive controls exist**: Big Craters, Mauna Ulu, Kīlauea Iki, Kīlauea caldera (R29) |

Later, through the data improvement backlog:
- aqueous mineral sites (OMEGA, CRISM; site sets);
- HiRISE rover-scale terrain (1,377 DTMs, large);
- thermal inertia (THEMIS, not verified);
- atmosphere (Mars Climate Database, registration).

## Decisions for David
1. **E19: window size on Mars.** The Moon uses 1 km windows at 40 m (25 × 25 pixels). MOLA pixels are 115 to 460 m, so a 1 km window holds 2 to 9 pixels and its slope means little. Proposal: keep **25 × 25 pixels of the planetary grid**, which gives windows of 2.9 km at the poles and 11.6 km at 128 pixels per degree. Earth is resampled to the same pixel and window. The 5 km cells keep their size; a window larger than a cell is assigned to the cell that holds its centre.
2. **E20: Martian volcanic units against Earth.** Volcanic units of the Tanaka map count as a match with Earth basalt, and other volcanic rocks as partial. This mirrors E17 and is to be reviewed by a Mars geologist.
3. **Interface.** Option A: a fifth mission card, "Mars", with the same screens as the lunar missions. Option B: a Moon/Mars switch in the top bar that changes the missions. Proposal: **A**, simpler and clearer for experts. The "Mars: next phase" chip on the home page becomes the entry.

## Data improvements to add to the backlog
- MOLA-HRSC blended global DEM at 200 m: finer than MOLA at mid-latitudes; not verified yet.
- HRSC DTMs at 50 m: strips, not global.
- HiRISE DTMs at 1 to 2 m: rover scale, 1,377 sites.
- THEMIS thermal inertia: not verified.
- Mars Climate Database: free registration by email.
