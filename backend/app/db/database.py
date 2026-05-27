"""
Configuração SQLAlchemy — engine, sessão e modelo base.

Row-Level Security (RLS):
  O modelo base não define políticas RLS (responsabilidade das migrações Alembic),
  mas expõe o padrão tenant_id e o helper set_tenant_context() para activar
  a variável de sessão PostgreSQL `app.current_tenant_id`.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

# Usar postgresql+psycopg2 para produção; fallback para sqlite em modo de teste.
# A variável TESTING=1 no ambiente substitui a URL por SQLite em memória
# (útil para testes locais sem psycopg2 instalado).
import os as _os
_db_url = (
    "sqlite:///:memory:"
    if _os.environ.get("TESTING") == "1"
    else settings.database_url
)
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

_is_sqlite = _db_url.startswith("sqlite")
_engine_kwargs: dict = dict(
    connect_args=_connect_args,
    echo=(settings.environment == "development"),
)
if not _is_sqlite:
    _engine_kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=10)

engine = create_engine(_db_url, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Classe base para todos os modelos SQLAlchemy.
    Todos os modelos multi-tenant devem incluir tenant_id como chave de isolamento.
    """
    pass


def set_tenant_context(db_session, tenant_id) -> None:
    """
    Define a variável de sessão PostgreSQL para Row-Level Security.

    Deve ser chamado após abrir a sessão e antes de qualquer query.
    As políticas RLS usam current_setting('app.current_tenant_id', true) para filtrar.
    O segundo argumento missing_ok=true faz a policy falhar fechada (zero linhas)
    em vez de lançar excepção quando a variável não está definida.

    NOTA: SET LOCAL é um utility statement — PostgreSQL não aceita bind
    parameters ($1) server-side neste contexto, independentemente do driver.
    psycopg2 mascarava isso via substituição client-side, mas psycopg3 e
    pg8000 falham correctamente. Usamos literal string com validação UUID
    para prevenir SQL injection.

    Args:
        db_session: Sessão SQLAlchemy activa.
        tenant_id:  UUID do tenant (str ou UUID object).
    """
    import uuid as _uuid
    tenant_id_str = str(tenant_id)
    _uuid.UUID(tenant_id_str)
    db_session.execute(
        text(f"SET LOCAL app.current_tenant_id = '{tenant_id_str}'"),
    )
