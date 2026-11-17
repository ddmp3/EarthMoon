import type { ParamId, ParamValues } from "../scoring/index.js";

/**
 * Catalog of data sources, named for the application and the Space Apps submission
 * (every source must be cited). Each parameter has a single source.
 */
export type DataSource = {
  id: string;
  name: string;
  provider: string;
  url: string;
  /** Earth side (candidates) or Moon side (reference profile). */
  body: "earth" | "moon";
  params: ParamId[];
  /** Attribution or terms of use to reproduce. */
  terms: string;
};

export const SOURCES: DataSource[] = [
  {
    id: "coordinates",
    name: "Candidate site coordinates",
    provider: "Cyber&Space 🛰️ Montréal (data/candidates.json)",
    url: "https://github.com/ddmp3/nasa-space-app-challenge-2026-cyber-space/blob/main/data/candidates.json",
    body: "earth",
    params: ["latitude_abs"],
    terms: "Versioned list in the project repository.",
  },
  {
    id: "nasa-power",
    name: "NASA POWER (point climatology)",
    provider: "NASA Langley Research Center",
    url: "https://power.larc.nasa.gov/",
    body: "earth",
    params: ["t2m_mean", "t2m_min", "t2m_max", "wind", "humidity", "specific_humidity", "precipitation", "solar"],
    terms: "NASA data, open access. Data obtained from the NASA Langley Research Center POWER Project.",
  },
  {
    id: "usgs-comcat",
    name: "USGS Earthquake Catalog (ComCat)",
    provider: "U.S. Geological Survey",
    url: "https://earthquake.usgs.gov/fdsnws/event/1/",
    body: "earth",
    params: ["quake_count", "quake_m45_count"],
    terms:
      "Public domain (U.S. Government). Earthquakes within 300 km since 2000: M ≥ 4.5 (quake_m45_count, reported worldwide) and M ≥ 2.5 (quake_count, complete only where networks are dense).",
  },
  {
    id: "smithsonian-gvp",
    name: "Smithsonian Global Volcanism Program, Volcanoes of the World (Holocene)",
    provider: "Smithsonian Institution",
    url: "https://volcano.si.edu/",
    body: "earth",
    params: ["volcano_distance", "lava_tube_evidence"],
    terms:
      "Global Volcanism Program, Smithsonian Institution, Volcanoes of the World database. lava_tube_evidence level 1 is derived from its rock type and distance; levels 2 and 3 come from the references in data/evidence/lava-tubes.json.",
  },
  {
    id: "copernicus-dem",
    name: "Copernicus DEM GLO-30",
    provider: "ESA / European Union (Copernicus programme), via AWS Open Data",
    url: "https://registry.opendata.aws/copernicus-dem/",
    body: "earth",
    params: [
      "elevation",
      "slope_mean",
      "slope_max",
      "slope_p95",
      "roughness",
      "roughness_detrended",
      "traversable_15",
      "traversable_20",
      "traversable_25",
    ],
    terms:
      "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA. Resampled to the 40 m grid of the lunar model; slope and roughness computed over 1 km windows (tools/precompute/site_terrain.py).",
  },
  {
    id: "modis",
    name: "NASA MODIS MOD11A2 / MYD11A2 (land surface temperature) and MOD13A1 / MYD13A1 (NDVI), version 6.1",
    provider: "NASA LP DAAC, via Microsoft Planetary Computer",
    url: "https://planetarycomputer.microsoft.com/dataset/group/modis",
    body: "earth",
    params: ["lst_day", "lst_night", "lst_amplitude", "ndvi"],
    terms: "NASA data, open access. 2024 means precomputed (tools/precompute/modis_values.py).",
  },
  {
    id: "lro-lola",
    name: "LRO LOLA polar elevation model LDEM_85S_40M",
    provider: "NASA, PDS Geosciences Node",
    url: "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/",
    body: "moon",
    params: [
      "slope_mean",
      "slope_max",
      "slope_p95",
      "roughness",
      "roughness_detrended",
      "traversable_15",
      "traversable_20",
      "traversable_25",
    ],
    terms:
      "NASA PDS data, open access. Computed with the same function, pixel and window as Earth (tools/precompute/lunar_reference_v2.py).",
  },
  {
    id: "lro-diviner",
    name: "LRO Diviner (lunar temperatures)",
    provider: "NASA / UCLA, Paige et al. 2010 (Science 330:479)",
    url: "https://www.diviner.ucla.edu/",
    body: "moon",
    params: ["lst_night"],
    terms: "Published values cited in data/reference/moon-south-pole.json.",
  },
];

const EARTH_SOURCE_BY_PARAM = new Map<ParamId, string>(
  SOURCES.filter((s) => s.body === "earth").flatMap((s) => s.params.map((p) => [p, s.id] as const)),
);

/** Source (catalog id) of each known value. In fixtures mode, everything comes from the sample data. */
export function valueSources(values: ParamValues, useFixtures = false): Partial<Record<ParamId, string>> {
  const out: Partial<Record<ParamId, string>> = {};
  for (const [param, value] of Object.entries(values) as [ParamId, number | null | undefined][]) {
    if (typeof value !== "number") continue;
    out[param] = useFixtures && param !== "latitude_abs" ? "fixtures" : (EARTH_SOURCE_BY_PARAM.get(param) ?? "unknown");
  }
  return out;
}
