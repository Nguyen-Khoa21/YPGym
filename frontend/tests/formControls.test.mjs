import assert from "node:assert/strict";
import test from "node:test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { buildSync } from "esbuild";

// Form.tsx is TSX with an "@/" alias, which node cannot load directly. Bundle it once for the test.
const cacheDir = fileURLToPath(new URL("../node_modules/.cache/form-test/", import.meta.url));
mkdirSync(cacheDir, { recursive: true });
const outfile = join(cacheDir, "Form.mjs");
buildSync({
  entryPoints: [fileURLToPath(new URL("../src/components/ui/Form.tsx", import.meta.url))],
  outfile,
  bundle: true,
  format: "esm",
  platform: "node",
  jsx: "automatic",
  external: ["react", "react/jsx-runtime", "react-dom"],
  alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
  logLevel: "error",
});
const { Field, FieldError, Input, Label, Textarea } = await import(pathToFileURL(outfile).href);

const attr = (html, tag, name) => new RegExp(`<${tag}[^>]*? ${name}="([^"]*)"`).exec(html)?.[1];

test("Textarea matches Input: full width, card background, focus ring, disabled state", () => {
  const input = renderToStaticMarkup(h(Input));
  const area = renderToStaticMarkup(h(Textarea));
  for (const token of ["w-full", "bg-card", "border-input", "rounded-md", "focus:ring-2", "disabled:cursor-not-allowed", "placeholder:text-muted-foreground"]) {
    assert.ok(input.includes(token), `Input ${token}`);
    assert.ok(area.includes(token), `Textarea ${token}`);
  }
  assert.ok(area.includes("min-h-28") && area.includes("resize-y"));
});

test("a label points at its control without any call-site ids", () => {
  const html = renderToStaticMarkup(h(Field, null, h(Label, null, "Title"), h(Input), h(FieldError, { message: undefined })));
  const labelFor = attr(html, "label", "for");
  const inputId = attr(html, "input", "id");
  assert.ok(labelFor);
  assert.equal(labelFor, inputId);
  assert.equal(attr(html, "input", "aria-invalid"), undefined);
});

test("two fields never share an id", () => {
  const html = renderToStaticMarkup(h("div", null,
    h(Field, null, h(Label, null, "A"), h(Input)),
    h(Field, null, h(Label, null, "B"), h(Textarea))));
  const ids = [...html.matchAll(/ id="([^"]+)"/g)].map((match) => match[1]);
  assert.equal(new Set(ids).size, ids.length);
});

test("an explicit id on the control is kept and the label follows it", () => {
  const html = renderToStaticMarkup(h(Field, null, h(Label, { htmlFor: "email" }, "Email"), h(Input, { id: "email" })));
  assert.equal(attr(html, "label", "for"), "email");
  assert.equal(attr(html, "input", "id"), "email");
});

test("the error message has an id that the control can reference", () => {
  const html = renderToStaticMarkup(h(Field, null, h(Label, null, "Title"), h(Textarea), h(FieldError, { message: "Required." })));
  const errorId = attr(html, "p", "id");
  assert.ok(errorId && errorId.endsWith("-error"));
  assert.ok(html.includes("Required."));
});
