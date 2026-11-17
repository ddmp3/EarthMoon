import type { ParamId } from "../scoring/index.js";

/** Parameter catalog (docs/scenarios.md). `Record<ParamId, …>` forces every identifier to be covered. */
export type ParameterInfo = {
  id: ParamId;
  label: string;
  unit: string;
  /** Earth source. */
  source: string;
  /** Lunar equivalent. */
  lunar: string;
};

const INFO: Record<ParamId, Omit<ParameterInfo, "id">> = {
  slope_mean: { label: "Mean slope (1 km window)", unit: "°", source: "Copernicus DEM", lunar: "LOLA" },
  slope_max: { label: "Maximum slope (1 km window)", unit: "°", source: "Copernicus DEM", lunar: "LOLA" },
  roughness: { label: "Roughness: standard deviation of elevation (1 km window)", unit: "m", source: "Copernicus DEM", lunar: "LOLA" },
  elevation: { label: "Elevation", unit: "m", source: "Copernicus DEM", lunar: "—" },
  ndvi: { label: "Vegetation index", unit: "", source: "MODIS MOD13A1", lunar: "no vegetation" },
  lst_day: { label: "Surface temperature (day)", unit: "°C", source: "MODIS MOD11A2", lunar: "Diviner" },
  lst_night: { label: "Surface temperature (night)", unit: "°C", source: "MODIS MOD11A2", lunar: "Diviner" },
  lst_amplitude: { label: "Surface day-night swing", unit: "°C", source: "MODIS MOD11A2", lunar: "Diviner" },
  t2m_mean: { label: "Air temperature (mean)", unit: "°C", source: "NASA POWER", lunar: "— (cold proxy)" },
  t2m_min: { label: "Air temperature (coldest monthly minimum)", unit: "°C", source: "NASA POWER", lunar: "— (cold proxy)" },
  t2m_max: { label: "Air temperature (maximum)", unit: "°C", source: "NASA POWER", lunar: "— (cold proxy)" },
  wind: { label: "Mean wind speed at 2 m", unit: "m/s", source: "NASA POWER", lunar: "0 (no atmosphere)" },
  humidity: { label: "Relative humidity at 2 m (deprecated: depends on temperature, use specific_humidity)", unit: "%", source: "NASA POWER", lunar: "0" },
  precipitation: { label: "Precipitation", unit: "mm/day", source: "NASA POWER", lunar: "0" },
  solar: {
    label: "Solar irradiance",
    unit: "kWh/m²/day",
    source: "NASA POWER",
    lunar: "near-continuous illumination on some polar ridges",
  },
  latitude_abs: { label: "Absolute latitude", unit: "°", source: "coordinates", lunar: "polar illumination regime" },
  quake_count: {
    label: "Earthquakes M ≥ 2.5 within 300 km since 2000 (deprecated: catalog incomplete outside dense networks)",
    unit: "count",
    source: "USGS Earthquake Catalog",
    lunar: "weak moonquakes",
  },
  volcano_distance: {
    label: "Distance to the nearest Holocene volcano (deprecated: says nothing about rock type or lava tubes)",
    unit: "km",
    source: "Smithsonian GVP",
    lunar: "none",
  },
  slope_p95: { label: "95th percentile of slope (1 km window, 40 m baseline)", unit: "°", source: "Copernicus DEM", lunar: "LOLA" },
  roughness_detrended: {
    label: "Roughness: relief left after removing the mean tilt (1 km window)",
    unit: "m",
    source: "Copernicus DEM",
    lunar: "LOLA",
  },
  traversable_15: { label: "Share of the 1 km window with slope ≤ 15°", unit: "", source: "Copernicus DEM", lunar: "LOLA" },
  traversable_20: { label: "Share of the 1 km window with slope ≤ 20°", unit: "", source: "Copernicus DEM", lunar: "LOLA" },
  traversable_25: { label: "Share of the 1 km window with slope ≤ 25°", unit: "", source: "Copernicus DEM", lunar: "LOLA" },
  specific_humidity: {
    label: "Specific humidity at 2 m (water vapour content of the air)",
    unit: "g/kg",
    source: "NASA POWER",
    lunar: "0 (no atmosphere)",
  },
  quake_m45_count: {
    label: "Earthquakes M ≥ 4.5 within 300 km since 2000",
    unit: "count",
    source: "USGS Earthquake Catalog",
    lunar: "weak moonquakes",
  },
  lava_tube_evidence: {
    label: "Lava tube evidence (1 predisposition only, 2 probable, 3 demonstrated; empty = not assessed)",
    unit: "level",
    source: "Smithsonian GVP and references in data/evidence/lava-tubes.json",
    lunar: "mare pits and lava tubes (not a south polar feature)",
  },
};

export const PARAMETERS: ParameterInfo[] = (Object.keys(INFO) as ParamId[]).map((id) => ({ id, ...INFO[id] }));
