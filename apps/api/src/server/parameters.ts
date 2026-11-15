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
  t2m_min: { label: "Air temperature (minimum)", unit: "°C", source: "NASA POWER", lunar: "— (cold proxy)" },
  t2m_max: { label: "Air temperature (maximum)", unit: "°C", source: "NASA POWER", lunar: "— (cold proxy)" },
  wind: { label: "Mean wind speed at 2 m", unit: "m/s", source: "NASA POWER", lunar: "0 (no atmosphere)" },
  humidity: { label: "Relative humidity at 2 m", unit: "%", source: "NASA POWER", lunar: "0" },
  precipitation: { label: "Precipitation", unit: "mm/day", source: "NASA POWER", lunar: "0" },
  solar: {
    label: "Solar irradiance",
    unit: "kWh/m²/day",
    source: "NASA POWER",
    lunar: "near-continuous illumination on some polar ridges",
  },
  latitude_abs: { label: "Absolute latitude", unit: "°", source: "coordinates", lunar: "polar illumination regime" },
  quake_count: {
    label: "Earthquakes M ≥ 2.5 within 300 km since 2000",
    unit: "count",
    source: "USGS Earthquake Catalog",
    lunar: "weak moonquakes",
  },
  volcano_distance: {
    label: "Distance to the nearest Holocene volcano",
    unit: "km",
    source: "Smithsonian GVP",
    lunar: "basaltic maria, lava tubes",
  },
};

export const PARAMETERS: ParameterInfo[] = (Object.keys(INFO) as ParamId[]).map((id) => ({ id, ...INFO[id] }));
