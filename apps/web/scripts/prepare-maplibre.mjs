import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageFile = createRequire(import.meta.url).resolve("maplibre-gl/package.json");
const packageDir = path.dirname(packageFile);
const { version } = JSON.parse(readFileSync(packageFile, "utf8"));
const destination = fileURLToPath(
  new URL(`../public/vendor/maplibre/${version}/`, import.meta.url),
);
mkdirSync(destination, { recursive: true });

// MapLibre 6's worker imports its shared module by relative URL. Both must be
// served together; Next.js does not emit this sibling for a new URL() asset.
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(path.join(packageDir, "dist", file), path.join(destination, file));
}
copyFileSync(path.join(packageDir, "LICENSE.txt"), path.join(destination, "LICENSE.txt"));
console.log(`Prepared MapLibre ${version} worker and shared module.`);
