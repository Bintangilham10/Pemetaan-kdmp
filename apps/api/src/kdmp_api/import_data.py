"""Validate a public CSV release and optionally publish it atomically."""

import argparse
import csv
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from kdmp_api.core.config import get_settings
from kdmp_api.modules.cooperatives.model import ImportBatch

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ROWS = 100_000
COLUMNS = ["external_id", "name", "village_code", "longitude", "latitude"]
REFERENCE_COLUMNS = ["village_code"]


class VillageReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = Field(min_length=1, max_length=100)
    source_url: HttpUrl = Field(max_length=2048)
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_codes: int = Field(ge=1, le=MAX_ROWS)

    @field_validator("source_url")
    @classmethod
    def require_public_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https" or value.username or value.password:
            raise ValueError("reference source_url must be HTTPS without credentials")
        return value


class ImportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dataset_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,79}$")
    version: str = Field(min_length=1, max_length=100)
    source_name: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl = Field(max_length=2048)
    license: str = Field(min_length=1, max_length=200)
    retrieved_at: datetime
    approved_by: str = Field(min_length=1, max_length=200)
    approved_at: datetime
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_rows: int = Field(ge=1, le=MAX_ROWS)
    village_reference: VillageReference | None = None

    @field_validator("retrieved_at", "approved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value

    @field_validator("version", "source_name", "license", "approved_by")
    @classmethod
    def require_printable_text(cls, value: str) -> str:
        if not value.isprintable():
            raise ValueError("metadata must contain printable text")
        return value

    @field_validator("source_url")
    @classmethod
    def require_public_source_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https" or value.username or value.password:
            raise ValueError("source_url must be HTTPS without credentials")
        return value

    @model_validator(mode="after")
    def approval_follows_retrieval(self) -> "ImportManifest":
        if self.approved_at < self.retrieved_at:
            raise ValueError("approved_at must not precede retrieved_at")
        return self


@dataclass(frozen=True)
class ImportRow:
    external_id: str
    name: str
    village_code: str | None
    longitude: float
    latitude: float


@dataclass(frozen=True)
class ImportPlan:
    manifest: ImportManifest
    rows: list[ImportRow]


def load_village_codes(path: Path, reference: VillageReference) -> set[str]:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"village reference exceeds {MAX_FILE_BYTES} bytes")
    content = path.read_bytes()
    if len(content) > MAX_FILE_BYTES:
        raise ValueError(f"village reference exceeds {MAX_FILE_BYTES} bytes")
    if hashlib.sha256(content).hexdigest() != reference.file_sha256:
        raise ValueError("village reference SHA-256 does not match the manifest")
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    if reader.fieldnames != REFERENCE_COLUMNS:
        raise ValueError("village reference header must be exactly: village_code")
    codes: set[str] = set()
    for values in reader:
        code = values.get("village_code")
        if code is None or None in values or not re.fullmatch(r"[0-9]{1,20}", code):
            raise ValueError(f"village reference row {reader.line_num}: invalid code")
        if code in codes:
            raise ValueError(f"village reference row {reader.line_num}: duplicate code")
        codes.add(code)
        if len(codes) > MAX_ROWS:
            raise ValueError(f"village reference exceeds {MAX_ROWS} codes")
    if len(codes) != reference.expected_codes:
        raise ValueError("village reference count does not match the manifest")
    return codes


def validate_release(
    manifest_path: Path, csv_path: Path, village_codes_path: Path | None = None
) -> ImportPlan:
    manifest = ImportManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if (manifest.village_reference is None) != (village_codes_path is None):
        raise ValueError("village reference metadata and --village-codes must be supplied together")
    village_codes = (
        load_village_codes(village_codes_path, manifest.village_reference)
        if village_codes_path is not None and manifest.village_reference is not None
        else None
    )
    if csv_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"CSV exceeds {MAX_FILE_BYTES} bytes")
    content = csv_path.read_bytes()
    if len(content) > MAX_FILE_BYTES:
        raise ValueError(f"CSV exceeds {MAX_FILE_BYTES} bytes")
    digest = hashlib.sha256(content).hexdigest()
    if digest != manifest.file_sha256:
        raise ValueError("CSV SHA-256 does not match the manifest")
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    if reader.fieldnames != COLUMNS:
        raise ValueError(f"CSV header must be exactly: {','.join(COLUMNS)}")
    rows: list[ImportRow] = []
    seen: set[str] = set()
    for values in reader:
        line = reader.line_num
        if len(rows) >= MAX_ROWS:
            raise ValueError(f"CSV exceeds {MAX_ROWS} rows")
        if None in values or any(value is None for value in values.values()):
            raise ValueError(f"row {line}: wrong number of columns")
        external_id = values["external_id"].strip()
        name = values["name"].strip()
        village_code = values["village_code"].strip() or None
        if not external_id or len(external_id) > 120 or not external_id.isprintable():
            raise ValueError(f"row {line}: invalid external_id")
        if external_id in seen:
            raise ValueError(f"row {line}: duplicate external_id")
        if not name or len(name) > 200 or not name.isprintable():
            raise ValueError(f"row {line}: invalid name")
        if village_code and (len(village_code) > 20 or not re.fullmatch(r"[0-9]+", village_code)):
            raise ValueError(f"row {line}: village_code must contain at most 20 digits")
        if village_code and village_codes is None:
            raise ValueError(f"row {line}: village_code requires a versioned village reference")
        if village_code and village_codes is not None and village_code not in village_codes:
            raise ValueError(f"row {line}: village_code is absent from the reference")
        try:
            longitude = float(values["longitude"])
            latitude = float(values["latitude"])
        except ValueError as exc:
            raise ValueError(f"row {line}: invalid coordinates") from exc
        if not (math.isfinite(longitude) and -180 <= longitude <= 180):
            raise ValueError(f"row {line}: longitude outside EPSG:4326")
        if not (math.isfinite(latitude) and -90 <= latitude <= 90):
            raise ValueError(f"row {line}: latitude outside EPSG:4326")
        if not (94 <= longitude <= 142 and -12 <= latitude <= 8):
            raise ValueError(f"row {line}: coordinates outside the broad Indonesia extent")
        seen.add(external_id)
        rows.append(ImportRow(external_id, name, village_code, longitude, latitude))
    if len(rows) != manifest.expected_rows:
        raise ValueError("CSV row count does not match the manifest")
    if village_codes is not None and not any(row.village_code for row in rows):
        raise ValueError("village reference supplied but no row has a village_code")
    return ImportPlan(manifest, rows)


