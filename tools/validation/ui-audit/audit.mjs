// UX audit of the site with a real browser (Playwright + Chromium): desktop and phone.
//   node audit.mjs [web url] [output dir]
// Walks the site like a visitor, records console errors, blocked or failed requests, horizontal overflow,
// and takes screenshots. Exit code 1 if any defect is found.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

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
    await page.locator("img.leaflet-tile-loaded").first().waitFor({ timeout: 20000 }).catch(() => undefined);
    await page.waitForLoadState("networkidle");
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
  await browser.close();
}

await run("desktop", { width: 1440, height: 900 }, false);
await run("phone", { width: 390, height: 844 }, true);

for (const n of notes) console.log("note  ", n);
const unique = [...new Set(defects)];
for (const d of unique) console.log("DEFECT", d);
console.log(`\n${unique.length} defect(s) found`);
process.exit(unique.length ? 1 : 0);
