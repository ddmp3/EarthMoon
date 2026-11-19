import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * API paths. This file lives in src/server/ (tsx) or dist/server/ (build):
 * in both cases ../.. is the apps/api folder.
 */
const here = path.dirname(fileURLToPath(import.meta.url));

export const API_ROOT = path.resolve(here, "../..");
export const REPO_ROOT = path.resolve(API_ROOT, "../..");

export type ServerConfig = {
  port: number;
  dataDir: string;
  /** Origins allowed by CORS (front-end domain). */
  allowedOrigins: string[];
  /** If true: sample values (data/fixtures) instead of the real sources. Never for the demo. */
  useFixtures: boolean;
  rateLimitPerMinute: number;
  /** Folder of the v3 releases (index.json and one folder per release). */
  releasesDir: string;
  /** Internal discovery service (ADR-005), for example http://discovery:8000 on the Compose network. */
  discoveryUrl?: string;
};

export function readConfig(env: NodeJS.ProcessEnv = process.env): ServerConfig {
  const port = Number(env.PORT ?? 3001);
  if (!Number.isInteger(port) || port <= 0 || port > 65535) throw new Error(`Invalid PORT : ${env.PORT}`);
  const origins = [env.FRONTEND_URL, ...(env.EXTRA_ORIGINS ?? "").split(",")]
    .map((o) => o?.trim().replace(/\/$/, ""))
    .filter((o): o is string => Boolean(o));
  if (env.NODE_ENV !== "production") origins.push("http://localhost:5173", "http://127.0.0.1:5173");
  return {
    port,
    dataDir: env.DATA_DIR ?? path.join(REPO_ROOT, "data"),
    allowedOrigins: [...new Set(origins)],
    useFixtures: env.USE_FIXTURES === "1" || env.USE_FIXTURES === "true",
    rateLimitPerMinute: Number(env.RATE_LIMIT_PER_MINUTE ?? 120),
    releasesDir: env.RELEASES_DIR ?? path.join(env.DATA_DIR ?? path.join(REPO_ROOT, "data"), "releases"),
    ...(env.DISCOVERY_URL ? { discoveryUrl: env.DISCOVERY_URL.replace(/\/$/, "") } : {}),
  };
}
