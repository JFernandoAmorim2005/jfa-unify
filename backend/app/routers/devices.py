"""
Router de dispositivos de entrada (PIN pad / leitor de cartão).
Operações CRUD com isolamento por tenant.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_tenant
from app.middleware.auth import get_tenant_id
from app.models.device import InputDevice
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
from app.services.access_crypto import hash_pin_for_device, generate_pin_salt

router = APIRouter()


def _inject_card_count(device: InputDevice) -> InputDevice:
    """Injeta o campo calculado card_count (UIDs sem chaves internas __)."""
    device.card_count = sum(
        1 for k in (device.card_uids or {}) if not k.startswith("__")
    )
    return device


@router.get("/", response_model=List[DeviceRead])
def list_devices(
    db: Session = Depends(get_db_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Lista todos os dispositivos do tenant (RLS filtra automaticamente)."""
    devices = (
        db.query(InputDevice)
        .filter(InputDevice.tenant_id == tenant_id)
        .all()
    )
    return [_inject_card_count(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(
    device_id: uuid.UUID,
    db: Session = Depends(get_db_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna um dispositivo pelo ID."""
    return _inject_card_count(_get_or_404(db, device_id, tenant_id))


@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Cria um novo dispositivo para o tenant."""
    if payload.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id no corpo não corresponde ao token.",
        )

    # Gerar salt e hash do PIN
    salt = generate_pin_salt()
    card_uids_dict: dict = {}

    if payload.pin_plain:
        pin_hash = hash_pin_for_device(payload.pin_plain, salt)
        card_uids_dict["__pin__"] = pin_hash

    for uid in payload.card_uids:
        card_uids_dict[uid.upper()] = True

    device = InputDevice(
        tenant_id=tenant_id,
        name=payload.name,
        device_type=payload.device_type,
        mqtt_topic=payload.mqtt_topic,
        mqtt_backend=payload.mqtt_backend,
        auth_mode=payload.auth_mode,
        pin_salt=salt,
        pin_hash_algorithm="hmac_sha256",
        card_uids=card_uids_dict,
        enabled=payload.enabled,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return _inject_card_count(device)


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: uuid.UUID,
    payload: DeviceUpdate,
    db: Session = Depends(get_db_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Actualiza campos de um dispositivo existente."""
    device = _get_or_404(db, device_id, tenant_id)
    update_data = payload.model_dump(exclude_unset=True)

    # PIN em texto limpo → gerar novo hash com mesmo salt
    if "pin_plain" in update_data:
        pin_plain = update_data.pop("pin_plain")
        if pin_plain:
            new_hash = hash_pin_for_device(pin_plain, device.pin_salt)
            # Actualizar hash dentro do JSONB card_uids
            card_uids = dict(device.card_uids or {})
            card_uids["__pin__"] = new_hash
            device.card_uids = card_uids
        else:
            card_uids = dict(device.card_uids or {})
            card_uids.pop("__pin__", None)
            device.card_uids = card_uids

    # UIDs de cartão → substituir lista (sem o campo __pin__)
    if "card_uids" in update_data:
        new_uids = update_data.pop("card_uids")
        card_uids = {k: v for k, v in (device.card_uids or {}).items() if k.startswith("__")}
        if new_uids:
            for uid in new_uids:
                card_uids[uid.upper()] = True
        device.card_uids = card_uids

    for field, value in update_data.items():
        setattr(device, field, value)

    db.commit()
    db.refresh(device)
    return _inject_card_count(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: uuid.UUID,
    db: Session = Depends(get_db_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Desactiva (soft delete) um dispositivo."""
    device = _get_or_404(db, device_id, tenant_id)
    device.enabled = False
    db.commit()


# --- Helpers ---

def _get_or_404(db: Session, device_id: uuid.UUID, tenant_id: uuid.UUID) -> InputDevice:
    device = (
        db.query(InputDevice)
        .filter(InputDevice.id == device_id, InputDevice.tenant_id == tenant_id)
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispositivo {device_id} não encontrado.",
        )
    return device
