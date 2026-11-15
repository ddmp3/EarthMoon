import type { Connector } from "../analyze/analyze.js";
import { fetchJson } from "./http.js";
import type { FetchJsonOptions } from "./http.js";

/**
 * Smithsonian Global Volcanism Program (GVP), volcans holocènes, service WFS en GeoJSON (aucun compte requis).
 * La liste (~1 300 volcans) est téléchargée une fois puis gardée en mémoire ; la distance au plus proche est calculée
 * localement (formule de haversine). URL remplaçable par la variable d'environnement GVP_WFS_URL.
 * `srsName=EPSG:4326` (forme courte) demande l'ordre longitude, latitude ; on lit d'abord les attributs
 * Latitude / Longitude quand ils existent, ce qui évite toute ambiguïté d'axes.
 */
export const GVP_WFS_URL =
  "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=2.0.0&request=GetFeature" +
  "&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes&outputFormat=application/json&srsName=EPSG:4326";

export type Volcano = { lat: number; lon: number; name?: string };

const EARTH_RADIUS_KM = 6371.0088;

const isLat = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= -90 && v <= 90;
const isLon = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= -180 && v <= 180;

/** Distance orthodromique en km. */
export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(a)));
}

/** GeoJSON FeatureCollection du WFS -> liste de volcans. Lance une erreur si rien d'exploitable. */
export function parseVolcanoes(body: unknown): Volcano[] {
  const features = (body as { type?: string; features?: unknown } | null)?.features;
  if (!Array.isArray(features)) throw new Error("Réponse GVP inattendue (pas de FeatureCollection)");
  const out: Volcano[] = [];
  for (const f of features) {
    const props = ((f as { properties?: Record<string, unknown> } | null)?.properties ?? {}) as Record<string, unknown>;
    const coords = (f as { geometry?: { coordinates?: unknown } } | null)?.geometry?.coordinates;
    let lat: unknown = props.Latitude;
    let lon: unknown = props.Longitude;
    if (!isLat(lat) || !isLon(lon)) {
      [lon, lat] = Array.isArray(coords) ? coords : [];
    }
    if (!isLat(lat) || !isLon(lon)) continue;
    const name = typeof props.Volcano_Name === "string" ? props.Volcano_Name : undefined;
    out.push(name ? { lat, lon, name } : { lat, lon });
  }
  if (out.length === 0) throw new Error("Réponse GVP sans volcan exploitable");
  return out;
}

export function nearestVolcanoKm(volcanoes: Volcano[], lat: number, lon: number): number {
  let best = Infinity;
  for (const v of volcanoes) best = Math.min(best, haversineKm(lat, lon, v.lat, v.lon));
  return best;
}

export type GvpOptions = FetchJsonOptions & { url?: string; ttlMs?: number; now?: () => number };

/**
 * Connecteur volcano_distance (km). La liste est chargée au premier appel, partagée entre les appels simultanés
 * et rechargée après `ttlMs` (24 h par défaut). Un échec de chargement n'est pas mémorisé : l'appel suivant réessaie.
 */
export function createGvpConnector(options: GvpOptions = {}): Connector {
  const { url = process.env.GVP_WFS_URL ?? GVP_WFS_URL, ttlMs = 24 * 60 * 60 * 1000, now = Date.now, ...fetchOptions } = options;
  let loaded: { at: number; volcanoes: Volcano[] } | undefined;
  let loading: Promise<Volcano[]> | undefined;

  const load = async (): Promise<Volcano[]> => {
    if (loaded && now() - loaded.at < ttlMs) return loaded.volcanoes;
    loading ??= fetchJson(url, { timeoutMs: 30_000, ...fetchOptions })
      .then((body) => {
        const volcanoes = parseVolcanoes(body);
        loaded = { at: now(), volcanoes };
        return volcanoes;
      })
      .finally(() => {
        loading = undefined;
      });
    return loading;
  };

  return async ({ lat, lon }) => ({ volcano_distance: Math.round(nearestVolcanoKm(await load(), lat, lon) * 10) / 10 });
}
