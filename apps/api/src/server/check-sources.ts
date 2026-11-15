/**
 * Vérifie les vraies sources depuis votre machine (le réseau du bac à sable ne les atteint pas) :
 *   npm run check:sources
 * Compare avec les valeurs réelles de Haughton relevées le 2026-11-14 (data/fixtures/site-values.json),
 * et vérifie GVP avec Mauna Kea (volcan holocène : distance attendue presque nulle).
 */
import { createPowerConnector } from "../sources/power.js";
import { createUsgsConnector } from "../sources/usgs.js";
import { createGvpConnector } from "../sources/gvp.js";
import type { ParamValues } from "../scoring/index.js";

const HAUGHTON = { lat: 75.38, lon: -89.67 };
const EXPECTED: ParamValues = {
  t2m_mean: -14.42,
  t2m_min: -48.55,
  t2m_max: 16.81,
  wind: 3.08,
  humidity: 94.36,
  precipitation: 0.85,
  solar: 2.32,
  quake_count: 18,
};

async function main(): Promise<void> {
  const checks: [string, () => Promise<ParamValues>][] = [
    ["NASA POWER", () => createPowerConnector()(HAUGHTON)],
    ["USGS", () => createUsgsConnector()(HAUGHTON)],
  ];
  // GVP : Mauna Kea est lui-même un volcan holocène, la distance doit être presque nulle.
  // Une grande valeur signifierait que latitude et longitude sont inversées dans la réponse du WFS.
  const MAUNA_KEA = { lat: 19.82, lon: -155.47 };
  let failures = 0;
  try {
    const { volcano_distance: d } = await createGvpConnector()(MAUNA_KEA);
    const ok = typeof d === "number" && d < 15;
    console.log(`\nSmithsonian GVP : ${ok ? "OK" : "ÉCART"} — Mauna Kea à ${d} km du volcan le plus proche (attendu < 15 km)`);
    if (!ok) failures++;
  } catch (error) {
    failures++;
    console.log(`\nSmithsonian GVP : ÉCHEC — ${error instanceof Error ? error.message : String(error)}`);
  }
  for (const [name, run] of checks) {
    try {
      const values = await run();
      console.log(`\n${name} : OK`);
      for (const [param, value] of Object.entries(values)) {
        const expected = EXPECTED[param as keyof ParamValues];
        const close = typeof value === "number" && typeof expected === "number" && Math.abs(value - expected) <= Math.max(1, Math.abs(expected) * 0.15);
        console.log(`  ${param.padEnd(14)} ${String(value).padEnd(10)} attendu ~${expected}  ${close ? "ok" : "ÉCART (à vérifier)"}`);
      }
    } catch (error) {
      failures++;
      console.log(`\n${name} : ÉCHEC — ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  process.exit(failures === 0 ? 0 : 1);
}

void main();
