# Verifikasi fondasi

Dilakukan lokal pada 20 September 2026, Windows/PowerShell dan Docker Desktop Linux
containers. Hasil berikut mengacu pada fondasi fase ini, bukan uji kapasitas nasional.

## Hasil

| Pemeriksaan                                 | Hasil                                                                                                                           |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Prettier, ESLint 10 + Next/React rules      | Lulus; nol warning lint pada kode proyek.                                                                                       |
| TypeScript strict frontend dan test tooling | Lulus.                                                                                                                          |
| Ruff lint/format dan mypy strict API        | Lulus; 15 modul source diperiksa mypy.                                                                                          |
| Unit/API contract tests                     | 20 lulus. Bbox wajib/finite/ordered, limit, host, request ID, redaksi error, API read-only.                                     |
| Integrasi database                          | 7 lulus pada PostgreSQL/PostGIS nyata, project `kdmp-foundation-test` terpisah.                                                 |
| Playwright E2E                              | 10 lulus pada Chromium desktop dan mobile; API/PostGIS nyata, basemap sintetis khusus test.                                     |
| Next.js production build                    | Lulus di host dan image Linux standalone.                                                                                       |
| Docker API/web images                       | Build dan startup lulus; proses web UID 1000, API UID 10001, filesystem aplikasi read-only.                                     |
| Migrasi                                     | Upgrade awal dan pengulangan lulus; `alembic check` tidak menemukan drift.                                                      |
| Koneksi penuh                               | Web `/api/health` → API → PostGIS mengembalikan 200.                                                                            |
| Gangguan database nyata                     | Saat DB dihentikan: web/API liveness 200, readiness dan query spasial 503 tanpa SQL/credential. Pulih setelah DB aktif kembali. |
| Privilege database                          | Role API dapat SELECT, ditolak saat DELETE dan CREATE TABLE, bukan superuser.                                                   |
| Dataset utama                               | Tabel koperasi kosong (0 baris); fixture hanya pada database test dengan rollback.                                              |
| Audit dependency runtime npm                | 0 kerentanan yang dilaporkan pada waktu pemeriksaan. Bukan audit keamanan menyeluruh.                                           |
| Browser dengan basemap eksternal            | Tile PBF dan glyph 200, worker lokal termuat, tidak ada error/warning console.                                                  |
| Responsif                                   | Lebar 1440, 390, 320 px: peta terpasang, layanan terhubung, tanpa horizontal overflow.                                          |
| Rahasia dan source                          | `.env`, virtualenv, build dan artefak QA diabaikan; `src/lib` tetap masuk source repository.                                    |

Versi runtime database teramati: PostgreSQL **18.6**, PostGIS **3.6.4**. Image dasar
Node 24, Python 3.13, PostGIS dan uv dipin digest. Dependency aplikasi memakai
`package-lock.json` dan `uv.lock`.

Test browser memakai sumber GeoJSON sintetis pada style lokal agar worker benar-benar
melakukan parsing/rendering. Test ini memeriksa viewport awal mencakup Indonesia,
status kosong, reset peta, error data, pemulihan, kegagalan basemap, dan truncation.
Tidak mengandalkan style kosong yang dapat lolos walaupun worker rusak.

## Masalah yang ditemukan dan diperbaiki

1. Docker Desktop belum aktif; engine diaktifkan untuk verifikasi seluruh stack.
2. Image kandidat `17-3.5` membawa minor PostgreSQL lama. Baseline diganti ke
   `18-3.6` yang telah diuji dan dipin digest, dengan volume path PostgreSQL 18.
3. Healthcheck UNIX socket sempat lolos pada server sementara selama initdb.
   Pemeriksaan TCP mencegah migrator berjalan sebelum server final siap.
4. Nama `schema` berbenturan dengan API BaseModel Pydantic. Field internal diganti
   `schema_status`, sambil mempertahankan alias kontrak `schema`.
