// Run against local Uvicorn with Stockfish; no model download is needed.
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
  await page.waitForFunction(() => document.querySelector("#turn").textContent.includes("Sua vez · brancas"));

  async function ask(reason) {
    await page.$eval("#reason", (field, value) => {
      field.value = value;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }, reason);
    await page.click("#ask");
    await page.waitForFunction(() => !document.querySelector("#feedback").hidden);
    return page.$eval("#hint", (node) => node.textContent);
  }

  await page.click('#board g[data-piece="wb"][data-square="f1"]');
  await page.waitForFunction(() => document.querySelector("#piece").value === "f1");
  assert.match(await ask("O que faço com esse bispo agora?"), /bispo em f1 não tem lance legal/);
  await page.click('#board g[data-piece="wp"][data-square="e2"]');
  await page.click('#board rect[data-square="e4"]');
  await page.waitForFunction(() => document.querySelector("#move-readout").textContent.includes("Bot jogou"));
  await page.waitForSelector('#board g[data-piece="wp"][data-square="e4"] use');
  assert.match(await page.$eval("#turn", (node) => node.textContent), /Sua vez · brancas/);
  await page.click('#board g[data-piece="wb"][data-square="f1"]');
  assert.match(await ask("O que faço com esse bispo agora?"), /bispo em f1, analise/);
  await page.waitForSelector("#board .arrow-success");
  await mkdir("docs", { recursive: true });
  await page.screenshot({ path: "docs/coach-game.png", fullPage: true });

  await page.select("#side", "black");
  await page.waitForFunction(() => document.querySelector("#turn").textContent.includes("Sua vez · pretas"));
  assert.match(await page.$eval("#move-readout", (node) => node.textContent), /Bot jogou/);

  await page.select("#cases", "queen-trade");
  await page.waitForFunction(() => !document.querySelector("#play").disabled &&
    [...document.querySelector("#keyboard-move").options].some(({ value }) => value === "c8f5"));
  assert.deepEqual(await page.select("#keyboard-move", "c8f5"), ["c8f5"]);
  await page.click("#play");
  await page.waitForFunction(() => document.querySelector("#move-readout").textContent.includes("Bf5"));
  const advice = await ask("O que fazer com o bispo depois?");
  assert.match(advice, /bispo em f5.*dama com Qxe5/);
  await page.waitForSelector("#board .arrow-danger");
  await page.click("#reveal");
  await page.waitForFunction(() => !document.querySelector("#steps").hidden);
  await page.click("#next");
  await page.waitForFunction(() => document.querySelector("#line").textContent.includes("Qxe5"));
  assert.doesNotMatch(await ask("O que fazer com o bispo depois?"), /dama com Qxe5/);

  await page.setViewport({ width: 390, height: 844 });
  const geometry = await page.evaluate(() => ({
    fits: document.documentElement.scrollWidth <= 390,
    stacks: document.querySelector(".coach-panel").getBoundingClientRect().top >
      document.querySelector("#board").getBoundingClientRect().bottom,
  }));
  assert.deepEqual(geometry, { fits: true, stacks: true });
  await page.screenshot({ path: "docs/coach-mobile.png", fullPage: true });
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ advice, geometry, black: "bot opened", replay: "Bf5 Qxe5" }, null, 2));
} finally {
  await browser.close();
}
