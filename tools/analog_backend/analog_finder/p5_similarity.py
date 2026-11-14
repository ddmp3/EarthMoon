"""Phase 5 - Normalization against planetary references + Multi-Criteria Similarity Index (MCSI).

KEY DESIGN RULE: Earth and Moon thermal states are not matchable in absolute units (Earth skin T 200-330 K vs PSR
~25-110 K; lunar day/night swings are far larger than terrestrial). So:
  * GEOMETRIC variables (slope, roughness at a matched baseline, shadow fraction) are matched in ABSOLUTE terms using a
    lunar-referenced z-score.
  * THERMAL variables (cold-tail temperature, diurnal amplitude ratio, thermal-inertia proxy) are matched in RELATIVE
    terms: each planet's value becomes its own within-planet quantile, then is compared with the target's quantile position.
Cells with missing features (e.g. SAR/DEM-only RCM cells have no thermal data) are scored on the features they HAVE;
`coverage` reports the weight fraction actually used, and the geometric / thermal sub-scores are exposed separately.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

ABSOLUTE = ["slope_deg", "roughness_m", "shadow_frac"]   # geometry: lunar-referenced z-score
RELATIVE = ["t_p05", "amp_ratio", "ati"]                  # thermal: within-planet quantile (0..1)
FEATURES = ABSOLUTE + RELATIVE
GEOM_IDX = [FEATURES.index(c) for c in ABSOLUTE]
THERM_IDX = [FEATURES.index(c) for c in RELATIVE]

# ILLUSTRATIVE FALLBACK ONLY -- not measured values. The pipeline derives the real target from LRO rasters
# (build_target_from_rasters). Absolute: (mean, std) in raw units. Relative: (mean, std) of quantile position.
LUNAR_SP_TARGET_PLACEHOLDER = {
    "slope_deg": (12.0, 8.0), "roughness_m": (3.0, 2.0), "shadow_frac": (0.50, 0.30),
    "t_p05": (0.05, 0.05), "amp_ratio": (0.30, 0.20), "ati": (0.80, 0.20),
}


# ---------- Reference handling ----------
def build_target_from_rasters(stack: pd.DataFrame, aoi_mask: np.ndarray | None = None) -> dict:
    """Target profile from the table of ALL lunar cells (columns = FEATURES) and a boolean AOI mask
    (e.g. poleward of 85 S). Absolute -> raw (mean, std) inside AOI; relative -> (mean, std) of AOI cells' quantile
    positions within the whole lunar distribution."""
    m = np.ones(len(stack), bool) if aoi_mask is None else np.asarray(aoi_mask, bool)
    t = {}
    for c in ABSOLUTE:
        v = stack.loc[m, c]
        t[c] = (float(v.mean()), float(v.std(ddof=0)) or 1e-9)
    for c in RELATIVE:
        q = stack[c].rank(pct=True)[m]
        t[c] = (float(q.mean()), float(q.std(ddof=0)) or 1e-9)
    return t


class PlanetNormalizer:
    """Maps one planet's cell table to the common comparison space. Fit one instance PER PLANET (relative features use that
    planet's own distribution) but pass the SAME target to both.
      ref_z  : absolute -> (x - mu_ref)/sd_ref ; relative -> (quantile - mu_q)/sd_q      (target = origin)
      minmax : absolute -> independent min-max (1st-99th pct, clipped) ; relative -> quantile (already 0..1)"""

    def __init__(self, target: dict, method: str = "ref_z", z_clip: float = 6.0):
        self.target, self.method, self.z_clip = target, method, z_clip   # z_clip: saturate so one feature cannot dominate

    def fit(self, df: pd.DataFrame):
        self.sorted_ = {c: np.sort(df[c].dropna().values) for c in RELATIVE}
        self.lohi = {c: (df[c].quantile(0.01), df[c].quantile(0.99)) for c in ABSOLUTE}
        return self

    def quantile(self, col: str, x) -> np.ndarray:
        """Within-planet empirical quantile (NaN-safe)."""
        x = np.asarray(x, float)
        s = self.sorted_[col]
        q = np.searchsorted(s, x, side="right") / max(len(s), 1) if len(s) else np.full(x.shape, np.nan)
        return np.where(np.isfinite(x), q, np.nan)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for c in ABSOLUTE:
            if self.method == "minmax":
                lo, hi = self.lohi[c]; out[c] = ((df[c] - lo) / (hi - lo)).clip(0, 1)
            else:
                mu, sd = self.target[c]; out[c] = (df[c] - mu) / sd
        for c in RELATIVE:
            q = self.quantile(c, df[c].values)
            mu, sd = self.target[c]
            out[c] = q if self.method == "minmax" else (q - mu) / sd
        out = out[FEATURES]
        return out.clip(-self.z_clip, self.z_clip) if self.method != "minmax" else out

    def target_vector(self) -> np.ndarray:
        if self.method != "minmax":
            return np.zeros(len(FEATURES))
        v = []
        for c in FEATURES:
            mu = self.target[c][0]
            if c in ABSOLUTE:
                lo, hi = self.lohi[c]; mu = float(np.clip((mu - lo) / (hi - lo), 0, 1))
            v.append(mu)
        return np.array(v)


# ---------- Similarity metrics (NaN-aware: each row uses only its finite features) ----------
def _wdist(Z, t, w, M):
    we = w[None, :] * M
    sw = we.sum(1)
    d = np.sqrt((we * (np.where(M, Z, 0.0) - t) ** 2).sum(1) / np.where(sw > 0, sw, np.nan))
    return d, sw


def _wcos(Z, t, w, M, c):
    s = np.sqrt(w[None, :] * M)
    A = np.where(M, Z - c, 0.0) * s
    B = (t - c)[None, :] * s
    den = np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1)
    return (A * B).sum(1) / np.where(den > 0, den, np.nan)


def weighted_euclidean(Z: np.ndarray, t: np.ndarray, w: np.ndarray) -> np.ndarray:
    return _wdist(Z, t, w / w.sum(), np.isfinite(Z))[0]


def weighted_cosine(Z: np.ndarray, t: np.ndarray, w: np.ndarray, center: np.ndarray | None = None) -> np.ndarray:
    c = np.zeros(Z.shape[1]) if center is None else center
    return _wcos(Z, t, w / w.sum(), np.isfinite(Z), c)


def mcsi(df: pd.DataFrame, norm: PlanetNormalizer, weights: dict[str, float] | None = None, alpha: float = 0.7,
         tau: float | None = None, hard_limits: dict[str, tuple[float, float]] | None = None,
         min_features: int = 3) -> pd.DataFrame:
    """Multi-Criteria Similarity Index in [0,1]:
        MCSI = alpha * exp(-d_w / tau)  +  (1 - alpha) * (cos_w + 1) / 2
    d_w   weighted Euclidean distance to the target (magnitude match);  cos_w weighted cosine vs pooled mean (profile match).
    tau=None -> median(d_w) of the input; for Earth-vs-Moon comparisons pass ONE numeric tau (e.g. the lunar median) to both.
    Returns columns: d_w, cos_w, mcsi, coverage, geometry_match, thermal_match (sub-scores = exp(-d_sub/tau)).
    hard_limits: feasibility gates in RAW units, e.g. {'slope_deg': (0, 20)} -> outside = MCSI 0."""
    w = np.array([(weights or {}).get(c, 1.0) for c in FEATURES], float)
    Z = norm.transform(df[FEATURES]).values
    M = np.isfinite(Z)
    t = norm.target_vector()
    with np.errstate(all="ignore"):
        d, sw = _wdist(Z, t, w, M)
        c = np.nanmean(np.where(M, Z, np.nan), axis=0)
        c = np.where(np.isfinite(c), c, 0.0)
        cs = _wcos(Z, t + 1e-3, w, M, c)
        tau = float(np.nanmedian(d)) if tau is None else tau
        s = alpha * np.exp(-d / tau) + (1 - alpha) * (cs + 1) / 2
        dg, _ = _wdist(Z[:, GEOM_IDX], t[GEOM_IDX], w[GEOM_IDX], M[:, GEOM_IDX])
        dt, _ = _wdist(Z[:, THERM_IDX], t[THERM_IDX], w[THERM_IDX], M[:, THERM_IDX])
    s = np.where(M.sum(1) >= min_features, s, np.nan)
    out = pd.DataFrame({"d_w": d, "cos_w": cs, "mcsi": s, "coverage": sw / w.sum(),
                        "geometry_match": np.exp(-dg / tau), "thermal_match": np.exp(-dt / tau)}, index=df.index)
    for col, (lo, hi) in (hard_limits or {}).items():
        out.loc[(df[col] < lo) | (df[col] > hi), "mcsi"] = 0.0
    return out


def shrink_partial(score: pd.Series, coverage: pd.Series, full_cov: float = 0.99) -> tuple[pd.Series, float]:
    """Cells scored on fewer features (e.g. SAR/DEM-only RCM cells: no thermal data) are shrunk toward the median score of
    fully-covered cells in proportion to missing weight, so partial evidence cannot outrank complete evidence by default.
    Returns (shrunk scores, prior)."""
    prior = float(score[coverage >= full_cov].median())
    return coverage * score + (1 - coverage) * prior, prior


def weight_robustness(df: pd.DataFrame, norm: PlanetNormalizer, base_w: dict[str, float] | None = None,
                      n: int = 200, top_frac: float = 0.02, conc: float = 20.0, seed: int = 0, **kw) -> pd.Series:
    """Monte-Carlo sensitivity: perturb weights ~ Dirichlet; fraction of runs in which each cell stays in the top set."""
    rng = np.random.default_rng(seed)
    b = np.array([(base_w or {}).get(c, 1.0) for c in FEATURES], float); b /= b.sum()
    hits = pd.Series(0.0, index=df.index)
    for _ in range(n):
        w = rng.dirichlet(conc * b + 1e-3)
        s = mcsi(df, norm, dict(zip(FEATURES, w)), **kw)["mcsi"]
        hits[s >= s.quantile(1 - top_frac)] += 1
    return hits / n


def percentile_vs_moon(earth_scores: pd.Series, lunar_scores: pd.Series) -> pd.Series:
    """Where would each Earth cell rank among lunar cells? 0.9 => better analog than 90% of lunar cells (NaN stays NaN)."""
    ref = np.sort(lunar_scores.dropna().values)
    p = np.searchsorted(ref, earth_scores.values) / max(len(ref), 1)
    return pd.Series(np.where(earth_scores.notna(), p, np.nan), index=earth_scores.index)
