"""Export a deterministic contract without connecting to PostgreSQL."""

import json
from pathlib import Path

from pydantic import SecretStr

from kdmp_api.core.config import Settings
from kdmp_api.main import create_app

root = Path(__file__).resolve().parents[3]
app = create_app(
    Settings(database_url=SecretStr("postgresql+psycopg://contract@localhost/contract"))
)
target = root / "packages/contracts/openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Exported {target.relative_to(root)}")
