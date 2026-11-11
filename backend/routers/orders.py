"""Orders Management Routes."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_current_user, require_roles
from backend.services.inventory_service import get_all_products, get_all_warehouses
from backend.services.order_service import (
    create_order,
    delete_order,
    get_order_detail,
    get_order_stats,
    get_orders,
    update_order_status,
)
from backend.services.partner_service import get_customers

router = APIRouter(prefix="/api/orders", tags=["Orders"])


class OrderCreateReq(BaseModel):
    order_code: str
    customer_id: int
    warehouse_id: int
    time_window_start: str = "08:00"
    time_window_end: str = "11:30"
    product_id: Optional[int] = None
    quantity: int = 10
    shipping_fee: float = 180000.0


class OrderStatusReq(BaseModel):
    status: str


@router.get("")
def api_orders(status: str = "ALL", province: str = "ALL", search: str = "", user: Dict[str, Any] = Depends(get_current_user)):
    company_id = user.get("company_id") or 1
    return {
        "orders": get_orders(company_id=company_id, status=status, province=province, search=search, limit=200),
        "stats": get_order_stats(company_id=company_id),
        "customers": get_customers(company_id=company_id),
        "warehouses": get_all_warehouses(company_id=company_id),
        "products": get_all_products(company_id=company_id),
    }


@router.get("/{order_id}")
def api_order_detail(order_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    company_id = user.get("company_id") or 1
    detail = get_order_detail(order_id, company_id=company_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    return detail


@router.post("")
def api_create_order(req: OrderCreateReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    items = [{"product_id": req.product_id, "quantity": req.quantity}] if req.product_id else []
    company_id = user.get("company_id") or 1
    ok, msg, oid = create_order(
        order_code=req.order_code,
        customer_id=req.customer_id,
        warehouse_id=req.warehouse_id,
        time_window_start=req.time_window_start,
        time_window_end=req.time_window_end,
        items=items,
        shipping_fee=req.shipping_fee,
        company_id=company_id,
        user_id=user["id"],
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "order_id": oid}


@router.patch("/{order_id}/status")
def api_order_status(order_id: int, req: OrderStatusReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    company_id = user.get("company_id") or 1
    ok, msg = update_order_status(order_id, req.status, company_id=company_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.delete("/{order_id}")
def api_delete_order(order_id: int, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    company_id = user.get("company_id") or 1
    ok, msg = delete_order(order_id, company_id=company_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

