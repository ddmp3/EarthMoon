// npm audit gate for development dependencies.
//   npm audit --json | node tools/security/npm_audit_gate.mjs tools/security/audit-allowlist.json
// Production dependencies are checked separately and strictly (`npm audit --omit=dev`, 0 allowed).
// Here every advisory of the full tree must be in the allowlist, with a reason and a review date that
// has not passed. Exit code 1 otherwise.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

/** Unique advisories of an `npm audit --json` (v2) report: [{ id, package, severity, title, url }]. */
export function advisories(report) {
  const byId = new Map();
  for (const vuln of Object.values(report.vulnerabilities ?? {})) {
    for (const via of vuln.via ?? []) {
      if (typeof via !== "object" || !via.url) continue;
      const id = via.url.split("/").pop();
      if (!byId.has(id)) byId.set(id, { id, package: via.name, severity: via.severity, title: via.title, url: via.url });
    }
  }
  return [...byId.values()];
}

/** failures: advisories not covered by a valid allowlist entry; stale: allowlist ids no longer reported. */
export function evaluate(report, allowlist, today) {
  const found = advisories(report);
  const failures = [];
  for (const a of found) {
    const entry = allowlist.find((e) => e.id === a.id);
    if (!entry) {
      failures.push(`${a.id} ${a.package} (${a.severity}): ${a.title} ${a.url}: not in the allowlist`);
    } else if (!entry.reason || !entry.reviewBy || !entry.scope) {
      failures.push(`${a.id}: allowlist entry needs scope, reason and reviewBy`);
    } else if (entry.reviewBy < today) {
      failures.push(`${a.id}: allowlist review date ${entry.reviewBy} has passed, review it again`);
    }
  }
  const stale = allowlist.filter((e) => !found.some((a) => a.id === e.id)).map((e) => e.id);
  return { found, failures, stale };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const allowlist = JSON.parse(readFileSync(process.argv[2], "utf8")).advisories;
  const report = JSON.parse(readFileSync(0, "utf8"));
  const today = new Date().toISOString().slice(0, 10);
  const { found, failures, stale } = evaluate(report, allowlist, today);
  for (const a of found) console.log(`advisory ${a.id} ${a.package} (${a.severity}) ${failures.some((f) => f.startsWith(a.id)) ? "FAIL" : "allowlisted"}`);
  for (const id of stale) console.log(`note: allowlist entry ${id} is no longer reported, remove it`);
  for (const f of failures) console.error(`FAIL ${f}`);
  process.exit(failures.length ? 1 : 0);
}
