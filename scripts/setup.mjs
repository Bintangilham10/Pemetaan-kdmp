import { randomBytes } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const target = path.join(root, ".env");
if (existsSync(target)) {
  console.log(".env already exists; preserved unchanged.");
} else {
  const template = readFileSync(path.join(root, ".env.example"), "utf8");
  const content = template.replace(/replace-with-random-[a-z]+-secret/g, () =>
    randomBytes(32).toString("hex"),
  );
  writeFileSync(target, content, { flag: "wx", mode: 0o600 });
  console.log("Created local .env with random secrets. Keep this file private.");
}
