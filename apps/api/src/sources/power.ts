import type { Connector } from "../analyze/analyze.js";
import type { ParamId, ParamValues } from "../scoring/index.js";
import { fetchJson } from "./http.js";
import type { FetchJsonOptions } from "./http.js";

/**
 * NASA POWER, point climatology (no account required):
 * https://power.larc.nasa.gov/docs/services/api/
 * POWER parameter -> catalog identifier (docs/scenarios.md).
 */
export const POWER_PARAMETERS = {
  T2M: "t2m_mean",
  T2M_MIN: "t2m_min",
  T2M_MAX: "t2m_max",
  WS2M: "wind",
  RH2M: "humidity",
  PRECTOTCORR: "precipitation",
  ALLSKY_SFC_SW_DWN: "solar",
} as const satisfies Record<string, ParamId>;

/** NASA POWER "no data" value. */
const POWER_FILL = -999;

export const POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point";

export function powerUrl(lat: number, lon: number): string {
  const params = Object.keys(POWER_PARAMETERS).join(",");
  return `${POWER_BASE_URL}?parameters=${params}&community=RE&longitude=${lon}&latitude=${lat}&format=JSON`;
}

/** Extracts the annual means (ANN key) from the POWER response. Throws if the shape is unexpected. */
export function parsePower(body: unknown): ParamValues {
  const parameter = (body as { properties?: { parameter?: Record<string, Record<string, unknown>> } } | null)?.properties
    ?.parameter;
  if (!parameter || typeof parameter !== "object") throw new Error("Unexpected NASA POWER response");
  const out: ParamValues = {};
  for (const [powerName, id] of Object.entries(POWER_PARAMETERS)) {
    const raw = parameter[powerName]?.ANN;
    out[id] = typeof raw === "number" && Number.isFinite(raw) && raw !== POWER_FILL ? raw : null;
  }
  return out;
}

export function createPowerConnector(options: FetchJsonOptions = {}): Connector {
  return async ({ lat, lon }) => parsePower(await fetchJson(powerUrl(lat, lon), options));
}
