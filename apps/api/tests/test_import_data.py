import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from kdmp_api.import_data import validate_release

HEADER = "external_id,name,village_code,longitude,latitude\n"
ROW = "synthetic-1,Test cooperative,3171010001,106.8,-6.2\n"


def write_release(
    tmp_path: Path, csv_body: str = HEADER + ROW, **overrides: object
) -> tuple[Path, Path]:
    csv_path = tmp_path / "cooperatives.csv"
    csv_path.write_text(csv_body, encoding="utf-8")
    manifest = {
        "dataset_key": "synthetic-test",
        "version": "2026-09-25",
        "source_name": "Synthetic test source",
        "source_url": "https://example.org/source",
        "license": "Test only",
        "retrieved_at": "2026-09-25T00:00:00+07:00",
        "approved_by": "Synthetic reviewer",
        "approved_at": "2026-09-25T01:00:00+07:00",
        "file_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "expected_rows": 1,
    }
    manifest.update(overrides)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, csv_path


def test_valid_release_has_provenance_and_coordinate_order(tmp_path: Path) -> None:
    plan = validate_release(*write_release(tmp_path))
    assert plan.manifest.dataset_key == "synthetic-test"
    assert plan.rows[0].external_id == "synthetic-1"
    assert (plan.rows[0].longitude, plan.rows[0].latitude) == (106.8, -6.2)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (HEADER + ROW + ROW, "duplicate external_id"),
        (HEADER + "synthetic-1,Test cooperative,,0,0\n", "outside the broad Indonesia extent"),
        (HEADER + "synthetic-1,Test cooperative,,nan,-6.2\n", "longitude outside EPSG:4326"),
        (HEADER + "synthetic-1,Test cooperative,ABC,106.8,-6.2\n", "village_code"),
        (HEADER + "synthetic-1,Test cooperative,,106.8\n", "wrong number of columns"),
        (HEADER.replace("longitude,latitude", "latitude,longitude") + ROW, "CSV header"),
    ],
)
def test_rejects_invalid_rows(tmp_path: Path, body: str, expected: str) -> None:
    manifest_path, csv_path = write_release(tmp_path, body, expected_rows=body.count("\n") - 1)
    with pytest.raises(ValueError, match=expected):
        validate_release(manifest_path, csv_path)


def test_rejects_changed_file(tmp_path: Path) -> None:
    manifest_path, csv_path = write_release(tmp_path)
    csv_path.write_text(HEADER + ROW + "synthetic-2,Other,,107,-6\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        validate_release(manifest_path, csv_path)


def test_cli_dry_run_and_apply_guard(tmp_path: Path) -> None:
    manifest_path, csv_path = write_release(tmp_path)
    command = [
        sys.executable,
        "-m",
        "kdmp_api.import_data",
        "--manifest",
        str(manifest_path),
        "--csv",
        str(csv_path),
    ]
    dry_run = subprocess.run(command, capture_output=True, text=True, check=False)
    assert dry_run.returncode == 0
    assert json.loads(dry_run.stdout)["status"] == "validated"
    without_confirmed_hash = subprocess.run(
        [*command, "--apply"], capture_output=True, text=True, check=False
    )
    assert without_confirmed_hash.returncode != 0
    assert "--confirm-sha256" in without_confirmed_hash.stderr


@pytest.mark.parametrize(
    "override",
    [
        {"approved_by": ""},
        {"approved_at": "2026-09-25T00:00:00"},
        {"retrieved_at": "2026-09-25T00:00:00"},
        {"approved_at": "2026-09-24T23:00:00+07:00"},
        {"source_url": "not-a-url"},
        {"source_url": "http://example.org/source"},
        {"expected_rows": 0},
    ],
)
def test_requires_reviewable_manifest(tmp_path: Path, override: dict[str, object]) -> None:
    manifest_path, csv_path = write_release(tmp_path, **override)
    with pytest.raises(ValueError):
        validate_release(manifest_path, csv_path)
