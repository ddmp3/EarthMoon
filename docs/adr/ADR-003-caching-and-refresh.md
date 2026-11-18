# ADR-003 Caching, refresh and custom criteria

Status: proposed (T30), for gate G3. Implements David's decision 6.3.

## Decision
1. **Preset scenarios** (A to D, with their environments) are precomputed and served as static files (tiles and zone JSON). They are refreshed **automatically** when a source changes, recomputing only what changed (ADR-009). `tools/discovery/refresh.sh <scenario>` stays available to force a rebuild.
2. **Custom criteria** (a user picks parameters, an environment and thresholds) are computed **on demand over the precomputed feature cube**. A request never fetches an external source.
3. **A new version of a source** is detected and ingested by the `refresher` (ADR-009), never during a request. It creates a new data version with new hashes. **A brand-new source** still needs a catalogue entry and a task.

## The trade-off, for David
- **What you gain:** every number shown can be reproduced exactly from a release id, and two users asking the same question get the same answer. Requests are fast (seconds), cost nothing in external API calls, and do not fail when NASA or ESA servers are down. That is the guarantee v2 already gave ("no network call when scoring").
- **What you give up:** a custom query can only use parameters already in the cube. A user cannot ask for a brand-new dataset live. New versions of existing sources arrive automatically, minutes to hours after the check that detects them (ADR-009).
- **Mitigation:** the custom query form lists exactly which parameters and data versions are available, with their dates. Missing ones are shown as "not in this release", never as zero.

## Limits of a custom query
- Area: at most 1,000,000 cells of 5 km (about a sixth of global land).
- Time: at most 30 s.
- Input: validated strictly. Only parameters of `data/parameters.yaml` with decision `keep` or `context`, profiles that exist, and thresholds inside their stated ranges.
- Results carry the same release id, provenance and four states as the presets.
