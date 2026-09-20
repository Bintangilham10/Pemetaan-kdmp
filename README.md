# WebGIS Koperasi Merah Putih

Fondasi platform pemetaan Koperasi Desa/Kelurahan Merah Putih. Berisi Next.js,
FastAPI dan PostgreSQL/PostGIS yang benar-benar terhubung, dengan peta minimal dan
dataset kosong. Belum menyediakan administrasi, autentikasi, monitoring kompleks,
AI, marketplace atau analitik.

## Jalankan seluruh stack

Prasyarat: Docker Engine/Desktop dengan Linux containers + Compose v2, Node.js 24
LTS. Image PostGIS yang dipilih menggunakan Linux amd64; ARM membutuhkan image
PostGIS yang sesuai atau emulasi amd64 yang diverifikasi.

```powershell
node scripts/setup.mjs
docker compose up --build -d --wait
```

Buka **http://localhost:3000**. `setup` menghasilkan `.env` lokal berisi secret
acak; file yang sudah ada dipertahankan. Jangan unggah `.env`. Tidak perlu npm,
Python atau PostgreSQL terinstal di host untuk membangun image, selain Node untuk
menjalankan script setup. Build pertama membutuhkan internet.

```powershell
docker compose ps
docker compose logs --tail 100 api web
docker compose down
```

`down` mempertahankan volume data. Jangan menambahkan `--volumes` pada lingkungan
yang memiliki data penting. Database/API tidak dipublikasikan ke host pada
konfigurasi utama; web hanya bind ke loopback.

## Struktur

```text
apps/web/             Next.js App Router, UI shadcn, fitur map dan status layanan
apps/api/             FastAPI src/kdmp_api, modul domain, Alembic, unit/integration tests
packages/contracts/  OpenAPI dan tipe TypeScript hasil generate
infra/db/            Bootstrap role dan privileges database
scripts/             Setup, dev API, pemeriksaan drift kontrak
tests/e2e/           Playwright desktop/mobile
docs/                Keputusan arsitektur, operasi, catatan verifikasi
compose*.yaml        Stack utama, port dev opsional, database test terisolasi
```

Detail keputusan dan risiko: [arsitektur](docs/architecture.md).

## Pengembangan dengan hot reload

Tambahan prasyarat: npm dan uv, Python 3.13. Dependency Node dan Python dikunci
oleh `package-lock.json` serta `apps/api/uv.lock`.

```powershell
npm ci
uv sync --project apps/api --locked
npm run setup
docker compose -f compose.yaml -f compose.dev.yaml up -d db
docker compose run --rm migrate
```

Terminal pertama:

```powershell
npm run dev:api
```

Terminal kedua:

```powershell
npm run dev
```

API dev: http://localhost:8000/docs. Web: http://localhost:3000. PostgreSQL dev:
`127.0.0.1:55432`. Jangan menjalankan web/API kontainer dan proses host pada port
yang sama; bila sebelumnya stack penuh berjalan, jalankan `docker compose stop
web api`. `dev:api` membaca credential lokal tanpa mencetaknya. Untuk memakai port
API selain 8000, atur `API_INTERNAL_URL` pada environment proses web atau
`apps/web/.env.local`.

## Konfigurasi