def publish_release(session: Session, plan: ImportPlan) -> UUID:
    manifest = plan.manifest
    # Serialize releases of the same dataset so a stale job cannot replace a newer one.
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:dataset_key, 0))"),
        {"dataset_key": manifest.dataset_key},
    )
    existing = session.execute(
        text("SELECT 1 FROM import_batches WHERE dataset_key=:key AND version=:version"),
        {"key": manifest.dataset_key, "version": manifest.version},
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("dataset version already imported; use a new version")
    active_approval = session.execute(
        text("SELECT approved_at FROM import_batches WHERE dataset_key=:key AND active"),
        {"key": manifest.dataset_key},
    ).scalar_one_or_none()
    if active_approval is not None and manifest.approved_at <= active_approval:
        raise ValueError("release approval must be newer than the active release")
    legacy = session.execute(
        text(
            "SELECT 1 FROM cooperatives WHERE import_batch_id IS NULL "
            "AND source=:source_name LIMIT 1"
        ),
        {"source_name": manifest.source_name},
    ).scalar_one_or_none()
    if legacy is not None:
        raise ValueError("legacy rows from this source must be reconciled before publication")
    batch_id = uuid4()
    session.add(
        ImportBatch(
            id=batch_id,
            dataset_key=manifest.dataset_key,
            version=manifest.version,
            source_name=manifest.source_name,
            source_url=str(manifest.source_url),
            license=manifest.license,
            retrieved_at=manifest.retrieved_at,
            approved_by=manifest.approved_by,
            approved_at=manifest.approved_at,
            file_sha256=manifest.file_sha256,
            row_count=len(plan.rows),
            village_reference_version=(
                manifest.village_reference.version if manifest.village_reference else None
            ),
            village_reference_source_url=(
                str(manifest.village_reference.source_url) if manifest.village_reference else None
            ),
            village_reference_sha256=(
                manifest.village_reference.file_sha256 if manifest.village_reference else None
            ),
            active=False,
        )
    )
    session.flush()
    insert_sql = text(
        "INSERT INTO cooperatives "
        "(id, name, village_code, location, source, import_batch_id, external_id) "
        "VALUES (:id, :name, :village_code, "
        "ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), "
        ":source, :import_batch_id, :external_id)"
    )
    for start in range(0, len(plan.rows), 1000):
        session.execute(
            insert_sql,
            [
                {
                    "id": uuid4(),
                    "name": row.name,
                    "village_code": row.village_code,
                    "longitude": row.longitude,
                    "latitude": row.latitude,
                    "source": manifest.source_name,
                    "import_batch_id": batch_id,
                    "external_id": row.external_id,
                }
                for row in plan.rows[start : start + 1000]
            ],
        )
    session.execute(
        text("UPDATE import_batches SET active=false WHERE dataset_key=:key AND active"),
        {"key": manifest.dataset_key},
    )
    session.execute(text("UPDATE import_batches SET active=true WHERE id=:id"), {"id": batch_id})
    return batch_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate or publish a public cooperative CSV release"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--village-codes", type=Path, help="Versioned CSV of valid village codes")
    parser.add_argument("--apply", action="store_true", help="Publish in one database transaction")
    parser.add_argument(
        "--confirm-sha256", help="Required with --apply; must match the reviewed CSV"
    )
    args = parser.parse_args()
    try:
        plan = validate_release(args.manifest, args.csv, args.village_codes)
        if args.apply:
            if args.confirm_sha256 != plan.manifest.file_sha256:
                raise ValueError("--confirm-sha256 must match the validated file")
            settings = get_settings()
            engine = create_engine(
                settings.database_url.get_secret_value(),
                pool_pre_ping=True,
                hide_parameters=True,
                connect_args={
                    "connect_timeout": settings.db_timeout_seconds,
                    "options": "-c lock_timeout=10000 -c statement_timeout=60000",
                },
            )
            try:
                with Session(engine) as session, session.begin():
                    batch_id = publish_release(session, plan)
            finally:
                engine.dispose()
        result = {
            "dataset_key": plan.manifest.dataset_key,
            "version": plan.manifest.version,
            "rows": len(plan.rows),
            "file_sha256": plan.manifest.file_sha256,
            "status": "published" if args.apply else "validated",
        }
        if args.apply:
            result["batch_id"] = str(batch_id)
        print(json.dumps(result))
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        parser.exit(1, f"Import rejected: {exc}\n")
    except SQLAlchemyError:
        parser.exit(1, "Import rejected: database operation failed; no changes committed\n")


if __name__ == "__main__":
    main()
