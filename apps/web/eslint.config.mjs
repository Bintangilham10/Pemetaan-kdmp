import { defineConfig, globalIgnores } from "eslint/config";
import { fixupConfigRules } from "@eslint/compat";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

export default defineConfig([
  // Next's React plugins still use rule context methods removed in ESLint 10.
  ...fixupConfigRules([...nextVitals, ...nextTypescript]),
  globalIgnores([".next/**", "out/**", "build/**", "public/vendor/**", "next-env.d.ts"]),
]);
