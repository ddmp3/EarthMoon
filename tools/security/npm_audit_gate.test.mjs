// Tests of the npm audit gate. Run: node --test tools/security/
import { test } from "node:test";
import assert from "node:assert/strict";
import { advisories, evaluate } from "./npm_audit_gate.mjs";

const report = (vulns) => ({ vulnerabilities: vulns });
const adv = (name, id, severity = "high") => ({
  name, severity, via: [{ source: 1, name, title: `${name} issue`, url: `https://github.com/advisories/${id}`, severity, range: "<=1" }],
});
const transitive = (name, through) => ({ name, severity: "high", via: [through] });

test("collects each advisory once, with the packages it reaches", () => {
  const r = report({
    picomatch: adv("picomatch", "GHSA-aaaa"),
    vite: { name: "vite", severity: "high", via: ["picomatch", { source: 2, name: "picomatch", title: "t", url: "https://github.com/advisories/GHSA-aaaa", severity: "high" }] },
    vitest: transitive("vitest", "vite"),
  });
  const found = advisories(r);
  assert.equal(found.length, 1);
  assert.equal(found[0].id, "GHSA-aaaa");
  assert.equal(found[0].package, "picomatch");
});

test("an empty report passes", () => {
  assert.deepEqual(evaluate(report({}), [], "2026-11-17").failures, []);
});

test("an advisory not in the allowlist fails", () => {
  const { failures } = evaluate(report({ x: adv("x", "GHSA-bbbb") }), [], "2026-11-17");
  assert.equal(failures.length, 1);
  assert.match(failures[0], /GHSA-bbbb/);
});

test("an allowlisted advisory passes until its review date", () => {
  const allow = [{ id: "GHSA-bbbb", package: "x", scope: "dev", reason: "r", reviewBy: "2026-12-01" }];
  assert.deepEqual(evaluate(report({ x: adv("x", "GHSA-bbbb") }), allow, "2026-11-17").failures, []);
  assert.equal(evaluate(report({ x: adv("x", "GHSA-bbbb") }), allow, "2026-12-02").failures.length, 1);
});

test("an allowlist entry without reason or review date is rejected", () => {
  const allow = [{ id: "GHSA-bbbb", package: "x", scope: "dev" }];
  assert.equal(evaluate(report({ x: adv("x", "GHSA-bbbb") }), allow, "2026-11-17").failures.length, 1);
});

test("an allowlist entry that no longer matches is reported as stale, not as a failure", () => {
  const allow = [{ id: "GHSA-old", package: "y", scope: "dev", reason: "r", reviewBy: "2026-12-01" }];
  const res = evaluate(report({}), allow, "2026-11-17");
  assert.deepEqual(res.failures, []);
  assert.deepEqual(res.stale, ["GHSA-old"]);
});
