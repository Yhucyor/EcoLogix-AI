"""Inventory, Warehouses, Products & Stock Transactions Routes."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_current_user, require_roles
from backend.services.inventory_service import (
    add_product,
    add_warehouse,
    delete_product,
    get_all_products,
    get_all_warehouses,
    get_inventory_metrics,
    get_inventory_status,
    get_transaction_history,
    record_transaction,
    transfer_stock,
    update_product,
)

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


class ProductReq(BaseModel):
    sku: str
    name: str
    category: str = "Đồ uống"
    unit: str = "Thùng"
    unit_price: float
    weight_kg: float
    min_stock: int = 40
    max_stock: int = 300


class ProductUpdateReq(BaseModel):
    name: str
    category: str
    unit: str
    unit_price: float
    weight_kg: float
    min_stock: int = 40
    max_stock: int = 300


class WarehouseReq(BaseModel):
    name: str
    code: str
    address: str
    capacity_m3: float = 2500.0


class InventoryTxReq(BaseModel):
    product_id: int
    warehouse_id: int
    to_warehouse_id: Optional[int] = None
    trans_type: str
    quantity: int
    note: str = ""


@router.get("")
def api_inventory(warehouse_id: Optional[int] = None, search: str = "", user: Dict[str, Any] = Depends(get_current_user)):
    company_id = user.get("company_id") or 1
    return {
        "warehouses": get_all_warehouses(company_id=company_id),
        "products": get_all_products(company_id=company_id),
        "inventory": get_inventory_status(company_id=company_id, warehouse_id=warehouse_id, search=search),
        "transactions": get_transaction_history(company_id=company_id, limit=50),
        "metrics": get_inventory_metrics(company_id=company_id),
    }


@router.post("/products")
def api_add_product(req: ProductReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    company_id = user.get("company_id") or 1
    ok, msg = add_product(
        company_id, req.sku, req.name, req.category, req.unit, req.unit_price, req.weight_kg, req.min_stock, req.max_stock, user_id=user["id"]
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.put("/products/{product_id}")
def api_update_product(product_id: int, req: ProductUpdateReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg = update_product(
        product_id, req.name, req.category, req.unit, req.unit_price, req.weight_kg, req.min_stock, req.max_stock, user_id=user["id"]
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.delete("/products/{product_id}")
def api_delete_product(product_id: int, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    ok, msg = delete_product(product_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/warehouses")
def api_add_warehouse(req: WarehouseReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    company_id = user.get("company_id") or 1
    ok, msg = add_warehouse(req.name, req.code, req.address, req.capacity_m3, company_id=company_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/transactions")
def api_inventory_tx(req: InventoryTxReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    if req.trans_type == "TRANSFER":
        if not req.to_warehouse_id:
            raise HTTPException(status_code=400, detail="Thiếu kho đích để điều chuyển.")
        ok, msg = transfer_stock(req.product_id, req.warehouse_id, req.to_warehouse_id, req.quantity, req.note, user_id=user["id"])
    else:
        ok, msg = record_transaction(req.product_id, req.warehouse_id, req.trans_type, req.quantity, req.note, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

