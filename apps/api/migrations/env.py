from alembic import context
from sqlalchemy import create_engine, pool

from kdmp_api.core.config import get_settings
from kdmp_api.core.database import Base
from kdmp_api.modules.cooperatives.model import Cooperative  # noqa: F401

config = context.config
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # PostGIS owns spatial_ref_sys and extension objects; Alembic must not drop them.
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline():
    context.configure(
        url=get_settings().database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(get_settings().database_url.get_secret_value(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
