"""Phase 4 - Clustering, spatial random forest, novelty scoring and interactive map export."""
from __future__ import annotations
import numpy as np
import pandas as pd
import xarray as xr
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import silhouette_score, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import RobustScaler
from .config import KNOWN_ANALOGS


def to_table(f: xr.Dataset, extra: dict[str, xr.DataArray] | None = None) -> pd.DataFrame:
    g = f.copy()
    for k, v in (extra or {}).items():
        g[k] = v
    return g.to_dataframe().reset_index()


# ---------- Spatial clustering ----------
def cluster_regimes(df: pd.DataFrame, feats: list[str], k_range=range(3, 9), geo_weight: float = 0.0, seed=0):
    """KMeans on robust-scaled features (+ optionally lat/lon with geo_weight>0 for spatially coherent regions).
    k chosen by silhouette. Returns (labels Series, k). Returns (empty, 0) if too few rows."""
    d = df.dropna(subset=feats)
    k_range = [k for k in k_range if k <= len(d) // 10]
    if not k_range:
        return pd.Series(dtype=float, name="regime"), 0
    X = RobustScaler().fit_transform(d[feats].values)
    if geo_weight > 0:
        G = RobustScaler().fit_transform(d[["lat", "lon"]].values) * geo_weight
        X = np.c_[X, G]
    best = (-1, None, None)
    sub = np.random.default_rng(seed).choice(len(X), size=min(4000, len(X)), replace=False)
    for k in k_range:
        km = KMeans(k, n_init=5, random_state=seed).fit(X)
        s = silhouette_score(X[sub], km.labels_[sub])
        if s > best[0]:
            best = (s, k, km.labels_)
    return pd.Series(best[2], index=d.index, name="regime"), best[1]


def cluster_analog_rank(df: pd.DataFrame, labels: pd.Series, score_col="mcsi") -> pd.DataFrame:
    """Which regimes host the best analogs? -> mean/p90 MCSI per cluster."""
    g = df.drop(columns=["regime"], errors="ignore").assign(regime=labels).groupby("regime")[score_col]
    return g.agg(count="count", mean="mean", p90=lambda s: s.quantile(0.9)).sort_values("p90", ascending=False)


# ---------- Spatial random forest ----------
class SpatialRF:
    """RF surrogate of the similarity score with *spatial-block* CV (avoids optimistic autocorrelation leakage).
    Uses: (1) driver analysis via permutation importance, (2) predicting score where features are partly missing
    (gap-filling), (3) tree-variance as per-cell model uncertainty."""

    def __init__(self, feats: list[str], block_deg: float = 2.0, n_estimators=300, seed=0):
        self.feats, self.block, self.seed = feats, block_deg, seed
        self.rf = RandomForestRegressor(n_estimators=n_estimators, min_samples_leaf=3, n_jobs=-1, random_state=seed)

    def _blocks(self, df):
        return (df["lat"] // self.block).astype(int).astype(str) + "_" + (df["lon"] // self.block).astype(int).astype(str)

    def fit(self, df: pd.DataFrame, target="mcsi", use_coords=False):
        d = df.dropna(subset=self.feats + [target])
        cols = self.feats + (["lat", "lon"] if use_coords else [])
        self.cols = cols
        groups = self._blocks(d)
        scores = []
        for tr, te in GroupKFold(n_splits=min(5, groups.nunique())).split(d, groups=groups):
            m = RandomForestRegressor(n_estimators=150, min_samples_leaf=3, n_jobs=-1, random_state=self.seed).fit(d.iloc[tr][cols], d.iloc[tr][target])
            scores.append(r2_score(d.iloc[te][target], m.predict(d.iloc[te][cols])))
        self.cv_r2 = float(np.mean(scores))
        self.rf.fit(d[cols], d[target])
        self.importance = pd.Series(self.rf.feature_importances_, index=cols).sort_values(ascending=False)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.cols].fillna(df[self.cols].median())
        preds = np.stack([t.predict(X.values) for t in self.rf.estimators_])
        return pd.DataFrame({"rf_mean": preds.mean(0), "rf_std": preds.std(0)}, index=df.index)


# ---------- Novelty ----------
def haversine_km(lat, lon, lat0, lon0):
    la, lo, la0, lo0 = map(np.deg2rad, (lat, lon, lat0, lon0))
    a = np.sin((la - la0) / 2) ** 2 + np.cos(la) * np.cos(la0) * np.sin((lo - lo0) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def novelty_km(df: pd.DataFrame, known=KNOWN_ANALOGS) -> pd.Series:
    """Distance (km) to the nearest classical analog site -> 'non-traditional' analogs score high."""
    D = np.stack([haversine_km(df["lat"].values, df["lon"].values, la, lo) for la, lo in known.values()])
    return pd.Series(D.min(0), index=df.index, name="novelty_km")


def rank_analogs(df: pd.DataFrame, score="mcsi", gap="gap_index", w_gap=0.25, w_nov=0.25, nov_scale_km=1500) -> pd.Series:
    """Final priority = similarity, boosted by observational gap and by distance from known analogs."""
    nov = (df["novelty_km"] / nov_scale_km).clip(0, 1) if "novelty_km" in df else 0
    g = df[gap].fillna(0) if gap in df else 0
    return (df[score] * (1 + w_gap * g + w_nov * nov)).rename("priority")
