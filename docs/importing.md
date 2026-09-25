# Impor data koperasi publik

Alur ini menyiapkan publikasi dataset koperasi yang telah ditinjau. Saat ini belum
ada dataset resmi dalam repository atau database awal. Pilih sumber dan versi resmi,
pastikan izin publikasi titik serta nama koperasi, dan cocokkan kode wilayah dengan
referensi yang disepakati sebelum menjalankan `--apply`.

## Format berkas

Simpan CSV UTF-8 dan manifest JSON dalam folder lokal `imports/` (diabaikan Git).
Header CSV harus persis:

```csv
external_id,name,village_code,longitude,latitude
```

`external_id` harus unik dalam satu versi dataset. `village_code` boleh kosong.
Jika terisi, sediakan CSV referensi kode wilayah berversi dengan header tunggal
`village_code`; kode harus 1-20 digit dan ada di daftar tersebut. Pilih sumber
referensi resmi yang disepakati pemilik data. Keanggotaan kode dalam daftar belum
membuktikan bahwa titik berada di dalam batas desa tersebut.
Koordinat memakai longitude lalu latitude (EPSG:4326),
berada dalam rentang dunia dan kotak kasar Indonesia 94-142 BT, 12 LS-8 LU.
Kotak ini hanya pemeriksaan kewajaran, bukan validasi batas administratif.
CSV boleh berisi maksimal 100.000 baris dan 50 MiB. Gunakan `dataset_key` yang sama
untuk setiap versi dari sumber yang sama. Jangan mengubahnya untuk menyiasati
penolakan versi atau duplikasi data. URL sumber harus HTTPS tanpa credential.

Contoh bentuk manifest (isi dengan metadata sumber nyata, bukan nilai contoh):

```json
{
  "dataset_key": "identifier-sumber",
  "version": "versi-dari-penerbit",
  "source_name": "Nama lembaga dan dataset",
  "source_url": "https://penerbit.example/dataset",
  "license": "Izin publikasi yang telah diperiksa",
  "retrieved_at": "2026-09-25T09:00:00+07:00",
  "approved_by": "Nama penanggung jawab review",
  "approved_at": "2026-09-25T10:00:00+07:00",
  "file_sha256": "64 digit heksadesimal huruf kecil dari CSV",
  "expected_rows": 1
}
```

Jika CSV koperasi memiliki `village_code`, tambahkan objek berikut ke manifest:

```json
"village_reference": {
  "version": "versi-referensi-resmi",
  "source_url": "https://penerbit.example/kode-wilayah",
  "file_sha256": "64 digit heksadesimal huruf kecil dari CSV referensi",
  "expected_codes": 1
}
```

Simpan referensi sebagai `imports/villages.csv` dan tambahkan
`--village-codes imports/villages.csv` pada validasi lokal, atau
`--village-codes /imports/villages.csv` pada perintah Docker. SHA-256 referensi
harus sama dengan `village_reference.file_sha256`. Versi, URL sumber, dan hash
referensi ikut tersimpan dalam riwayat rilis. Saat semua `village_code` kosong,
hilangkan objek dan argumen referensi.

`approved_by` dan `approved_at` mencatat persetujuan operator; CLI tidak
memverifikasi identitas atau izin secara otomatis. Lakukan review sumber, lisensi,
duplikasi, kesesuaian kode dengan lokasi, dan kewajaran lokasi di luar CLI. Jangan masukkan NIK,
nomor rekening, telepon pribadi, atau kolom lain yang tidak layak publik. Kolom
tambahan ditolak.

## Pemeriksaan dan publikasi

```powershell
(Get-FileHash imports/cooperatives.csv -Algorithm SHA256).Hash.ToLowerInvariant()
uv run --project apps/api python -m kdmp_api.import_data --manifest imports/manifest.json --csv imports/cooperatives.csv
```

Salin hash ke `file_sha256`, isi jumlah baris sebenarnya pada `expected_rows`,
kemudian jalankan perintah validasi di atas. Proses ini tidak membutuhkan database.
Setelah hasil validasi dan berkas yang sama disetujui, jalankan migrasi lalu impor
dengan role migrator lewat Docker Compose:

```powershell
docker compose run --rm migrate
docker compose run --rm -v "${PWD}/imports:/imports:ro" migrate python -m kdmp_api.import_data --manifest /imports/manifest.json --csv /imports/cooperatives.csv --apply --confirm-sha256 HASH_YANG_SUDAH_DITINJAU
```

Jalankan dari root repository. Perintah kedua hanya berhasil bila hash konfirmasi
sama dengan manifest dan isi CSV. Untuk produksi gunakan proses release dengan
akses terbatas pada role migrator dan volume impor baca saja; jangan jalankan CLI
dengan credential API yang hanya punya SELECT.

Publikasi berjalan dalam satu transaksi. Rilis baru untuk `dataset_key` yang sama
menonaktifkan rilis lama dan menampilkan titik baru setelah commit; baris lama tetap
tersimpan untuk audit. `dataset_key` + `version` tidak dapat diterbitkan ulang.
Waktu `approved_at` harus lebih baru dari persetujuan rilis aktif. Kegagalan validasi
atau database menggagalkan seluruh transaksi. Dataset awal tetap kosong sampai ada
rilis yang benar-benar diterapkan. Tidak ada endpoint tulis publik.

Sebelum setiap refresh, periksa perubahan jumlah baris dan lokasi terhadap rilis
aktif. Backup dan uji restore tetap diperlukan; riwayat rilis bukan pengganti backup.
Jika database lama sudah berisi titik manual dengan `source` yang sama, impor akan
ditolak sampai baris itu direkonsiliasi agar tidak muncul dua kali.
