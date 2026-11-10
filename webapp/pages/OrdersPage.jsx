const { useState, useEffect, useRef, useMemo } = React;

// ==================== 7. ORDERS VIEW (MODULE 07) ====================
function OrdersView({ showToast, onRefreshHeader }) {
  const [data, setData] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [provFilter, setProvFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [detailModal, setDetailModal] = useState(null);
  const [newOrder, setNewOrder] = useState({ order_code: '', customer_id: 1, warehouse_id: 1, product_id: 1, quantity: 10, time_window_start: '08:00', time_window_end: '11:30', shipping_fee: 180000 });

  const load = async () => {
    try {
      const qs = new URLSearchParams({ status: statusFilter, province: provFilter, search });
      const d = await apiFetch(`/api/orders?${qs.toString()}`);
      setData(d);
      if (!newOrder.order_code) setNewOrder((p) => ({ ...p, order_code: `ORD-2026-${String((d.stats?.total || 28) + 1).padStart(3, '0')}` }));
    } catch (err) { showToast(err.message, 'error'); }
  };

  useEffect(() => { load(); }, [statusFilter, provFilter, search]);

  const openDetail = async (id) => {
    try {
      const d = await apiFetch(`/api/orders/${id}`);
      setDetailModal(d);
    } catch (err) { showToast(err.message, 'error'); }
  };

  const changeStatus = async (id, st) => {
    try {
      const r = await apiFetch(`/api/orders/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status: st }) });
      showToast(r.message);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const removeOrder = async (id) => {
    try {
      const r = await apiFetch(`/api/orders/${id}`, { method: 'DELETE' });
      showToast(r.message);
      load();
      onRefreshHeader();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const submitCreate = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/orders', { method: 'POST', body: JSON.stringify(newOrder) });
      showToast(r.message);
      setNewOrder({ ...newOrder, order_code: '' });
      load();
      onRefreshHeader();
    } catch (err) { showToast(err.message, 'error'); }
  };

  if (!data) return <div className="p-8 text-xs text-text-sub">⏳ Đang tải danh sách đơn hàng...</div>;
  const paged = (data.orders || []).slice((page - 1) * 8, page * 8);

  return (
    <div className="space-y-5">
      {detailModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b pb-3">
              <h4 className="font-extrabold text-base m-0">Chi tiết Đơn {detailModal.order_code}</h4>
              <button onClick={() => setDetailModal(null)} className="text-slate-400 hover:text-slate-700 font-bold">✕</button>
            </div>
            <div className="text-xs space-y-1.5 text-slate-700">
              <div><strong>Khách hàng:</strong> {detailModal.customer_name} ({detailModal.customer_phone})</div>
              <div><strong>Địa chỉ giao:</strong> {detailModal.delivery_address} — {detailModal.district}, {detailModal.province}</div>
              <div><strong>Kho xuất:</strong> {detailModal.warehouse_name} | <strong>Giờ nhận:</strong> {detailModal.time_window_start} – {detailModal.time_window_end}</div>
              <div><strong>Tổng khối lượng:</strong> {detailModal.total_weight_kg} kg | <strong>Tổng tiền:</strong> {fmtVnd(detailModal.total_amount)}</div>
            </div>
            <div className="bg-canvas p-3 rounded-xl text-xs">
              <strong className="block mb-2">Danh sách sản phẩm (`order_items`):</strong>
              {detailModal.items?.length ? detailModal.items.map((it) => (
                <div key={it.id} className="flex justify-between py-1 border-b border-slate-200 last:border-0">
                  <span>{it.sku} - {it.product_name} (x{it.quantity})</span>
                  <span className="font-mono font-bold">{fmtVnd(it.unit_price * it.quantity)}</span>
                </div>
              )) : <span>Không có dòng sản phẩm chi tiết.</span>}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Tổng đơn hàng</div><div className="font-mono text-2xl font-extrabold">{data.stats.total}</div></div>
        <div className="bg-white p-4 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Chờ xử lý</div><div className="font-mono text-2xl font-extrabold text-amber-600">{data.stats.pending + data.stats.processing}</div></div>
        <div className="bg-white p-4 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Đang giao</div><div className="font-mono text-2xl font-extrabold text-blue-600">{data.stats.shipping}</div></div>
        <div className="bg-white p-4 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Hoàn thành</div><div className="font-mono text-2xl font-extrabold text-brand-600">{data.stats.completed}</div></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8 bg-white p-5 rounded-2xl border border-border-light shadow-sm space-y-4">
          <div className="flex flex-wrap gap-2">
            <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Tìm mã đơn / khách..." className="flex-1 min-w-[160px] text-xs px-3 py-2 rounded-xl border border-border-light bg-canvas" />
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="text-xs px-3 py-2 rounded-xl border border-border-light bg-canvas">
              <option value="ALL">Tất cả trạng thái</option><option value="PENDING">PENDING</option><option value="PROCESSING">PROCESSING</option><option value="SHIPPING">SHIPPING</option><option value="COMPLETED">COMPLETED</option><option value="CANCELLED">CANCELLED</option>
            </select>
            <select value={provFilter} onChange={(e) => { setProvFilter(e.target.value); setPage(1); }} className="text-xs px-3 py-2 rounded-xl border border-border-light bg-canvas">
              <option value="ALL">Tất cả Tỉnh/TP</option><option value="TP.HCM">TP.HCM</option><option value="Bình Dương">Bình Dương</option><option value="Đồng Nai">Đồng Nai</option>
            </select>
          </div>
          {paged.length === 0 ? <EmptyState /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-canvas text-text-sub"><tr><th className="p-2.5">Mã đơn</th><th className="p-2.5">Khách hàng</th><th className="p-2.5">KL</th><th className="p-2.5">Giá trị</th><th className="p-2.5">Trạng thái</th><th className="p-2.5">Tác vụ</th></tr></thead>
                <tbody>
                  {paged.map((o) => (
                    <tr key={o.id} className="border-t border-border-light">
                      <td className="p-2.5 font-mono font-bold text-brand-700 cursor-pointer hover:underline" onClick={() => openDetail(o.id)}>{o.order_code}</td>
                      <td className="p-2.5"><div>{o.customer_name}</div><div className="text-[10px] text-text-sub">{o.district}, {o.province}</div></td>
                      <td className="p-2.5 font-mono">{o.total_weight_kg}kg</td>
                      <td className="p-2.5 font-mono">{fmtVnd(o.total_amount)}</td>
                      <td className="p-2.5">
                        <select value={o.status} onChange={(e) => changeStatus(o.id, e.target.value)} className="text-[11px] px-2 py-1 rounded-lg border border-border-light bg-canvas font-bold">
                          <option>PENDING</option><option>PROCESSING</option><option>SHIPPING</option><option>COMPLETED</option><option>CANCELLED</option>
                        </select>
                      </td>
                      <td className="p-2.5 flex gap-2"><button onClick={() => openDetail(o.id)} className="text-blue-600 font-bold">Xem</button><button onClick={() => removeOrder(o.id)} className="text-red-500 font-bold">Xóa</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <PaginationBar total={data.orders.length} page={page} pageSize={8} onPage={setPage} />
        </div>

        <form onSubmit={submitCreate} className="lg:col-span-4 bg-white p-5 rounded-2xl border border-border-light shadow-sm space-y-3 text-xs h-fit">
          <h4 className="font-extrabold text-sm m-0">➕ Tạo Đơn Hàng Mới (Trừ Kho)</h4>
          <input value={newOrder.order_code} onChange={(e) => setNewOrder({ ...newOrder, order_code: e.target.value })} placeholder="Mã đơn *" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" required />
          <select value={newOrder.customer_id} onChange={(e) => setNewOrder({ ...newOrder, customer_id: Number(e.target.value) })} className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas">
            {data.customers.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.district})</option>)}
          </select>
          <select value={newOrder.warehouse_id} onChange={(e) => setNewOrder({ ...newOrder, warehouse_id: Number(e.target.value) })} className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas">
            {data.warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <div className="grid grid-cols-3 gap-2">
            <select value={newOrder.product_id} onChange={(e) => setNewOrder({ ...newOrder, product_id: Number(e.target.value) })} className="col-span-2 px-2 py-2 rounded-xl border border-border-light bg-canvas">
              {data.products.map((p) => <option key={p.id} value={p.id}>{p.sku} - {p.name}</option>)}
            </select>
            <input type="number" min="1" value={newOrder.quantity} onChange={(e) => setNewOrder({ ...newOrder, quantity: Number(e.target.value) })} className="px-2 py-2 rounded-xl border border-border-light bg-canvas" />
          </div>
          <button type="submit" className="w-full py-2.5 rounded-xl bg-brand-600 text-white font-bold">Lưu Đơn Hàng</button>
        </form>
      </div>
    </div>
  );
}

Object.assign(window, { OrdersView });
