import { expect, test, type Page } from "@playwright/test";

// The basemap is deterministic in CI; the API and PostGIS are real services.
// The external demonstration basemap is checked separately during visual QA.
async function localBasemap(page: Page) {
  await page.route("https://demotiles.maplibre.org/style.json", (route) =>
    route.fulfill({
      json: {
        version: 8,
        sources: {
          "test-land": {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: [
                {
                  type: "Feature",
                  properties: {},
                  geometry: {
                    type: "Polygon",
                    coordinates: [
                      [
                        [95, -11],
                        [141, -11],
                        [141, 6],
                        [95, 6],
                        [95, -11],
                      ],
                    ],
                  },
                },
              ],
            },
          },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#e5eef1" } },
          // A real GeoJSON source forces the browser worker to parse and render.
          {
            id: "test-land",
            source: "test-land",
            type: "fill",
            paint: { "fill-color": "#e2e8de" },
          },
        ],
      },
    }),
  );
}

test("real web → API → PostGIS connection and bounded contract", async ({ request }) => {
  const health = await request.get("/api/health");
  expect(health.status()).toBe(200);
  expect(await health.json()).toEqual({
    status: "ok",
    database: "ok",
    spatial: "ok",
    schema: "ok",
  });
  const response = await request.get("/api/v1/cooperatives?bbox=95,-11,141,6&limit=1");
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toMatchObject({ type: "FeatureCollection" });
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(response.headers()["x-request-id"]).toMatch(/^[\da-f-]{36}$/);
  expect((await request.get("/api/v1/cooperatives")).status()).toBe(422);
  expect((await request.get("/api/v1/cooperatives?bbox=nan,0,1,2")).status()).toBe(422);
  expect((await request.post("/api/v1/cooperatives", { data: {} })).status()).toBe(405);
});

test("map mounts, empty state is honest, controls work, layout fits", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await localBasemap(page);
  const initialViewport = page.waitForRequest((request) =>
    request.url().includes("/api/v1/cooperatives?"),
  );
  await page.goto("/");
  const bbox = new URL((await initialViewport).url()).searchParams
    .get("bbox")!
    .split(",")
    .map(Number);
  expect(bbox[0]).toBeLessThanOrEqual(95);
  expect(bbox[1]).toBeLessThanOrEqual(-11);
  expect(bbox[2]).toBeGreaterThanOrEqual(141);
  expect(bbox[3]).toBeGreaterThanOrEqual(6);
  await expect(
    page.getByRole("heading", { level: 1, name: "Peta Koperasi Merah Putih" }),
  ).toBeVisible();
  await expect(page.getByText("Layanan terhubung", { exact: true })).toBeVisible();
  await expect(page.getByTestId("cooperative-map")).toHaveAttribute("data-ready", "true");
  await expect(
    page.getByText("Belum ada data koperasi di area ini", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Atur ulang peta" })).toBeEnabled();
  await page.getByRole("button", { name: "Atur ulang peta" }).click();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
  expect(errors).toEqual([]);
});

test("data failure can recover without showing a false empty state", async ({ page }) => {
  await localBasemap(page);
  await page.route("**/api/v1/cooperatives?*", (route) =>
    route.fulfill({ status: 503, json: { detail: "Test outage" } }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "Peta sebaran koperasi" }).getByRole("alert"),
  ).toContainText("Data koperasi belum dapat dimuat");
  await expect(page.getByText("Belum ada data koperasi di area ini", { exact: true })).toHaveCount(
    0,
  );
  await page.unroute("**/api/v1/cooperatives?*");
  await page.getByRole("button", { name: "Coba lagi", exact: true }).click();
  await expect(
    page.getByText("Belum ada data koperasi di area ini", { exact: true }),
  ).toBeVisible();
});

test("basemap failure is distinct and retry recreates the map", async ({ page }) => {
  await page.route("https://demotiles.maplibre.org/style.json", (route) => route.abort());
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "Peta sebaran koperasi" }).getByRole("alert"),
  ).toContainText("peta dasar");
  await page.unroute("https://demotiles.maplibre.org/style.json");
  await localBasemap(page);
  await page.getByRole("button", { name: "Coba lagi", exact: true }).click();
  await expect(page.getByTestId("cooperative-map")).toHaveAttribute("data-ready", "true");
  await expect(
    page.getByText("Belum ada data koperasi di area ini", { exact: true }),
  ).toBeVisible();
});

test("truncated data is explicit and point rendering accepts the contract", async ({ page }) => {
  await localBasemap(page);
  await page.route("**/api/v1/cooperatives?*", (route) =>
    route.fulfill({
      json: {
        type: "FeatureCollection",
        numberReturned: 1,
        truncated: true,
        features: [
          {
            type: "Feature",
            id: "00000000-0000-0000-0000-000000000001",
            geometry: { type: "Point", coordinates: [110, -7] },
            properties: { name: "Synthetic browser test", village_code: null, source: "test-only" },
          },
        ],
      },
    }),
  );
  await page.goto("/");
  await expect(page.getByText("Menampilkan 1 titik pertama.", { exact: false })).toBeVisible();
  await expect(page.getByText("Belum ada data koperasi di area ini", { exact: true })).toHaveCount(
    0,
  );
});
