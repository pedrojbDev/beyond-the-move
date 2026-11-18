// Run against a local Uvicorn instance with Stockfish and the released adapter.
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const { default: puppeteer } = await import(pathToFileURL(resolve(
  process.env.PUPPETEER_MODULE ?? ".local/tools/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js",
)));
const browser = await puppeteer.launch({
  browser: "firefox",
  executablePath: process.env.FIREFOX_PATH ?? "/usr/bin/firefox",
  headless: true,
  env: { ...process.env, MOZ_HEADLESS: "1" },
});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400 && !response.url().endsWith("/favicon.ico")) {
      errors.push(`${response.status()} ${response.url()}`);
    }
  });
  await page.setViewport({ width: 1240, height: 1000 });
  await page.goto(process.env.DEMO_URL ?? "http://127.0.0.1:8000/");
  await page.waitForSelector("#board svg use");
  await page.waitForFunction(() => !document.querySelector("#example").disabled);
  await page.click('#board g[data-piece="bq"][data-square="e5"]');
  await page.click('#board rect[data-square="e2"]');
  await page.waitForFunction(() => document.querySelector("#move-readout").textContent.includes("Qxe2+"));
  async function ask(reason) {
    await page.$eval("#reason", (field, value) => {
      field.value = value;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }, reason);
    await page.click("#ask");
    await page.waitForFunction(() => !document.querySelector("#feedback").hidden, { timeout: 45000 });
    assert.match(await page.$eval("#source", (node) => node.textContent), /MODELO AJUSTADO/);
    return page.$eval("#hint", (node) => node.textContent);
  }
  const first = await ask("Quero trocar as damas para simplificar.");
  const second = await ask("Achei que essa peça estava de graça.");
  assert.notEqual(first, second);
  assert.match(first, /troca/);
  assert.match(second, /recapturar/);
  await page.click("#reveal");
  await page.waitForFunction(() => !document.querySelector("#steps").hidden);
  await page.click("#next");
  await page.click("#next");
  assert.match(await page.$eval("#line", (node) => node.textContent), /Bxe2/);
  await page.waitForSelector('#board g[data-piece="wb"][data-square="e2"] use');
  await mkdir("docs", { recursive: true });
  await page.screenshot({ path: "docs/demo.png", fullPage: true });
  await page.setViewport({ width: 390, height: 844 });
  const geometry = await page.evaluate(() => ({
    fits: document.documentElement.scrollWidth <= 390,
    stacks: document.querySelector(".coach-panel").getBoundingClientRect().top >
      document.querySelector("#board").getBoundingClientRect().bottom,
  }));
  assert.deepEqual(geometry, { fits: true, stacks: true });
  await page.screenshot({ path: "docs/demo-mobile.png", fullPage: true });
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ first, second, geometry, replay: "Qxe2+, Bxe2" }, null, 2));
} finally {
  await browser.close();
}
