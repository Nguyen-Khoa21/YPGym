import assert from "node:assert/strict";
import test from "node:test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { buildSync } from "esbuild";

// QueryState.tsx is TSX with an "@/" alias, which node cannot load directly. Bundle it for the test.
const cacheDir = fileURLToPath(new URL("../node_modules/.cache/query-state-test/", import.meta.url));
mkdirSync(cacheDir, { recursive: true });
const outfile = join(cacheDir, "QueryState.mjs");
buildSync({
  entryPoints: [fileURLToPath(new URL("../src/components/common/QueryState.tsx", import.meta.url))],
  outfile,
  bundle: true,
  format: "esm",
  platform: "node",
  jsx: "automatic",
  packages: "external",
  alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
  logLevel: "error",
});
const { QueryState } = await import(pathToFileURL(outfile).href);

const idle = { data: undefined, isLoading: false, isError: false, error: null, refetch() {} };
const loading = { title: "Loading rows", message: "Fetching the rows." };
const empty = { title: "No rows", message: "Add one." };
const render = (query, props = {}) =>
  renderToStaticMarkup(
    h(QueryState, { query, loading, empty, isEmpty: (d) => d.length === 0, ...props }, (d) =>
      h("ul", null, d.map((row) => h("li", { key: row }, row))),
    ),
  );

test("shows only the loading panel while the first request is in flight", () => {
  const html = render({ ...idle, isLoading: true }, { className: "m-4" });
  assert.ok(html.includes("Loading rows") && html.includes("Fetching the rows."));
  assert.ok(html.includes("m-4"));
  assert.ok(!html.includes("No rows") && !html.includes("<ul>"));
});

test("renders nothing for a query that is disabled and has no data yet", () => {
  assert.equal(render(idle), "");
});

test("shows the error without a Retry button unless retry is requested", () => {
  const html = render({ ...idle, isError: true, error: new Error("boom") });
  assert.ok(html.includes('role="alert"'));
  assert.ok(!html.includes("<button"));
});

test("retry shows a button with the default or a custom label", () => {
  const failed = { ...idle, isError: true, error: new Error("boom") };
  assert.ok(render(failed, { retry: true }).includes(">Retry</button>"));
  assert.ok(render(failed, { retry: "Check access again" }).includes(">Check access again</button>"));
});

test("shows the empty state once data has loaded and is empty, and hides the children", () => {
  const html = render({ ...idle, data: [] });
  assert.ok(html.includes("No rows") && html.includes("Add one."));
  assert.ok(!html.includes("<ul>"));
});

test("renders the children for loaded data", () => {
  const html = render({ ...idle, data: ["Yoga", "HIIT"] });
  assert.ok(html.includes("<li>Yoga</li>") && html.includes("<li>HIIT</li>"));
  assert.ok(!html.includes("No rows"));
});

test("a failed refetch keeps the stale data on screen next to the error", () => {
  const html = render({ ...idle, data: ["Yoga"], isError: true, error: new Error("boom") });
  assert.ok(html.includes('role="alert"') && html.includes("<li>Yoga</li>"));
});

test("without an empty config, empty data still reaches the children", () => {
  const html = renderToStaticMarkup(
    h(QueryState, { query: { ...idle, data: [] }, loading }, (d) => h("p", null, `${d.length} rows`)),
  );
  assert.ok(html.includes("0 rows"));
});
