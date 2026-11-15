import type { Connector } from "../analyze/analyze.js";
import { fetchJson } from "./http.js";
import type { FetchJsonOptions } from "./http.js";

/**
 * Smithsonian Global Volcanism Program (GVP), Holocene volcanoes, WFS service returning GeoJSON (no account required).
 * The list (~1,300 volcanoes) is downloaded once and kept in memory; the distance to the nearest one is computed
 * locally (haversine formula). URL overridable with the GVP_WFS_URL environment variable.
 * `srsName=EPSG:4326` (short form) asks for longitude, latitude order; we read the Latitude / Longitude
 * attributes first when they exist, which avoids any axis ambiguity.
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

/** WFS GeoJSON FeatureCollection -> list of volcanoes. Throws if nothing usable. */
export function parseVolcanoes(body: unknown): Volcano[] {
  const features = (body as { type?: string; features?: unknown } | null)?.features;
  if (!Array.isArray(features)) throw new Error("Unexpected GVP response (no FeatureCollection)");
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
  if (out.length === 0) throw new Error("GVP response without any usable volcano");
  return out;
}

export function nearestVolcanoKm(volcanoes: Volcano[], lat: number, lon: number): number {
  let best = Infinity;
  for (const v of volcanoes) best = Math.min(best, haversineKm(lat, lon, v.lat, v.lon));
  return best;
}

export type GvpOptions = FetchJsonOptions & { url?: string; ttlMs?: number; now?: () => number };

/**
 * volcano_distance connector (km). The list is loaded on the first call, shared between concurrent calls
 * and reloaded after `ttlMs` (24 h by default). A load failure is not remembered: the next call retries.
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
