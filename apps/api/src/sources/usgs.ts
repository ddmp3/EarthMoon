import type { Connector } from "../analyze/analyze.js";
import { fetchJson } from "./http.js";
import type { FetchJsonOptions } from "./http.js";

/**
 * USGS Earthquake Catalog (FDSN), number of M ≥ 2.5 earthquakes within 300 km since 2000:
 * https://earthquake.usgs.gov/fdsnws/event/1/
 */
export const USGS_COUNT_URL = "https://earthquake.usgs.gov/fdsnws/event/1/count";
export const QUAKE_RADIUS_KM = 300;
export const QUAKE_MIN_MAGNITUDE = 2.5;
export const QUAKE_START_DATE = "2000-01-01";

export function usgsUrl(lat: number, lon: number): string {
  return (
    `${USGS_COUNT_URL}?format=geojson&latitude=${lat}&longitude=${lon}` +
    `&maxradiuskm=${QUAKE_RADIUS_KM}&minmagnitude=${QUAKE_MIN_MAGNITUDE}&starttime=${QUAKE_START_DATE}`
  );
}

export function parseUsgsCount(body: unknown): number {
  const count = (body as { count?: unknown } | null)?.count;
  if (typeof count !== "number" || !Number.isInteger(count) || count < 0) {
    throw new Error("Unexpected USGS response");
  }
  return count;
}

export function createUsgsConnector(options: FetchJsonOptions = {}): Connector {
  return async ({ lat, lon }) => ({ quake_count: parseUsgsCount(await fetchJson(usgsUrl(lat, lon), options)) });
}
