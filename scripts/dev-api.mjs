import { loadEnvFile } from "node:process";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
loadEnvFile(new URL("../.env", import.meta.url));
const databaseUrl = new URL(
  `postgresql://127.0.0.1:${process.env.DB_PORT ?? "55432"}/${process.env.POSTGRES_DB ?? "kdmp"}`,
);
databaseUrl.username = "kdmp_api";
databaseUrl.password = process.env.API_DB_PASSWORD ?? "";
if (!databaseUrl.password) throw new Error("Run npm run setup to create local credentials first.");
const child = spawn(
  "uv",
  [
    "run",
    "--project",
    "apps/api",
    "uvicorn",
    "kdmp_api.main:create_app",
    "--factory",
    "--reload",
    "--host",
    "127.0.0.1",
    "--port",
    process.env.API_PORT ?? "8000",
  ],
  {
    cwd: root,
    stdio: "inherit",
    env: {
      ...process.env,
      KDMP_ENVIRONMENT: "development",
      KDMP_DATABASE_URL:
        process.env.KDMP_DATABASE_URL ??
        databaseUrl.toString().replace("postgresql://", "postgresql+psycopg://"),
    },
  },
);
child.on("error", () => {
  console.error("Could not start uv. Install uv and Python 3.13 first.");
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
