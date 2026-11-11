"""Vehicles & Fleet Management Routes."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_current_user, require_roles
from backend.services.vehicle_service import (
    add_vehicle,
    delete_vehicle,
    get_vehicles_with_stats,
    update_vehicle,
)

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])


class VehicleReq(BaseModel):
    plate_number: str = ""
    vehicle_name: str
    vehicle_type: str = "Tải nhẹ đô thị"
    max_load_kg: float = 1500.0
    fuel_type: str = "Diesel"
    fuel_consumption_per_100km: float = 11.5
    operational_cost_per_km: float = 3800.0
    status: str = "Available"


@router.get("")
def api_vehicles(user: Dict[str, Any] = Depends(get_current_user)):
    company_id = user.get("company_id") or 1
    return {"vehicles": get_vehicles_with_stats(company_id=company_id)}


@router.post("")
def api_add_vehicle(req: VehicleReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    company_id = user.get("company_id") or 1
    ok, msg = add_vehicle(
        req.plate_number,
        req.vehicle_name,
        req.vehicle_type,
        req.max_load_kg,
        req.fuel_type,
        req.fuel_consumption_per_100km,
        req.operational_cost_per_km,
        company_id=company_id,
        user_id=user["id"],
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.put("/{vehicle_id}")
def api_update_vehicle(vehicle_id: int, req: VehicleReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    company_id = user.get("company_id") or 1
    ok, msg = update_vehicle(
        vehicle_id,
        req.vehicle_name,
        req.vehicle_type,
        req.max_load_kg,
        req.fuel_type,
        req.fuel_consumption_per_100km,
        req.operational_cost_per_km,
        req.status,
        company_id=company_id,
        user_id=user["id"],
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.delete("/{vehicle_id}")
def api_delete_vehicle(vehicle_id: int, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    company_id = user.get("company_id") or 1
    ok, msg = delete_vehicle(vehicle_id, company_id=company_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