| Variabel                                                               | Kegunaan                                                                                                                                                          |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POSTGRES_PASSWORD`, `MIGRATOR_PASSWORD`, `API_DB_PASSWORD`            | Tiga secret terpisah di `.env`; script menghasilkan hex yang aman sebagai komponen URL. Jika diisi manual, gunakan hex/alphanumeric atau encode URL dengan benar. |
| `POSTGRES_DB`, `POSTGRES_USER`                                         | Database dan admin bootstrap, bukan akun runtime API.                                                                                                             |
| `WEB_PORT`, `API_PORT`, `DB_PORT`                                      | Port host. API/DB hanya aktif lewat override dev.                                                                                                                 |
| `API_INTERNAL_URL`                                                     | Origin API di runtime server Next; Compose mengatur `http://api:8000`.                                                                                            |
| `MAP_STYLE_URL`                                                        | Style MapLibre yang dapat diakses browser; default basemap demonstrasi.                                                                                           |
| `KDMP_DATABASE_URL`                                                    | URL psycopg milik backend/migrator; tidak pernah dikirim ke browser.                                                                                              |
| `KDMP_ALLOWED_HOSTS`, `KDMP_CORS_ORIGINS`                              | JSON array host/origin eksplisit; tidak menerima wildcard. Default browser menggunakan origin web yang sama.                                                      |
| `KDMP_DB_POOL_SIZE`, `KDMP_DB_MAX_OVERFLOW`, `KDMP_DB_TIMEOUT_SECONDS` | Batas pool dan timeout per proses API.                                                                                                                            |

Pengubahan password pada `.env` tidak mengubah role di volume yang sudah ada.
Rotasikan credential di PostgreSQL dan environment layanan sebagai satu operasi
terkontrol. Jangan menghapus volume untuk memperbaiki password produksi.

## API fondasi

| Endpoint                                                   | Perilaku                                                                          |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------- |
| API `GET /health/live`                                     | Liveness tanpa akses database.                                                    |
| API `GET /health/ready`                                    | Koneksi PostGIS, tabel dan revisi Alembic; 503 bila belum siap.                   |
| API `GET /api/v1/cooperatives?bbox=95,-11,141,6&limit=500` | GeoJSON titik publik, bbox wajib, limit 1–1000, `numberReturned` dan `truncated`. |
| Web `GET /health/live`                                     | Liveness proses web.                                                              |
| Web `GET /api/health`                                      | Kesiapan end-to-end web → API → database.                                         |
| Web `GET /api/v1/cooperatives?...`                         | Proxy terbatas untuk GET data peta.                                               |

Semua koordinat memakai **longitude, latitude / EPSG:4326**. Antimeridian bbox
tidak didukung pada fase ini. Data kosong sah; error dan truncation tidak disamakan
dengan kosong. Tidak ada endpoint tulis atau seed data yang menyerupai data resmi.
API docs publik dinonaktifkan pada environment production.

## Pemeriksaan

```powershell
npm run check
npm run build
npm run test:integration
docker compose -p kdmp-foundation-test -f compose.test.yaml down
docker compose up --build -d --wait
npx playwright install chromium
npm run test:e2e
```

- `check`: format, ESLint, TypeScript strict, Ruff, mypy strict, unit tests, drift kontrak.
- `test:integration`: PostGIS sungguhan pada project/db test terpisah; data sintetis
  berada dalam transaksi rollback. Jangan set database test ke produksi.
- `test:e2e`: stack utama harus berjalan dan kosong. API/PostGIS nyata; basemap CI
  diintersep dengan style lokal agar tidak bergantung pada layanan pihak ketiga.
  Pemeriksaan visual basemap eksternal dicatat terpisah.
- `npm run contracts:generate`: setelah mengubah schema/API, review dan simpan
  OpenAPI serta tipe hasil generate. Tidak memerlukan database berjalan.

Workflow GitHub Actions tersedia, tetapi eksekusi CI remote memerlukan repository
diunggah ke GitHub. Hasil lokal ada di [catatan verifikasi](docs/verification.md).

## Sebelum produksi nasional

Fondasi ini menggunakan pola deployment produksi, tetapi **bukan klaim siap
melayani skala nasional**. Lanjutkan sumber data resmi/kode wilayah, validasi impor,
OIDC/RBAC dan audit, lalu TLS/ingress, rate limiting, backup/PITR + restore drill,
secret manager, monitoring operasional, uji beban, dan basemap berlisensi/SLA.
Lihat [runbook operasi](docs/operations.md). Compose lokal bukan high availability.