5. Plugin React masih menggunakan API context yang dihapus ESLint 10. Adapter resmi
   `@eslint/compat` digunakan; aturan lint tetap aktif.
6. Quote tunggal npm script gagal pada shell Windows. Ekspresi marker pytest memakai
   quote ganda; generator kontrak memanggil Node/npm tanpa shell concatenation.
7. MapLibre 6 pada build Next.js tidak otomatis menyajikan worker/shared module.
   Prebuild/predev menyalin keduanya beserta lisensi ke aset lokal berversi dan
   mengatur URL worker secara eksplisit, sesuai [panduan MapLibre](https://maplibre.org/maplibre-gl-js/docs/).
8. Batas lintang peta terlalu ketat memotong cakupan awal pada layar portrait.
   Batas dan minimum zoom disesuaikan; test memeriksa cakupan viewport.
9. `.gitignore` awal mempunyai pola `lib/` yang juga mengabaikan helper frontend.
   Pola dibatasi ke root agar source `apps/web/src/lib` tidak hilang ketika disimpan.
10. Locator alert test berbenturan dengan announcer Next.js; locator kini dibatasi
    ke region peta. Konkurensi browser dibatasi 2 karena software WebGL berat; tidak
    ada sleep tetap atau pengabaian assertion untuk membuat test lulus.
11. Role database test dipisah lewat project eksplisit `-p kdmp-foundation-test`,
    sehingga `COMPOSE_PROJECT_NAME` dari `.env` tidak mengarahkannya ke stack utama.

## Batas verifikasi

- GitHub Actions disediakan dan langkah utamanya dijalankan lokal; workflow belum
  dijalankan pada runner GitHub karena tidak ada push/deployment remote.
- Ada warning deprecation dari `Starlette TestClient` terhadap alias AnyIO serta
  dependency ESLint 9 transitif milik plugin saat instalasi. Linter proyek adalah
  ESLint 10; warning pihak ketiga tersebut tidak menjadi error runtime/test.
- Basemap demonstrasi bukan dataset batas resmi atau layanan dengan SLA. Data
  koperasi resmi belum diimpor. Geometri sintetis hanya membuktikan kontrak/integrasi.
- Belum dilakukan uji beban nasional, failover/HA, restore backup, audit akses data
  riil, atau pengujian Safari/Firefox. Tidak ada autentikasi/endpoint tulis pada fase ini.

Screenshot visual lokal tersedia setelah sesi QA di `artifacts/desktop.png`,
`artifacts/mobile.png`, dan `artifacts/small-mobile.png` (diabaikan Git).

## Verifikasi alur impor, 25 September 2026

- Pemeriksaan format, ESLint, TypeScript, Ruff, mypy, kontrak OpenAPI, dan build
  produksi lulus setelah penambahan impor.
- Unit API/validator: 41 lulus. Integrasi PostGIS: 9 lulus pada database test
  terpisah, termasuk pergantian rilis aktif, penolakan versi duplikat, dan rollback
  saat penulisan satu batch gagal.
- `alembic check` tidak mendeteksi drift setelah migrasi `0003_village_reference`.
- CLI dry run dan `--apply` diuji dengan satu baris sintetis di database test;
  hash cocok, baris terbit, dan lingkungan test dibersihkan. Database utama tidak
  diisi atau dimigrasi dalam pemeriksaan ini.
- Stack Compose QA terpisah mencapai status healthy. Playwright desktop dan mobile:
  10 lulus pada web/API/PostGIS dengan dataset kosong. Stack QA memakai port web
  33001 dan volume tersendiri; stack utama tetap tidak diubah.
- Validator sekarang mewajibkan CSV referensi berversi bila `village_code` terisi;
  kode tak dikenal, hash berubah, dan kode ganda ditolak. Integrasi memastikan
  metadata referensi tersimpan di batch. Pemilihan sumber resmi dan review izin
  publikasi tetap merupakan pekerjaan pemilik data sebelum impor nyata.
