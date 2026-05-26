"""
env.py — Alembic environment configuration para JFA_Unify.

Autogenerate activado — usa Base.metadata dos modelos ORM (Tenant, InputDevice, AccessLog).

Configuração (uma das seguintes):
    1. DATABASE_URL=postgresql+psycopg2://user:pass@host/db alembic upgrade head
    2. Ficheiro .env na raiz de backend/ com a chave database_url=...
"""

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Garantir que backend/ está no sys.path (necessário para importar app.*)
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Configuração do Alembic
# ---------------------------------------------------------------------------
config = context.config

# Logging a partir do alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo — importar Base e todos os modelos para autogenerate.
from app.db.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  — regista Tenant, InputDevice, AccessLog

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# URL da base de dados
# Prioridade: variável de ambiente DATABASE_URL > app/config.py (lê .env)
# ---------------------------------------------------------------------------
_database_url: str | None = os.environ.get("DATABASE_URL")

if not _database_url:
    # Fallback: carregar via pydantic-settings (responde ao .env do backend)
    try:
        from app.config import get_settings as _get_settings
        _database_url = _get_settings().database_url
    except Exception:
        pass

if not _database_url:
    raise RuntimeError(
        "URL da base de dados não configurada. "
        "Defina DATABASE_URL como variável de ambiente "
        "ou configure 'database_url' no ficheiro .env do backend."
    )

# Injectar URL no objecto de configuração do Alembic
config.set_main_option("sqlalchemy.url", _database_url)


# ---------------------------------------------------------------------------
# Modo offline (gera SQL sem ligar à BD)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Executar migrações em modo offline (sem conexão activa)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Activar comparação de tipos PostgreSQL quando autogenerate for activado
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Modo online (ligação activa à BD)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Executar migrações com conexão activa à base de dados."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
