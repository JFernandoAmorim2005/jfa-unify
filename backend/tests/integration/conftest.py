"""
Fixtures para testes de integração RLS contra PostgreSQL real.

- postgres_url: superuser (bypassa RLS) para setup
- postgres_appuser_url: app_user (respeita RLS) para validação
- setup_database: Alembic auto-migrate via Python API
- Tenants e devices de teste
- Cleanup entre testes
"""
import os
import uuid
from typing import Generator

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, set_tenant_context
from app.models import InputDevice, AccessLog


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """URL para conexão superuser (bypassa RLS) — setup e limpeza."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "test-password")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    db = os.environ.get("POSTGRES_DB", "jfa_test")
    return f"postgresql+pg8000://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def postgres_appuser_url() -> str:
    """URL para conexão app_user (respeita RLS) — testes RLS."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    db = os.environ.get("POSTGRES_DB", "jfa_test")
    return f"postgresql+pg8000://app_user:test-app-password@{host}:{port}/{db}"


@pytest.fixture(scope="session", autouse=True)
def setup_database(postgres_url: str) -> Generator[None, None, None]:
    """Setup: executa Alembic auto-migrate via Python API."""
    engine = create_engine(postgres_url)

    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_url)

    with engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")

    yield
    engine.dispose()


@pytest.fixture(scope="session")
def engine_superuser(postgres_url: str):
    """Engine superuser para setup/limpeza."""
    engine = create_engine(postgres_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def engine_appuser(postgres_appuser_url: str):
    """Engine app_user para testes RLS."""
    engine = create_engine(postgres_appuser_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def session_factory_superuser(engine_superuser):
    """Session factory superuser."""
    return sessionmaker(bind=engine_superuser, autocommit=False, autoflush=False)


@pytest.fixture(scope="session")
def session_factory_appuser(engine_appuser):
    """Session factory app_user."""
    return sessionmaker(bind=engine_appuser, autocommit=False, autoflush=False)


@pytest.fixture
def db_superuser(session_factory_superuser) -> Generator[Session, None, None]:
    """Session superuser (bypassa RLS) para cada teste."""
    session = session_factory_superuser()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def db_appuser(session_factory_appuser) -> Generator[Session, None, None]:
    """Session app_user (respeita RLS) para cada teste."""
    session = session_factory_appuser()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_tenant_a() -> str:
    """UUID tenant A."""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def sample_tenant_b() -> str:
    """UUID tenant B."""
    return "00000000-0000-0000-0000-000000000002"


@pytest.fixture
def sample_device_a(sample_tenant_a: str, db_superuser: Session) -> InputDevice:
    """Device de tenant A."""
    device = InputDevice(
        id=str(uuid.uuid4()),
        tenant_id=sample_tenant_a,
        device_code="DEVICE_A_001",
        device_pin="1234",
        pin_and_card=0,
        status=1,
    )
    db_superuser.add(device)
    db_superuser.commit()
    return device


@pytest.fixture
def sample_device_b(sample_tenant_b: str, db_superuser: Session) -> InputDevice:
    """Device de tenant B."""
    device = InputDevice(
        id=str(uuid.uuid4()),
        tenant_id=sample_tenant_b,
        device_code="DEVICE_B_001",
        device_pin="5678",
        pin_and_card=0,
        status=1,
    )
    db_superuser.add(device)
    db_superuser.commit()
    return device


@pytest.fixture(autouse=True)
def cleanup_integration_data(db_superuser: Session):
    """Limpar dados de teste antes e depois de cada teste."""
    db_superuser.execute(text("TRUNCATE TABLE audit_logs CASCADE"))
    db_superuser.execute(text("TRUNCATE TABLE access_logs CASCADE"))
    db_superuser.execute(text("TRUNCATE TABLE input_devices CASCADE"))
    db_superuser.commit()

    yield

    db_superuser.execute(text("TRUNCATE TABLE audit_logs CASCADE"))
    db_superuser.execute(text("TRUNCATE TABLE access_logs CASCADE"))
    db_superuser.execute(text("TRUNCATE TABLE input_devices CASCADE"))
    db_superuser.commit()
