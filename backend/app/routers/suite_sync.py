"""JFA Suite Integration — Sync Endpoint (Phase 1)"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.middleware.auth import verify_tenant_token
from app.models import Device, AccessLog

router = APIRouter(prefix="/api/v1/suite", tags=["suite"])


class DeviceSyncPayload(BaseModel):
    device_id: str
    device_name: str
    device_type: str  # lock, camera, etc
    status: str  # active, inactive, error
    battery_level: int | None = None
    last_sync: datetime


class SyncRequest(BaseModel):
    tenant_id: str
    devices: List[DeviceSyncPayload]
    access_log_count: int
    month: str  # YYYY-MM


class SyncResponse(BaseModel):
    status: str  # success, error
    synced_at: datetime
    devices_count: int
    usage_stats: dict


@router.post("/sync", response_model=SyncResponse)
async def sync_to_suite(
    payload: SyncRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(verify_tenant_token),
):
    """
    Phase 1: Sync device list and usage stats to JFA Suite.

    Used by: Madeira clients (hotels, schools, residencies)
    Purpose: Auto-billing, unified dashboard, analytics

    Flow:
    1. Receive device list + usage stats from JFA_Unify
    2. Count active devices, access events, battery status
    3. Calculate monthly usage for billing (EUR X per device)
    4. Send to JFA_Suite via HTTP POST (webhook Phase 2)

    Returns:
    - success/error status
    - synced_at timestamp
    - devices_count (for billing)
    - usage_stats (access events, device types, etc)
    """
    try:
        # Validate tenant authorization
        if payload.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant mismatch"
            )

        # Query device count from database
        from sqlalchemy import func, select
        device_query = select(func.count(Device.id)).where(
            Device.tenant_id == tenant_id
        )
        result = await db.execute(device_query)
        db_device_count = result.scalar()

        # Query access log count for the month
        from sqlalchemy import and_
        log_query = select(func.count(AccessLog.id)).where(
            and_(
                AccessLog.tenant_id == tenant_id,
                AccessLog.created_at >= datetime(2026, int(payload.month.split('-')[1]), 1),
                AccessLog.created_at < datetime(2026, int(payload.month.split('-')[1]) + 1, 1)
            )
        )
        result = await db.execute(log_query)
        db_log_count = result.scalar()

        # Build usage stats
        usage_stats = {
            "devices_total": db_device_count,
            "devices_active": sum(1 for d in payload.devices if d.status == "active"),
            "devices_inactive": sum(1 for d in payload.devices if d.status == "inactive"),
            "devices_error": sum(1 for d in payload.devices if d.status == "error"),
            "access_events": db_log_count,
            "device_types": {},
            "battery_status": {
                "critical": sum(1 for d in payload.devices if d.battery_level and d.battery_level < 20),
                "low": sum(1 for d in payload.devices if d.battery_level and 20 <= d.battery_level < 50),
                "ok": sum(1 for d in payload.devices if d.battery_level and d.battery_level >= 50),
            }
        }

        # Count device types
        for device in payload.devices:
            device_type = device.device_type
            usage_stats["device_types"][device_type] = usage_stats["device_types"].get(device_type, 0) + 1

        # TODO Phase 2: Send to JFA_Suite webhook (await suite_client.sync(payload, usage_stats))
        # TODO Phase 3: Trigger auto-billing calculation (EUR X per device/month)

        return SyncResponse(
            status="success",
            synced_at=datetime.utcnow(),
            devices_count=db_device_count,
            usage_stats=usage_stats
        )

    except Exception as e:
        return SyncResponse(
            status=f"error: {str(e)}",
            synced_at=datetime.utcnow(),
            devices_count=0,
            usage_stats={}
        )


@router.get("/status")
async def suite_integration_status(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(verify_tenant_token),
):
    """Check Suite integration status and last sync."""
    # TODO: Query SyncLog or similar to return last sync timestamp
    return {
        "status": "operational",
        "phase": "Phase 1 (API sync endpoint)",
        "last_sync": None,  # TBD: track in database
        "next_sync": "TBD (Phase 2: webhook automation)"
    }
