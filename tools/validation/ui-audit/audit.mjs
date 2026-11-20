// UX audit of the site with a real browser (Playwright + Chromium): desktop and phone.
//   node audit.mjs [web url] [output dir]
// Walks the site like a visitor, records console errors, blocked or failed requests, horizontal overflow,
// and takes screenshots. Exit code 1 if any defect is found.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { gzipSync } from "node:zlib";

const WEB = (process.argv[2] ?? "http://localhost:8080").replace(/\/+$/, "");
const OUT = process.argv[3] ?? "./shots";
mkdirSync(OUT, { recursive: true });

const defects = [];
const notes = [];
const defect = (where, what) => defects.push(`[${where}] ${what}`);

async function overflow(page, where) {
  const info = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const wide = [];
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.right > vw + 1 || r.left < -1) {
        // An element inside a horizontally scrollable container is allowed to be wider than the screen.
        let p = el.parentElement, scrollable = false;
        while (p && p !== document.body) {
          const ox = getComputedStyle(p).overflowX;
          if (ox === "auto" || ox === "scroll" || ox === "hidden") { scrollable = true; break; }
          p = p.parentElement;
        }
        if (!scrollable) wide.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} right=${Math.round(r.right)}`);
      }
    }
    return { vw, scrollWidth: document.documentElement.scrollWidth, wide: wide.slice(0, 6) };
  });
  if (info.scrollWidth > info.vw + 1) defect(where, `page scrolls sideways: content ${info.scrollWidth}px for a ${info.vw}px screen; ${info.wide.join(", ")}`);
  else if (info.wide.length) defect(where, `elements wider than the screen: ${info.wide.join(", ")}`);
}


// WCAG contrast ratio of two CSS colours "rgb(r, g, b)" or "#rrggbb".
function contrast(a, b) {
  const rgb = (c) => c.startsWith("#") ? [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)) : c.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number);
  const lum = (c) => { const [r, g, b2] = rgb(c).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b2; };
  const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
}

// --- v3 discovery map (T45): states, overlay, panels, comparison, cells, French, ADR-006 budget
async function discovery(page, name, shot) {
  const js = new Map();
  const tiles = [];
  const onResponse = async (r) => {
    const u = r.url();
    if (u.endsWith(".js") && r.status() === 200) js.set(u, (await r.body().catch(() => Buffer.alloc(0))));
    if (u.includes("/api/v3/layers/")) tiles.push(u);
  };
  await page.goto(`${WEB}/`, { waitUntil: "networkidle" });
  const before = new Set(await page.evaluate(() => performance.getEntriesByType("resource").map((e) => e.name).filter((n) => n.endsWith(".js"))));
  page.on("response", onResponse);
  const t0 = Date.now();
  await page.locator(".discover-card").click();
  await page.locator(".v3-zones li").first().waitFor({ timeout: 30000 }).catch(() => defect(name, "discovery: no zone listed"));
  await page.waitForLoadState("networkidle");
  const firstView = Date.now() - t0;
  if (firstView > 2500) defect(name, `discovery: first map view took ${firstView} ms (budget 2,500 ms, ADR-006)`);
  const added = [...js.entries()].filter(([u]) => !before.has(u));
  const kb = added.reduce((s, [, b]) => s + gzipSync(b).length, 0) / 1024;
  if (kb > 60) defect(name, `discovery: ${kb.toFixed(1)} KB gzip of JavaScript added by v3 (budget 60 KB, ADR-006)`);
  if (tiles.length > 40) defect(name, `discovery: ${tiles.length} tile requests for the first view (budget 40, ADR-006)`);
  notes.push(`${name} discovery: first view ${firstView} ms, v3 JavaScript ${kb.toFixed(1)} KB gzip, ${tiles.length} tile requests`);
  for (const cls of ["Screened out", "No data", "Ground hidden", "Partial", "Low confidence", "Evaluated"]) {
    if (!(await page.locator(".v3-legend .legend-label", { hasText: cls }).count())) defect(name, `discovery: legend lacks "${cls}"`);
  }
  const alert = page.locator(".v3-page [role=alert]");
  if (await alert.count()) defect(name, `discovery: error shown: ${(await alert.first().innerText()).slice(0, 200)}`);
  const status = page.locator(".v3-status");
  if (!(await status.count()) || (await status.first().innerText()).match(/validated/i) === null) {
    defect(name, "discovery: no validity indicator");
    return;
  }
  if (!(await page.locator(".v3-layers .v3-disabled", { hasText: "T46" }).count())) defect(name, "discovery: the geology layer is not shown as waiting for T46");
  if (!(await page.locator(".v3-cannot-bar").isVisible())) defect(name, "discovery: the line on what Earth cannot reproduce is not visible");
  // contrast: pastel hatching against the panel (graphics, at least 3:1) and legend text (at least 4.5:1)
  const colours = await page.evaluate(() => {
    const panel = getComputedStyle(document.querySelector(".v3-block")).backgroundColor;
    const label = getComputedStyle(document.querySelector(".legend-label")).color;
    const share = getComputedStyle(document.querySelector(".legend-share")).color;
    return { panel, label, share };
  });
  if (contrast("#b9c6e8", colours.panel) < 3) defect(name, `discovery: pastel hatching contrast ${contrast("#b9c6e8", colours.panel).toFixed(2)} on the panel (needs 3)`);
  for (const [k, c] of [["legend label", colours.label], ["legend share", colours.share]]) {
    if (contrast(c, colours.panel) < 4.5) defect(name, `discovery: ${k} contrast ${contrast(c, colours.panel).toFixed(2)} (needs 4.5)`);
  }
  await overflow(page, `${name} discovery`);
  await shot("07-discovery");
  // overlay switch
  const sw = page.getByRole("switch", { name: "Coverage overlay" });
  await sw.click();
  if ((await sw.getAttribute("aria-checked")) !== "false") defect(name, "discovery: the overlay switch does not turn off");
  await sw.click();
  // Data and method
  await page.getByRole("button", { name: "Data and method" }).click();
  const dialog = page.getByRole("dialog", { name: "Data and method" });
  for (const h of ["What we cover", "Sources used", "How we processed it", "What it cannot say"]) {
    if (!(await dialog.getByRole("heading", { name: h }).count())) defect(name, `Data and method: no "${h}" block`);
  }
  if ((await dialog.locator(".v3-sources > li").count()) < 3) defect(name, "Data and method: fewer than 3 sources");
  await overflow(page, `${name} data and method`);
  await shot("08-data-method", false);
  await page.keyboard.press("Escape");
  // zone card, opened in under 300 ms (data cached)
  const z0 = Date.now();
  await page.locator(".v3-zone-btn").first().click();
  await page.locator(".v3-card").first().waitFor({ timeout: 5000 }).catch(() => defect(name, "discovery: the zone card does not open"));
  const zoneMs = Date.now() - z0;
  if (zoneMs > 300) defect(name, `discovery: zone card opened in ${zoneMs} ms (budget 300 ms, ADR-006)`);
  for (const text of ["Topography (slope)", "not evaluated (T46)", "Earth cannot reproduce", "Confidence"]) {
    if (!(await page.locator(".v3-card").first().getByText(text, { exact: false }).count())) defect(name, `zone card lacks "${text}"`);
  }
  await page.getByRole("button", { name: "Provenance" }).click();
  if (!(await page.getByRole("dialog").getByText("release", { exact: false }).count())) defect(name, "provenance: no release");
  await page.keyboard.press("Escape");
  // cells above zoom 7 (the card flew the map to the zone)
  await page.waitForFunction(() => !document.querySelector(".v3-map-note") && document.querySelectorAll(".v3-map path.v3-cell").length > 20, null, { timeout: 20000 })
    .catch(() => defect(name, "discovery: no cell drawn at zoom 9 around the zone"));
  const hatched = await page.evaluate(() => [...document.querySelectorAll(".v3-map path.v3-hatch")].filter((p) => (p.getAttribute("fill") ?? "").startsWith("url(#pat-")).length);
  await page.locator(".v3-map").scrollIntoViewIfNeeded();
  notes.push(`${name} discovery: ${hatched} hatched cells at the first zone`);
  await overflow(page, `${name} zone card`);
  await shot("09-zone-card");
  // comparison of 2 zones
  const boxes = page.locator(".v3-zones input[type=checkbox]");
  if ((await boxes.count()) >= 2) {
    await boxes.nth(0).check();
    await boxes.nth(1).check();
    await page.getByRole("button", { name: "Compare", exact: true }).click();
    if ((await page.locator(".v3-compare svg[data-strip]").count()) !== 2) defect(name, "comparison: not one strip per zone");
    await overflow(page, `${name} comparison`);
    await shot("10-compare");
  }
  // French
  await page.locator(".lang-switch button", { hasText: "FR" }).click();
  if (!(await page.locator(".v3-head h1").textContent())?.includes("Carte de découverte")) defect(name, "discovery in French: title not translated");
  const fr = await page.locator(".v3-page").innerText();
  for (const english of ["Coverage overlay", "Candidate zones", "Earth cannot reproduce", "Layers", "Not validated"]) {
    if (fr.includes(english)) defect(name, `discovery in French still shows "${english}"`);
  }
  await overflow(page, `${name} discovery (fr)`);
  await page.locator(".lang-switch button", { hasText: "EN" }).click();
  page.off("response", onResponse);
}

async function run(name, viewport, mobile) {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile });
  const page = await context.newPage();
  page.on("console", (m) => { if (m.type() === "error") defect(name, `console error: ${m.text().slice(0, 220)}`); });
  page.on("pageerror", (e) => defect(name, `page error: ${String(e).slice(0, 220)}`));
  page.on("requestfailed", (r) => { if (!r.failure()?.errorText.includes("ERR_ABORTED")) defect(name, `request failed: ${r.url().slice(0, 120)} (${r.failure()?.errorText})`); });
  page.on("response", (r) => { if (r.status() >= 400) defect(name, `HTTP ${r.status()}: ${r.url().slice(0, 120)}`); });
  const shot = (file, full = true) => page.screenshot({ path: `${OUT}/${name}-${file}.png`, fullPage: full });

  // --- Home
  await page.goto(`${WEB}/`, { waitUntil: "networkidle" });
  const cards = page.locator(".mission-card");
  if ((await cards.count()) !== 4) defect(name, `home: ${await cards.count()} mission cards instead of 4`);
  const broken = await page.evaluate(() => [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src));
  if (broken.length) defect(name, `home: broken images ${broken.join(", ")}`);
  await overflow(page, `${name} home`);
  await shot("01-home");

  // --- French interface: switch, content, memory of the choice, then back to English (the default)
  if ((await page.locator("html").getAttribute("lang")) !== "en") defect(name, "the site does not open in English by default");
  await page.locator(".lang-switch button", { hasText: "FR" }).click();
  if (!(await page.locator(".hero-copy h1").textContent())?.includes("Trouver la Lune")) defect(name, "FR switch: the home title is not in French");
  if ((await page.locator("html").getAttribute("lang")) !== "fr") defect(name, "FR switch: <html lang> is not fr");
  await overflow(page, `${name} home (fr)`);
  await page.locator(".mission-card").nth(2).click();
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  await page.waitForLoadState("networkidle");
  const frText = await page.locator("main").innerText();
  for (const english of ["Ranking", "Analog score", "Matches", "Earth site", "Lunar south pole", "Known analog", "Candidate to validate",
    "Rank stability", "See the match", "Cannot be reproduced", "Not reproducible", "Mean slope", "Gravity", "Data sources", "All missions"]) {
    if (frText.includes(english)) defect(name, `French interface still shows "${english}"`);
  }
  if (!frText.includes("Vallées sèches de McMurdo")) defect(name, "French interface: site names are not translated");
  await overflow(page, `${name} colony (fr)`);
  await shot("06-colony-fr");
  await page.reload({ waitUntil: "networkidle" });
  if ((await page.locator("html").getAttribute("lang")) !== "fr") defect(name, "the language choice is not remembered after a reload");
  await page.locator(".lang-switch button", { hasText: "EN" }).click();
  if (!(await page.locator("main").innerText()).includes("Ranking")) defect(name, "EN switch does not bring English back");

  // --- Each preset mission
  for (const [index, mode] of ["robotics", "calibration", "colony"].entries()) {
    await page.goto(`${WEB}/`, { waitUntil: "networkidle" });
    await page.locator(".mission-card").nth(index).click();
    await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
    await page.waitForLoadState("networkidle");
    const rows = await page.locator(".rank-row").count();
    if (rows < 30) defect(name, `${mode}: only ${rows} sites in the ranking`);
    const dots = await page.locator(".rank-row .stab").count();
    if (dots < 25) defect(name, `${mode}: stability dots on ${dots} rows only`);
    // NASA GIBS is a third-party service and can be slow: wait up to 45 s for two loaded tiles. A blocked
    // request (CSP, wrong URL) still fails, because no tile ever loads.
    await page
      .waitForFunction(() => [...document.querySelectorAll("img.leaflet-tile")].filter((i) => i.complete && i.naturalWidth > 0).length >= 2, null, { timeout: 45000 })
      .catch(() => undefined);
    const tiles = await page.evaluate(() => [...document.querySelectorAll("img.leaflet-tile")].filter((i) => i.complete && i.naturalWidth > 0).length);
    if (tiles < 2) defect(name, `${mode}: NASA base map tiles not loaded (${tiles})`);
    if (!(await page.locator(".site-detail h2").first().isVisible())) defect(name, `${mode}: no site card after the analysis`);
    const brokenSite = await page.evaluate(() => [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src.split("/").slice(-2).join("/")));
    if (brokenSite.length) defect(name, `${mode}: broken images ${brokenSite.slice(0, 4).join(", ")}`);
    const emptyCells = await page.evaluate(() => [...document.querySelectorAll(".scorecard tbody td")].filter((td) => td.textContent.trim() === "" && !td.querySelector(".match-bar")).length);
    if (emptyCells) defect(name, `${mode}: ${emptyCells} empty cells in the scorecard`);
    await overflow(page, `${name} ${mode}`);
    notes.push(`${name} ${mode}: ${rows} sites, first = ${(await page.locator(".rank-row strong").first().textContent())?.trim()}`);
  }

  // --- Colony: open a penalized site, use the comparator
  await page.goto(`${WEB}/#colony`, { waitUntil: "networkidle" });
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  const popigai = page.locator(".rank-row", { hasText: "Popigai" });
  await popigai.scrollIntoViewIfNeeded();
  await popigai.click();
  await page.waitForLoadState("networkidle");
  const title = (await page.locator(".site-detail h2").textContent())?.trim();
  if (!title?.includes("Popigai")) defect(name, `selecting a site did not open its card (got "${title}")`);
  if (!(await page.locator(".confidence").textContent())?.includes("Vegetation")) defect(name, "Popigai: vegetation note missing");
  const slider = page.locator(".fader input");
  await slider.scrollIntoViewIfNeeded();
  await slider.fill("70");
  const moonOpacity = await page.evaluate(() => getComputedStyle(document.querySelectorAll(".stage-layer")[2]).opacity);
  if (Math.abs(Number(moonOpacity) - 0.7) > 0.05) defect(name, `crossfade slider does not drive the Moon layer (opacity ${moonOpacity})`);
  await page.getByRole("button", { name: "Relief" }).click();
  const src = await page.locator(".stage-layer").first().getAttribute("src");
  if (!src?.includes("earth-relief")) defect(name, "Relief button does not switch the Earth layer");
  await page.locator(".stage-controls input[type=checkbox]").uncheck();
  if (await page.locator(".stage-mask").count()) defect(name, "highlight checkbox does not remove the overlay");
  await page.locator(".stage-controls input[type=checkbox]").check();
  await overflow(page, `${name} colony site card`);
  await shot("02-colony-popigai");

  // --- Amazon stays excluded and last; unchecking the filter brings it back
  const last = page.locator(".rank-row").last();
  if (!(await last.textContent())?.includes("Excluded")) defect(name, "the Amazon negative control is not last and excluded");
  await page.locator("#bare-soil").uncheck();
  await page.waitForFunction(() => document.querySelectorAll(".rank-row").length > 30 && !document.querySelector(".rank-row.is-excluded"), null, { timeout: 30000 })
    .catch(() => defect(name, "filter off: a site is still excluded"));
  await page.locator("#bare-soil").check();
  await page.waitForLoadState("networkidle");

  // --- Calibration: instrument filter
  await page.goto(`${WEB}/#calibration`, { waitUntil: "networkidle" });
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  await page.locator("#instrument").selectOption("seismograph");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(400);
  const criteriaRows = await page.locator(".scorecard tbody").first().locator("tr").count();
  if (criteriaRows !== 1) defect(name, `seismometer filter: ${criteriaRows} criteria rows instead of 1`);
  await page.locator("#instrument").selectOption("all");
  await page.waitForLoadState("networkidle");
  await shot("03-calibration", false);

  // --- Free criteria: invalid input, then a real run
  await page.goto(`${WEB}/#custom`, { waitUntil: "networkidle" });
  await page.locator("#criterion-min-0").waitFor({ timeout: 30000 });
  await page.locator("#criterion-min-0").fill("");
  await page.locator("#criterion-max-0").fill("");
  await page.getByRole("button", { name: /Run analysis/ }).click();
  if (!(await page.locator(".builder .note-error").isVisible())) defect(name, "free criteria: no message for an empty range");
  await page.locator("#criterion-max-0").fill("5");
  await page.getByRole("button", { name: /Add a criterion/ }).click();
  await page.locator("#criterion-param-1").selectOption("t2m_mean");
  await page.locator("#criterion-max-1").fill("-10");
  await page.locator("#criterion-tolerance-1").fill("10");
  await page.getByRole("button", { name: /Run analysis/ }).click();
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  await page.waitForLoadState("networkidle");
  const customCriteria = await page.locator(".scorecard tbody").first().locator("tr").count();
  if (customCriteria !== 2) defect(name, `free criteria: ${customCriteria} criteria in the card instead of 2`);
  await overflow(page, `${name} free criteria`);
  await shot("04-custom");

  // --- Browser Back button returns to the missions; a changed address updates the screen
  await page.goto(`${WEB}/`, { waitUntil: "networkidle" });
  await page.locator(".mission-card").first().click();
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  await page.goBack();
  await page.waitForTimeout(300);
  if ((await page.locator(".mission-card").count()) !== 4) defect(name, "browser Back button does not return to the missions");
  await page.goForward();
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  await page.evaluate(() => { window.location.hash = "#colony/tunnunik"; });
  await page.locator(".site-detail h2", { hasText: "Tunnunik" }).waitFor({ timeout: 60000 }).catch(() => defect(name, "changing the address in the same tab does not change the screen"));

  // --- Back to the missions, and a direct link
  await page.locator(".back").click();
  if ((await page.locator(".mission-card").count()) !== 4) defect(name, "\"All missions\" does not return to the home page");
  await page.goto(`${WEB}/#robotics/atacama`, { waitUntil: "networkidle" });
  await page.locator(".site-detail h2").waitFor({ timeout: 60000 });
  if (!(await page.locator(".site-detail h2").textContent())?.includes("Atacama")) defect(name, "direct link #robotics/atacama does not open Atacama");
  await page.waitForLoadState("networkidle");
  await overflow(page, `${name} robotics site card`);
  await shot("05-robotics-atacama");
  await discovery(page, name, shot);
  await browser.close();
}

await run("desktop", { width: 1440, height: 900 }, false);
// The API allows 120 requests per minute and per IP: the two passes act as two visitors, one window apart.
await new Promise((resolve) => setTimeout(resolve, 61_000));
await run("phone", { width: 390, height: 844 }, true);

for (const n of notes) console.log("note  ", n);
const unique = [...new Set(defects)];
for (const d of unique) console.log("DEFECT", d);
console.log(`\n${unique.length} defect(s) found`);
process.exit(unique.length ? 1 : 0);
