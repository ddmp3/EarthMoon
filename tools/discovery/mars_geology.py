"""Geologic map of Mars, Tanaka et al. 2014 (USGS SIM 3292, doi:10.3133/sim3292): map units under points (T48c, R5).

The volcanic plains target (decision E20, accepted by David on 20/11/2026; units confirmed on 24/11/2026) takes every
unit that the map itself describes as volcanic (field UnitDesc): no hand-made list of units. The map is at
1:20,000,000, so a MOLA window belongs to the target when its centre falls inside such a unit. The volcanic edifices
(UnitDesc "volcanic edifice") are left out in a sensitivity test only.

The shapefile is in the Mars 2000 sphere (radius 3,396,190 m, the MOLA sphere), longitudes -180 to 180° east; MOLA
windows use 0 to 360° east.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

VOLCANIC_WORD = "volcanic"
EDIFICE_WORDS = ("volcanic edifice",)


def volcanic_units(descriptions: dict[str, str]) -> set[str]:
    """Units whose map description names them volcanic."""
    return {u for u, d in descriptions.items() if VOLCANIC_WORD in (d or "").lower()}


def edifice_units(descriptions: dict[str, str]) -> set[str]:
    """Volcanic units the map describes as edifices (left out in the sensitivity test)."""
    return {u for u, d in descriptions.items() if any(w in (d or "").lower() for w in EDIFICE_WORDS)}


def lon180(lon: np.ndarray) -> np.ndarray:
    """Longitudes east from 0..360 to -180..180."""
    return (np.asarray(lon, float) + 180.0) % 360.0 - 180.0


@dataclass(frozen=True)
class UnitMap:
    """Polygons of the map units, with a spatial index."""
    units: tuple[str, ...]
    geoms: tuple
    descriptions: dict

    @classmethod
    def read(cls, base: Path) -> "UnitMap":
        import shapefile
        from shapely.geometry import shape
        units, geoms, desc = [], [], {}
        with shapefile.Reader(str(base)) as r:
            for sr in r.iterShapeRecords():
                d = sr.record.as_dict()
                g = shape(sr.shape.__geo_interface__)
                if not g.is_valid:
                    g = g.buffer(0)
                if g.is_empty:
                    continue
                units.append(str(d["Unit"]))
                geoms.append(g)
                desc[str(d["Unit"])] = str(d.get("UnitDesc") or "")
        return cls(tuple(units), tuple(geoms), desc)

    def unit_at(self, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        """Unit symbol under each point (MOLA longitudes, 0..360° east); "" where no unit."""
        from shapely import STRtree, points
        lat = np.asarray(lat, float)
        pts = points(np.c_[lon180(lon), lat])
        out = np.full(lat.size, "", dtype=object)
        pi, gi = STRtree(list(self.geoms)).query(pts, predicate="within")
        for p, g in zip(pi.tolist(), gi.tolist()):
            if out[p] == "":
                out[p] = self.units[g]
        return out

    def inside(self, lat: np.ndarray, lon: np.ndarray, selected: set[str]) -> np.ndarray:
        """True where the point is inside one of the selected units."""
        u = self.unit_at(lat, lon)
        return np.array([x in selected for x in u], dtype=bool)
