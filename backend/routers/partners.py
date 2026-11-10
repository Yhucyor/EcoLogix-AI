"""Customers & Suppliers Partner Management Routes."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_current_user, require_roles
from backend.services.partner_service import (
    add_customer,
    add_supplier,
    delete_customer,
    delete_supplier,
    get_customer_orders,
    get_customers,
    get_suppliers,
    update_customer,
    update_supplier,
    update_supplier_debt,
)

router = APIRouter(prefix="/api/partners", tags=["Partners"])


class CustomerReq(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    district: str = "Quận 1"
    province: str = "TP.HCM"
    customer_tier: str = "Standard"


class SupplierReq(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    products_supplied: str = ""
    debt_vnd: float = 0.0


class DebtUpdateReq(BaseModel):
    debt_vnd: float


@router.get("")
def api_partners(search: str = "", tier: str = "ALL", _: Dict[str, Any] = Depends(get_current_user)):
    return {
        "customers": get_customers(search=search, tier=tier),
        "suppliers": get_suppliers(search=search),
    }


@router.get("/customers/{customer_id}/orders")
def api_customer_orders(customer_id: int, _: Dict[str, Any] = Depends(get_current_user)):
    return {"orders": get_customer_orders(customer_id)}


@router.post("/customers")
def api_add_customer(req: CustomerReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg = add_customer(
        req.name, req.phone, req.email, req.address, req.district, req.province, req.customer_tier, user_id=user["id"]
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.put("/customers/{customer_id}")
def api_update_customer(customer_id: int, req: CustomerReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg = update_customer(
        customer_id, req.name, req.phone, req.email, req.address, req.district, req.province, req.customer_tier, user_id=user["id"]
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.delete("/customers/{customer_id}")
def api_delete_customer(customer_id: int, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    ok, msg = delete_customer(customer_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/suppliers")
def api_add_supplier(req: SupplierReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg = add_supplier(req.name, req.phone, req.email, req.address, req.products_supplied, req.debt_vnd, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.put("/suppliers/{supplier_id}")
def api_update_supplier(supplier_id: int, req: SupplierReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg = update_supplier(
        supplier_id, req.name, req.phone, req.email, req.address, req.products_supplied, req.debt_vnd, user_id=user["id"]
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.patch("/suppliers/{supplier_id}/debt")
def api_update_debt(supplier_id: int, req: DebtUpdateReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    ok, msg = update_supplier_debt(supplier_id, req.debt_vnd, user_id=user["id"])
    return {"ok": ok, "message": msg}


@router.delete("/suppliers/{supplier_id}")
def api_delete_supplier(supplier_id: int, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    ok, msg = delete_supplier(supplier_id, user_id=user["id"])
    return {"ok": ok, "message": msg}

