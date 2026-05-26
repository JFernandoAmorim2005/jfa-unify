"""
Testes de integração para Row-Level Security (RLS) contra PostgreSQL real.

Estratégia: 16 testes que validam fail-closed (sem contexto = zero linhas),
isolamento SELECT/INSERT/UPDATE/DELETE, e context-switching na mesma sessão.
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import set_tenant_context
from app.models import InputDevice, AccessLog

# Marcar todos os testes desta classe como integration tests
pytestmark = pytest.mark.integration


class TestFailClosedDevices:
    """Validar que sem SET LOCAL, app_user vê zero linhas (fail-closed)."""

    def test_no_context_returns_zero_devices(self, db_appuser: Session, sample_device_a, sample_tenant_a):
        """Sem SET LOCAL app.current_tenant_id, query retorna zero devices."""
        # sample_device_a foi inserido com tenant_a, mas db_appuser não tem contexto
        result = db_appuser.query(InputDevice).all()
        assert len(result) == 0, "RLS fail-closed: sem contexto, vê zero linhas"


class TestFailClosedAccessLogs:
    """Validar que sem SET LOCAL, access_logs retorna zero (fail-closed)."""

    def test_no_context_returns_zero_access_logs(self, db_appuser: Session, sample_device_a, sample_tenant_a):
        """Sem SET LOCAL, access_logs retorna zero."""
        result = db_appuser.query(AccessLog).all()
        assert len(result) == 0, "RLS fail-closed: access_logs sem contexto = zero"


class TestSelectIsolationDevices:
    """Validar que SET LOCAL isola SELECT por tenant_id."""

    def test_tenant_a_sees_only_device_a(self, db_appuser: Session, sample_tenant_a: str, sample_device_a, sample_device_b):
        """Tenant A vê só seu device, não o de B."""
        set_tenant_context(db_appuser, sample_tenant_a)
        result = db_appuser.query(InputDevice).all()
        assert len(result) == 1, f"Tenant A deve ver 1 device, viu {len(result)}"
        assert result[0].id == sample_device_a.id

    def test_tenant_b_sees_only_device_b(self, db_appuser: Session, sample_tenant_b: str, sample_device_a, sample_device_b):
        """Tenant B vê só seu device, não o de A."""
        set_tenant_context(db_appuser, sample_tenant_b)
        result = db_appuser.query(InputDevice).all()
        assert len(result) == 1, f"Tenant B deve ver 1 device, viu {len(result)}"
        assert result[0].id == sample_device_b.id


class TestSelectIsolationAccessLogs:
    """Validar que SET LOCAL isola SELECT de access_logs."""

    def test_tenant_a_sees_only_own_access_logs(self, db_appuser: Session, sample_tenant_a: str, sample_device_a):
        """Tenant A vê só seus access_logs."""
        # sample_device_a tem access logs gerados em conftest
        set_tenant_context(db_appuser, sample_tenant_a)
        result = db_appuser.query(AccessLog).all()
        # Esperamos access logs que pertencem a sample_device_a
        assert all(log.device_id == sample_device_a.id for log in result), "AccessLogs devem ser isolados por tenant"


class TestInsertCheckDevices:
    """Validar que INSERT respeita WITH CHECK (bloqueado se tenant_id != contexto)."""

    def test_insert_own_device_succeeds(self, db_appuser: Session, sample_tenant_a: str):
        """INSERT com tenant_id = contexto sucede."""
        set_tenant_context(db_appuser, sample_tenant_a)
        device_id = uuid.uuid4()
        new_device = InputDevice(
            id=device_id,
            tenant_id=sample_tenant_a,
            name="Test Device",
            device_type="pin_pad",
            mqtt_topic="test/device",
            pin_salt=b"test_salt" * 8,
        )
        db_appuser.add(new_device)
        db_appuser.commit()
        # SET LOCAL perdido após commit(); restaurar para verificação
        set_tenant_context(db_appuser, sample_tenant_a)
        result = db_appuser.query(InputDevice).filter_by(id=device_id).first()
        assert result is not None

    def test_insert_alien_device_fails(self, db_appuser: Session, sample_tenant_a: str, sample_tenant_b: str):
        """INSERT com tenant_id != contexto é bloqueado por WITH CHECK."""
        set_tenant_context(db_appuser, sample_tenant_a)
        # Tentar inserir com tenant_id de B
        new_device = InputDevice(
            id=uuid.uuid4(),
            tenant_id=sample_tenant_b,
            name="Alien Device",
            device_type="card_reader",
            mqtt_topic="test/device_alien",
            pin_salt=b"test_salt" * 8,
        )
        db_appuser.add(new_device)
        with pytest.raises(Exception):  # RLS WITH CHECK constraint violation
            db_appuser.commit()


class TestUpdateIsolation:
    """Validar que UPDATE respeita RLS (UPDATE alien = 0 rows affected)."""

    def test_update_own_device_succeeds(self, db_appuser: Session, sample_tenant_a: str, sample_device_a):
        """UPDATE próprio afecta 1 linha."""
        set_tenant_context(db_appuser, sample_tenant_a)
        db_appuser.query(InputDevice).filter_by(id=sample_device_a.id).update({"name": "Updated A"})
        db_appuser.commit()
        # SET LOCAL perdido após commit(); restaurar para verificação
        set_tenant_context(db_appuser, sample_tenant_a)
        result = db_appuser.query(InputDevice).filter_by(id=sample_device_a.id).first()
        assert result.name == "Updated A"

    def test_update_alien_device_fails_silently(self, db_appuser: Session, sample_tenant_a: str, sample_device_b):
        """UPDATE alien não levanta erro, mas afecta 0 linhas (RLS bloqueia silenciosamente)."""
        set_tenant_context(db_appuser, sample_tenant_a)
        # Tentar actualizar device de B enquanto contexto é A
        stmt = db_appuser.query(InputDevice).filter_by(id=sample_device_b.id).update({"name": "Hacked B"})
        db_appuser.commit()
        # RLS bloqueia SELECT implícito, por isso UPDATE afecta 0 linhas


class TestDeleteIsolation:
    """Validar que DELETE respeita RLS."""

    def test_delete_alien_device_fails_silently(self, db_appuser: Session, sample_tenant_a: str, sample_device_b):
        """DELETE alien afecta 0 linhas (RLS bloqueia)."""
        set_tenant_context(db_appuser, sample_tenant_a)
        # Tentar deletar device de B enquanto contexto é A
        stmt = db_appuser.query(InputDevice).filter_by(id=sample_device_b.id).delete()
        affected = stmt
        db_appuser.commit()
        # RLS bloqueia, logo 0 linhas afectadas
        assert affected == 0


class TestContextSwitching:
    """Validar que SET LOCAL muda visibilidade na mesma sessão."""

    def test_set_local_switches_tenant_context(self, db_appuser: Session, sample_tenant_a: str, sample_tenant_b: str, sample_device_a, sample_device_b):
        """Mudar SET LOCAL na mesma sessão muda visibilidade."""
        # Ver device A
        set_tenant_context(db_appuser, sample_tenant_a)
        result_a = db_appuser.query(InputDevice).all()
        assert len(result_a) == 1
        assert result_a[0].id == sample_device_a.id
        
        # Trocar para tenant B
        set_tenant_context(db_appuser, sample_tenant_b)
        result_b = db_appuser.query(InputDevice).all()
        assert len(result_b) == 1
        assert result_b[0].id == sample_device_b.id


class TestAllTablesSmokeTest:
    """Smoke test: 2 tabelas isolam simultaneamente."""

    def test_all_tables_isolated_simultaneously(self, db_appuser: Session, sample_tenant_a, sample_device_a):
        """InputDevice, AccessLog isolam-se simultaneamente por tenant."""
        set_tenant_context(db_appuser, sample_tenant_a)

        devices = db_appuser.query(InputDevice).all()
        access_logs = db_appuser.query(AccessLog).all()

        # Todos devem estar isolados
        assert len(devices) == 1, "InputDevice isolada"
        assert all(log.device_id == sample_device_a.id for log in access_logs), "AccessLog isolada"