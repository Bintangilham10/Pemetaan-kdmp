# Operasi fondasi

## Startup dan readiness

Compose menunggu PostgreSQL sehat, menjalankan migrasi hingga selesai, baru
menjalankan API dan web. Liveness tidak memeriksa dependency; gunakan web
`/api/health` untuk pemeriksaan end-to-end dan API `/health/ready` untuk readiness
orchestrator. HTTP 503 harus mengeluarkan instance dari traffic, bukan menghapus data.
Kehilangan koneksi setelah startup ditangani timeout/pool pre-ping; healthcheck
Compose sendiri tidak otomatis merestart container berstatus unhealthy.

## Migrasi

```powershell
docker compose run --rm migrate
docker compose run --rm migrate alembic -c alembic.ini current
docker compose run --rm migrate alembic -c alembic.ini check
```

Migrasi adalah pekerjaan release tunggal, sebelum menambah replica API. Jangan
menjalankannya di setiap worker atau menggunakan `metadata.create_all()` saat
startup. Untuk skema baru, buat revisi Alembic, review SQL dan kompatibilitas
deployment bergulir; uji upgrade pada salinan data dan siapkan strategi expand / contract.
Downgrade awal menghapus tabel dan hanya untuk database test kosong; bukan strategi
rollback produksi. PostGIS extension dimiliki administrator, tidak dihapus Alembic.

## Privilege dan secrets

- Admin hanya untuk provisioning/backup terkontrol. `kdmp_migrator` memiliki DDL
  pada skema aplikasi, tanpa superuser. `kdmp_api` mendapat SELECT pada tabel yang
  dibuat migrator; tidak dapat menulis atau membuat tabel.
- Inisialisasi role hanya terjadi saat volume kosong. Ubah privileges/rotate password
  melalui perubahan operasional terkontrol pada volume yang sudah digunakan.
- Secret di `.env` adalah mekanisme lokal. Gunakan secret manager/platform secret
  pada produksi, batasi akses operator, dan jangan menyimpan hasil `compose config`
  yang berisi interpolasi credential ke log atau tiket.
- Endpoint tahap ini hanya boleh memuat data publik. Tidak ada keamanan per-user
  karena autentikasi belum dibuat; endpoint tulis wajib menunggu OIDC/RBAC/audit.

## Backup dan pemulihan

Tetapkan RPO/RTO dan kebijakan retensi dengan pemilik sistem. Produksi membutuhkan
backup terenkripsi, WAL archive/PITR, salinan terpisah, serta restore drill berkala
ke lingkungan terisolasi. Backup logical `pg_dump -Fc` saja tidak membuktikan
pemulihan; periksa jumlah objek, constraint, PostGIS, revisi skema, dan API setelah
restore. Untuk backup lewat CLI gunakan output file di kontainer lalu `docker cp`;
hindari redirect biner PowerShell lama yang dapat merusak arsip.

## Observabilitas dan skala

API mencatat JSON request ID, method, path, status dan durasi tanpa query string,
body atau credential. Gateway wajib membatasi laju dan ukuran request serta menjaga
request correlation. Timeout SQL default 5 detik, upstream web 8 detik. Batas
koneksi maksimum adalah replica × worker × (pool size + overflow); sisakan kapasitas
PostgreSQL untuk migrasi dan operasi. Awal: satu worker per kontainer, scale replica
setelah mengukur; PgBouncer dipertimbangkan jika pool menjadi hambatan.

Tambahkan metrik error/latensi/pool, tracing, alarm, dan load test sebelum menaikkan
traffic. Vector tiles/cluster server dibangun ketika query bbox/payload terukur
tidak lagi memadai. Tidak ada target kapasitas nasional yang diklaim dari smoke test.

## Basemap dan boundary

`demotiles.maplibre.org` untuk demonstrasi, tanpa SLA produksi. `MAP_STYLE_URL`
dibaca saat runtime Next; setiap URL turunan (tiles, glyphs, sprite) harus dapat
diakses browser. Jangan taruh secret server dalam style URL. Tinjau lisensi,
atribusi, data residency, dan tile provider. Batas pada basemap bukan batas resmi;
dataset administratif resmi perlu versi dan sumber tersendiri.

## Release

Jalankan CI lokal/remote, review kontrak, pindai image/dependency, gunakan digest
yang sama dari staging ke produksi, verifikasi TLS dan ingress, jalankan migration
job sekali, lalu verifikasi web/API/PostGIS dan browser. Digest dalam repository
adalah baseline teruji; pembaruan rutin harus mengubah digest dan mengulang checks.
Tambahkan CSP nonce/script policy ketika autentikasi dan rendering final dirancang;
header saat ini membatasi framing/object/base, bukan CSP script yang ketat.
