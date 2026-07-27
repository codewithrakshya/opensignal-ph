import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the surveillance workspace", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>OpenSignal PH \| Safety Surveillance<\/title>/i);
  assert.match(html, /Review what changed/);
  assert.match(html, /Potential signals/);
  assert.match(html, /Data fitness/);
  assert.match(html, /Walk-forward backtest/);
  assert.match(html, /do not establish causality/i);
  assert.match(html, /og\.png/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});

test("removes starter assets and preserves accessible controls", async () => {
  const [dashboard, packageJson] = await Promise.all([
    readFile(
      new URL("../app/surveillance-dashboard.tsx", import.meta.url),
      "utf8",
    ),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(dashboard, /aria-label="Responsible-use notice"/);
  assert.match(dashboard, /aria-live="polite"/);
  assert.match(dashboard, /role="status"/);
  assert.match(dashboard, /Download analysis bundle/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  await assert.rejects(
    access(new URL("../app/_sites-preview", import.meta.url)),
  );
});
