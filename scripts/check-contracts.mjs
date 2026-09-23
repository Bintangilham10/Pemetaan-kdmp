import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const paths = ["packages/contracts/openapi.json", "packages/contracts/src/schema.d.ts"];
const before = paths.map((file) => readFileSync(file, "utf8").replaceAll("\r\n", "\n"));
const npmCli = process.env.npm_execpath;
if (!npmCli) throw new Error("Run this check with npm run contracts:check.");
const result = spawnSync(process.execPath, [npmCli, "run", "contracts:generate"], {
  stdio: "inherit",
});
if (result.status !== 0) process.exit(result.status ?? 1);
const changed = paths.filter(
  (file, index) => readFileSync(file, "utf8").replaceAll("\r\n", "\n") !== before[index],
);
if (changed.length) {
  console.error(`Contract drift detected; review regenerated files: ${changed.join(", ")}`);
  process.exit(1);
}
console.log("OpenAPI and TypeScript contracts are current.");
