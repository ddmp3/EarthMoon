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

const MISSIONS = 4;                                          // four missions per body: the Moon, or Mars (T45c)

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

// --- v3 inside the missions (T45b): site marks, site card section, zones tab, zone card, comparison, cells, search,
// French, contrast, ADR-006 budget. JavaScript of the v2 pages before v3 (main at cdfba91): 128.2 KB gzip.
const JS_BEFORE_V3_KB = 128.2;
async function discovery(page, name, shot) {
  const tiles = [];
  const js = new Map();
  const onResponse = async (r) => {
    const u = r.url();
    if (u.includes("/api/v3/layers/")) tiles.push(u);
    if (u.endsWith(".js") && r.status() === 200) js.set(u, await r.body().catch(() => Buffer.alloc(0)));
  };
  // The API allows 120 requests per minute and per IP: this part starts on a fresh window, as a new visitor would.
  await new Promise((resolve) => setTimeout(resolve, 61_000));
  await page.goto(`${WEB}/`, { waitUntil: "networkidle" });
  page.on("response", onResponse);
  const t0 = Date.now();
  await page.goto(`${WEB}/#robotics/atacama`);
  await page.reload({ waitUntil: "networkidle" });            // a hash change alone would not load the page again
  await page.locator(".site-detail h2").waitFor({ timeout: 60000 });
  await page.locator(".v3-chip").first().waitFor({ timeout: 20000 }).catch(() => defect(name, "robotics: no v3 mark on the ranked sites"));
  const firstView = Date.now() - t0;
  if (firstView > 2500) defect(name, `robotics with v3: first view took ${firstView} ms (budget 2,500 ms, ADR-006)`);
  const kb = [...js.values()].reduce((s, b) => s + gzipSync(b).length, 0) / 1024;
  if (kb - JS_BEFORE_V3_KB > 60) defect(name, `${(kb - JS_BEFORE_V3_KB).toFixed(1)} KB gzip of JavaScript added by v3 (budget 60 KB, ADR-006)`);
  if (tiles.length > 40) defect(name, `robotics: ${tiles.length} v3 tile requests for the first view (budget 40, ADR-006)`);
  notes.push(`${name} v3 in robotics: first view ${firstView} ms, JavaScript ${kb.toFixed(1)} KB gzip (+${(kb - JS_BEFORE_V3_KB).toFixed(1)} for v3), ${tiles.length} tile requests`);
  for (const id of ["v3-env", "v3-overlay"]) if (!(await page.locator(`#${id}`).count())) defect(name, `robotics: no #${id} control`);
  if (!(await page.locator(".v3-statusline").innerText()).match(/validated/i)) defect(name, "robotics: no validity line");
  const section = page.locator(".v3-site");
  if (!(await section.count())) defect(name, "site card: no v3 section");
  else if ((await section.locator("tbody tr").count()) < 2 && !(await section.getByText(/Not assessed at this place/).count())) {
    defect(name, "site card: v3 section with neither one row per environment nor the reason");
  }
  const legend = page.locator(".map-legend");
  for (const cls of ["Screened out", "No data", "Ground hidden", "Partial", "Low confidence", "Evaluated"]) {
    if (!(await legend.locator(".legend-label", { hasText: cls }).count())) defect(name, `map legend lacks "${cls}"`);
  }
  const panel = await page.evaluate(() => getComputedStyle(document.querySelector(".ranking")).backgroundColor);
  if (contrast("#b9c6e8", panel) < 3) defect(name, `pastel hatching contrast ${contrast("#b9c6e8", panel).toFixed(2)} on the panel (needs 3)`);
  await overflow(page, `${name} robotics v3`);
  await shot("07-robotics-v3");
  // geology layer (T46): picker, legend, site card column
  await page.locator("#v3-layer").selectOption("geology");
  if (!(await legend.getByText("Same rock family (match)").count())) defect(name, "geology layer: no geology legend");
  if ((await section.locator("table").count()) && !(await section.getByRole("columnheader", { name: "Geology" }).count())) {
    defect(name, "site card: no geology column");
  }
  await page.locator("#v3-layer").selectOption("frozen");
  if (!(await legend.getByText(/Frozen ground for drilling/).count())) defect(name, "frozen layer: no legend");
  if (!(await legend.getByText(/Not a comparison with the Moon/).count())) defect(name, "frozen layer: not labelled as Earth context");
  await page.locator("#v3-layer").selectOption("topography");
  // Data and method from the site card
  await section.getByRole("button", { name: "Data and method" }).click();
  const dialog = page.getByRole("dialog", { name: "Data and method" });
  for (const h of ["What we cover", "Sources used", "How we processed it", "What it cannot say"]) {
    if (!(await dialog.getByRole("heading", { name: h }).count())) defect(name, `Data and method: no "${h}" block`);
  }
  await overflow(page, `${name} data and method`);
  await shot("08-data-method", false);
  await page.keyboard.press("Escape");
  // zones tab, zone card in under 300 ms, cells at zoom 9
  await page.getByRole("tab", { name: /Discovered zones/ }).click();
  await page.locator(".zone-row").first().waitFor({ timeout: 20000 }).catch(() => defect(name, "zones tab: no zone listed"));
  const z0 = Date.now();
  await page.locator(".zone-row").first().click();
  await page.locator(".v3-under .v3-card").waitFor({ timeout: 5000 }).catch(() => defect(name, "the zone card does not open"));
  const zoneMs = Date.now() - z0;
  if (zoneMs > 300) defect(name, `zone card opened in ${zoneMs} ms (budget 300 ms, ADR-006)`);
  for (const text of ["Topography (slope)", "Geology", "Earth cannot reproduce", "Confidence"]) {
    if (!(await page.locator(".v3-under .v3-card").getByText(text, { exact: false }).count())) defect(name, `zone card lacks "${text}"`);
  }
  if (!(await page.locator(".v3-under .v3-card").getByText(/% match · .*% partial/).count())) defect(name, "zone card: geology without its shares");
  await page.waitForFunction(() => document.querySelectorAll(".map-wrap path.v3-cell").length > 20, null, { timeout: 20000 })
    .catch(() => defect(name, "no cell drawn at zoom 9 around the zone"));
  notes.push(`${name} zone: ${await page.locator(".map-wrap path.v3-hatch[fill^='url']").count()} hatched cells around it`);
  await page.getByRole("button", { name: "Provenance" }).click();
  if (!(await page.getByRole("dialog").getByText("release", { exact: false }).count())) defect(name, "provenance: no release");
  await page.keyboard.press("Escape");
  await page.locator(".explore").scrollIntoViewIfNeeded();
  await overflow(page, `${name} zone card`);
  await shot("09-zone-card");
  const boxes = page.locator(".zone-pick");
  if ((await boxes.count()) >= 2) {
    await boxes.nth(0).check();
    await boxes.nth(1).check();
    await page.getByRole("button", { name: /^Compare/ }).click();
    if ((await page.locator(".v3-compare svg[data-strip]").count()) !== 2) defect(name, "comparison: not one strip per zone");
    await overflow(page, `${name} comparison`);
    await shot("10-compare");
  }
  // mission 4: the search of the whole Earth, then French
  await page.goto(`${WEB}/#custom`, { waitUntil: "networkidle" });
  await page.locator(".v3-search").waitFor({ timeout: 20000 }).catch(() => defect(name, "free criteria: no v3 search"));
  await page.locator(".zone-row").first().waitFor({ timeout: 20000 }).catch(() => defect(name, "free criteria: the map and zones are not shown before a v2 run"));
  await page.locator("#v3-min-typicality").fill("0.5");
  await page.locator("#v3-min-confidence").selectOption("low");
  await page.getByRole("button", { name: /Search in this view/ }).click();
  await page.getByRole("tab", { name: /Search results/ }).waitFor({ timeout: 20000 }).catch(() => defect(name, "free criteria: the search gave no result tab"));
  notes.push(`${name} search: ${(await page.locator(".v3-search [role=status]").innerText().catch(() => "no message")).slice(0, 90)}`);
  await overflow(page, `${name} free criteria v3`);
  await shot("11-custom-v3");
  await page.locator(".lang-switch button", { hasText: "FR" }).click();
  const fr = await page.locator("main").innerText();
  for (const english of ["Coverage overlay", "Discovered zones", "Search the whole Earth", "Lunar environment", "Not validated", "Data and method",
    "Slope a crewed lunar rover", "Robotic lunar exploration", "Minimum typicality"]) {
    if (fr.includes(english)) defect(name, `French interface still shows "${english}"`);
  }
  await overflow(page, `${name} free criteria (fr)`);
  await shot("12-custom-fr");
  await page.locator(".lang-switch button", { hasText: "EN" }).click();
  // Mars mode (T45c): the body switch turns the whole site to Mars (its own home, colours and terrains), then the
  // Mars mission, scenario D from the Mars release, then French. A fresh rate-limit window, as a new visitor.
  await new Promise((resolve) => setTimeout(resolve, 61_000));
  await page.goto(`${WEB}/`, { waitUntil: "networkidle" });
  await page.locator(".body-switch button", { hasText: "Mars" }).click();
  if ((await page.locator("html").getAttribute("data-body")) !== "mars") defect(name, "Earth-Mars chip: the site is not in its Mars mode");
  if (!(await page.locator(".hero-copy h1").textContent())?.includes("Find Mars")) defect(name, "Mars home: the title is not the Mars one");
  if ((await page.locator(".mission-card").count()) !== MISSIONS) defect(name, `Mars home: ${await page.locator(".mission-card").count()} cards instead of ${MISSIONS}`);
  const marsBroken = await page.evaluate(() => [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src));
  if (marsBroken.length) defect(name, `Mars home: broken images ${marsBroken.join(", ")}`);
  await page.locator(".figures dt").first().waitFor({ timeout: 15000 }).catch(() => undefined);   // the Mars release loads after the switch
  if ((await page.locator(".figures dt").count()) !== 4) defect(name, "Mars home: the figures of the Mars release are missing");
  await overflow(page, `${name} Mars home`);
  await shot("13a-mars-home");
  if (!page.url().endsWith("#mars-home")) defect(name, `Mars home address is ${page.url()}`);
  await page.locator(".mission-card").nth(1).click();
  await page.locator(".zone-row").first().waitFor({ timeout: 20000 }).catch(() => defect(name, "Mars: no zone list"));
  const envs = await page.locator("#v3-env option").allInnerTexts();
  if (!envs.some((e) => e.includes("North polar terrain"))) defect(name, `Mars: environments are ${envs.join(", ").slice(0, 120)}`);
  if (envs.some((e) => /lunar|Mare|shadowed/i.test(e))) defect(name, "Mars: a lunar environment is offered");
  if (await page.locator("#bare-soil").count()) defect(name, "Mars: the v2 bare-soil filter is shown");
  await overflow(page, `${name} Mars`);
  if (((await page.locator("#v3-env").inputValue().catch(() => "")) || "") !== "mars-north-polar") defect(name, "Mars: the terrain picked on the home is not selected");
  if (!((await page.locator(".mission-banner h1").textContent()) || "").includes("North polar terrain")) defect(name, "Mars: the banner does not show the terrain picked");
  if (!((await page.locator(".mission-banner img").getAttribute("src")) || "").endsWith("/mars.jpg")) defect(name, "Mars: the banner photo is not the terrain's");
  await page.locator("#v3-env").selectOption("mars-south-polar");
  if (!((await page.locator(".mission-banner img").getAttribute("src")) || "").endsWith("/mars-south.jpg")) defect(name, "Mars: the banner does not follow a terrain changed in the mission");
  await page.locator("#v3-env").selectOption("mars-north-polar");
  await shot("13-mars");
  // T45c part 2: the Mars globe beside the map, linked both ways with the Earth zones
  await page.locator("canvas.planet-globe-canvas").waitFor({ timeout: 20000 }).catch(() => defect(name, "Mars: no 3D globe beside the map"));
  if (/^\d/.test(((await page.locator(".zone-row strong").first().textContent()) || "").trim())) defect(name, "Mars: the zone list shows coordinates, not a place name");
  await page.locator(".zone-row").first().click();
  await page.locator(".planet-caption").waitFor({ timeout: 10000 }).catch(() => defect(name, "Mars: selecting a zone does not light the same-slope windows"));
  const globe = page.locator("canvas.planet-globe-canvas");
  await globe.scrollIntoViewIfNeeded();
  const box = await globe.boundingBox();
  if (box) {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await page.locator(".planet-point").waitFor({ timeout: 10000 }).catch(() => defect(name, "Mars: a click on the globe lists no Earth zone"));
  }
  await shot("13b-mars-globe");
  // zooming past the tiles with the layer on: a view of more than 5,000 cells says "zoom in", never an error
  for (let k = 0; k < 6; k++) {
    await page.locator(".map-wrap .leaflet-control-zoom-in").click().catch(() => undefined);
    await page.waitForTimeout(350);
  }
  await page.waitForTimeout(2500);
  if (await page.locator(".map-wrap .map-note-error").count()) defect(name, `Mars: zooming shows an error: ${(await page.locator(".map-wrap .map-note-error").innerText()).slice(0, 120)}`);
  await page.locator(".v3-under").waitFor({ timeout: 10000 }).catch(() => defect(name, "Mars: the zone card does not open"));
  await shot("14-mars-zone");
  await page.locator(".lang-switch button", { hasText: "FR" }).click();
  const frMars = await page.locator("main").innerText();
  for (const english of ["Martian environment", "North polar terrain", "Mars analogs", "Discovered zones", "Data and method", "Lunar environment"]) {
    if (frMars.includes(english)) defect(name, `French Mars mission still shows "${english}"`);
  }
  await overflow(page, `${name} Mars (fr)`);
  await shot("15-mars-fr");
  await page.locator(".lang-switch button", { hasText: "EN" }).click();
  // back to the Moon: the whole site returns to its lunar mode
  await page.locator(".brand").click();
  await page.locator(".body-switch button", { hasText: "Moon" }).click();
  if ((await page.locator("html").getAttribute("data-body")) !== "moon") defect(name, "Earth-Moon chip: the site does not return to its Moon mode");
  if (!(await page.locator(".hero-copy h1").textContent())?.includes("Find the Moon")) defect(name, "Moon home: the title is not the lunar one");
  // the old address of the separate page opens mission 4
  await page.goto(`${WEB}/#discover`, { waitUntil: "networkidle" });
  if (!(await page.locator(".v3-search").count())) defect(name, "#discover does not open the free-criteria mission");
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
  if ((await cards.count()) !== MISSIONS) defect(name, `home: ${await cards.count()} mission cards instead of ${MISSIONS}`);
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
  if ((await page.locator(".mission-card").count()) !== MISSIONS) defect(name, "browser Back button does not return to the missions");
  await page.goForward();
  await page.locator(".rank-row").first().waitFor({ timeout: 60000 });
  await page.evaluate(() => { window.location.hash = "#colony/tunnunik"; });
  await page.locator(".site-detail h2", { hasText: "Tunnunik" }).waitFor({ timeout: 60000 }).catch(() => defect(name, "changing the address in the same tab does not change the screen"));

  // --- Back to the missions, and a direct link
  await page.locator(".back").click();
  if ((await page.locator(".mission-card").count()) !== MISSIONS) defect(name, "\"All missions\" does not return to the home page");
  await page.goto(`${WEB}/#robotics/atacama`, { waitUntil: "networkidle" });
  await page.locator(".site-detail h2").waitFor({ timeout: 60000 });
  if (!(await page.locator(".site-detail h2").textContent())?.includes("Atacama")) defect(name, "direct link #robotics/atacama does not open Atacama");
  await page.waitForLoadState("networkidle");
  await overflow(page, `${name} robotics site card`);
  await shot("05-robotics-atacama");
  await discovery(page, name, shot);
  await browser.close();
}

// e2e.py runs just before on the same IP: start on a fresh window of the API rate limit.
await new Promise((resolve) => setTimeout(resolve, 61_000));
await run("desktop", { width: 1440, height: 900 }, false);
// The API allows 120 requests per minute and per IP: the two passes act as two visitors, one window apart.
await new Promise((resolve) => setTimeout(resolve, 61_000));
await run("phone", { width: 390, height: 844 }, true);

for (const n of notes) console.log("note  ", n);
const unique = [...new Set(defects)];
for (const d of unique) console.log("DEFECT", d);
console.log(`\n${unique.length} defect(s) found`);
process.exit(unique.length ? 1 : 0);
