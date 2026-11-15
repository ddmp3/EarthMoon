import type { Connector } from "../analyze/analyze.js";

/** latitude_abs vient des coordonnées du site : aucune source externe. */
export const coordinatesConnector: Connector = async ({ lat }) => ({ latitude_abs: Math.abs(lat) });
