// The pages are built from components (dukaan_dost/webpage.py). These tests need the page as the browser gets it,
// so they ask the same composer the server uses, instead of keeping a second copy of its rules here.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));

/** The composed page ("index" or "dashboard"), with {{SHOP}} still in place. */
export function composedPage(name) {
  const r = spawnSync("python", ["-m", "dukaan_dost.webpage", name], { cwd: root, encoding: "utf8", maxBuffer: 16 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`could not compose the ${name} page: ${r.stderr || r.error}`);
  return r.stdout;
}
