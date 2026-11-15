import type { Connector } from "../analyze/analyze.js";

/** latitude_abs comes from the site coordinates: no external source. */
export const coordinatesConnector: Connector = async ({ lat }) => ({ latitude_abs: Math.abs(lat) });
