import type { ParamId } from "../scoring/index.js";

/** Catalogue des paramètres (docs/scenarios.md). `Record<ParamId, …>` oblige à couvrir tous les identifiants. */
export type ParameterInfo = {
  id: ParamId;
  label: string;
  unit: string;
  /** Source terrestre. */
  source: string;
  /** Équivalent lunaire. */
  lunar: string;
};

const INFO: Record<ParamId, Omit<ParameterInfo, "id">> = {
  slope_mean: { label: "Pente moyenne (fenêtre 1 km)", unit: "°", source: "Copernicus DEM", lunar: "LOLA" },
  slope_max: { label: "Pente maximale (fenêtre 1 km)", unit: "°", source: "Copernicus DEM", lunar: "LOLA" },
  roughness: { label: "Rugosité : écart-type de l'altitude (fenêtre 1 km)", unit: "m", source: "Copernicus DEM", lunar: "LOLA" },
  elevation: { label: "Altitude", unit: "m", source: "Copernicus DEM", lunar: "—" },
  ndvi: { label: "Indice de végétation", unit: "", source: "MODIS MOD13A1", lunar: "aucune végétation" },
  lst_day: { label: "Température de surface (jour)", unit: "°C", source: "MODIS MOD11A2", lunar: "Diviner" },
  lst_night: { label: "Température de surface (nuit)", unit: "°C", source: "MODIS MOD11A2", lunar: "Diviner" },
  lst_amplitude: { label: "Amplitude jour-nuit de surface", unit: "°C", source: "MODIS MOD11A2", lunar: "Diviner" },
  t2m_mean: { label: "Température de l'air (moyenne)", unit: "°C", source: "NASA POWER", lunar: "— (proxy du froid)" },
  t2m_min: { label: "Température de l'air (minimale)", unit: "°C", source: "NASA POWER", lunar: "— (proxy du froid)" },
  t2m_max: { label: "Température de l'air (maximale)", unit: "°C", source: "NASA POWER", lunar: "— (proxy du froid)" },
  wind: { label: "Vitesse moyenne du vent à 2 m", unit: "m/s", source: "NASA POWER", lunar: "0 (pas d'atmosphère)" },
  humidity: { label: "Humidité relative à 2 m", unit: "%", source: "NASA POWER", lunar: "0" },
  precipitation: { label: "Précipitations", unit: "mm/jour", source: "NASA POWER", lunar: "0" },
  solar: {
    label: "Ensoleillement",
    unit: "kWh/m²/jour",
    source: "NASA POWER",
    lunar: "éclairage quasi continu sur certaines crêtes polaires",
  },
  latitude_abs: { label: "Latitude absolue", unit: "°", source: "coordonnées", lunar: "régime d'éclairage polaire" },
  quake_count: {
    label: "Séismes M ≥ 2,5 à moins de 300 km depuis 2000",
    unit: "nombre",
    source: "USGS Earthquake Catalog",
    lunar: "séismes lunaires faibles",
  },
  volcano_distance: {
    label: "Distance au volcan holocène le plus proche",
    unit: "km",
    source: "Smithsonian GVP",
    lunar: "mers basaltiques, tubes de lave",
  },
};

export const PARAMETERS: ParameterInfo[] = (Object.keys(INFO) as ParamId[]).map((id) => ({ id, ...INFO[id] }));
