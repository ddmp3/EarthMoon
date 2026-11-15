import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Chemins de l'API. Ce fichier est dans src/server/ (tsx) ou dist/server/ (build) :
 * dans les deux cas, ../.. est le dossier apps/api.
 */
const here = path.dirname(fileURLToPath(import.meta.url));

export const API_ROOT = path.resolve(here, "../..");
export const REPO_ROOT = path.resolve(API_ROOT, "../..");

export type ServerConfig = {
  port: number;
  dataDir: string;
  /** Origines autorisées par CORS (domaine du front). */
  allowedOrigins: string[];
  /** Si vrai : valeurs d'exemple (data/fixtures) au lieu des vraies sources. Jamais pour la démo. */
  useFixtures: boolean;
  rateLimitPerMinute: number;
};

export function readConfig(env: NodeJS.ProcessEnv = process.env): ServerConfig {
  const port = Number(env.PORT ?? 3001);
  if (!Number.isInteger(port) || port <= 0 || port > 65535) throw new Error(`PORT invalide : ${env.PORT}`);
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
  };
}
