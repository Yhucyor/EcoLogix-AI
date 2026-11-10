const { useState, useEffect, useRef, useMemo } = React;

// ==================== 5. INVENTORY VIEW (MODULE 05) ====================
function InventoryView({ showToast, onRefreshHeader }) {
  const [tab, setTab] = useState('stock');
  const [invData, setInvData] = useState(null);
  const [whFilter, setWhFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [skuForm, setSkuForm] = useState({ sku: 'SKU-007', name: '', category: 'Đồ uống', unit: 'Thùng', unit_price: 185000, weight_kg: 10, min_stock: 40, max_stock: 300 });
  const [whForm, setWhForm] = useState({ name: '', code: '', address: '', capacity_m3: 2500 });
  const [txForm, setTxForm] = useState({ product_id: 1, warehouse_id: 1, to_warehouse_id: 2, trans_type: 'IN', quantity: 50, note: 'Nhập hàng bổ sung' });

  const load = async () => {
    try {
      const qs = new URLSearchParams();
      if (whFilter) qs.set('warehouse_id', whFilter);
      if (search) qs.set('search', search);
      const d = await apiFetch(`/api/inventory?${qs.toString()}`);
      setInvData(d);
    } catch (err) { showToast(err.message, 'error'); }
  };

  useEffect(() => { load(); }, [whFilter, search]);

  const addSku = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/inventory/products', { method: 'POST', body: JSON.stringify(skuForm) });
      showToast(r.message);
      setSkuForm({ ...skuForm, sku: '', name: '' });
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const removeSku = async (id) => {
    try {
      const r = await apiFetch(`/api/inventory/products/${id}`, { method: 'DELETE' });
      showToast(r.message);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const addWarehouse = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/inventory/warehouses', { method: 'POST', body: JSON.stringify(whForm) });
      showToast(r.message);
      setWhForm({ name: '', code: '', address: '', capacity_m3: 2500 });
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const submitTx = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/inventory/transactions', { method: 'POST', body: JSON.stringify(txForm) });
      showToast(r.message);
      load();
      onRefreshHeader();
    } catch (err) { showToast(err.message, 'error'); }
  };

  if (!invData) return <div className="p-8 text-xs text-text-sub">⏳ Đang tải dữ liệu kho...</div>;

  const stockRows = invData.inventory || [];
  const pagedStock = stockRows.slice((page - 1) * 8, page * 8);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 border-b border-border-light pb-2">
        {[
          { id: 'stock', label: '📦 Tồn kho hiện hữu' },
          { id: 'warehouses', label: '🏭 Kho bãi' },
          { id: 'skus', label: '🏷️ Danh mục SKU' },
          { id: 'tx', label: '🔄 Nhập / Xuất / Kiểm kê / Điều chuyển' },
          { id: 'history', label: '📜 Lịch sử giao dịch' }
        ].map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-xl text-xs font-bold ${tab === t.id ? 'bg-brand-600 text-white' : 'text-text-sub hover:bg-canvas'}`}>{t.label}</button>
        ))}
      </div>

      {tab === 'stock' && (
        <div className="bg-white p-5 rounded-2xl border border-border-light shadow-sm space-y-4">
          <div className="flex flex-wrap gap-3">
            <select value={whFilter} onChange={(e) => { setWhFilter(e.target.value); setPage(1); }} className="text-xs px-3 py-2 rounded-xl border border-border-light bg-canvas">
              <option value="">Tất cả các kho ({invData.warehouses.length})</option>
              {invData.warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
            <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Tìm mã SKU hoặc tên sản phẩm..." className="text-xs px-3 py-2 rounded-xl border border-border-light bg-canvas flex-1 min-w-[220px]" />
          </div>
          {pagedStock.length === 0 ? <EmptyState /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-canvas text-text-sub uppercase text-[11px]">
                  <tr><th className="p-3">Kho hàng</th><th className="p-3">SKU</th><th className="p-3">Sản phẩm</th><th className="p-3">Tồn kho</th><th className="p-3">Safety Stock</th><th className="p-3">Trạng thái</th></tr>
                </thead>
                <tbody>
                  {pagedStock.map((r) => {
                    const low = r.quantity <= r.safety_stock;
                    return (
                      <tr key={r.id} className="border-t border-border-light hover:bg-slate-50">
                        <td className="p-3 font-medium">{r.warehouse_name}</td>
                        <td className="p-3 font-mono font-bold text-brand-700">{r.sku}</td>
                        <td className="p-3">{r.product_name}</td>
                        <td className="p-3 font-mono font-bold">{r.quantity} {r.unit}</td>
                        <td className="p-3 font-mono">{r.safety_stock}</td>
                        <td className="p-3"><span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${low ? 'bg-amber-100 text-amber-800' : 'bg-emerald-50 text-brand-700'}`}>{low ? '⚠️ Cần nhập' : 'An toàn'}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <PaginationBar total={stockRows.length} page={page} pageSize={8} onPage={setPage} />
        </div>
      )}

      {tab === 'warehouses' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-7 space-y-3">
            {invData.warehouses.map((w) => (
              <div key={w.id} className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm flex justify-between items-center">
                <div>
                  <div className="font-bold text-sm text-text-main">{w.name} <span className="text-[11px] font-mono bg-sky-50 border border-sky-100 px-2 py-0.5 rounded ml-1">{w.code}</span></div>
                  <div className="text-xs text-text-sub mt-1">{w.address}</div>
                </div>
                <div className="text-right text-xs"><div className="font-bold text-brand-600">{w.capacity_m3} m³</div><div className="text-text-sub">Lấp đầy: {w.current_utilization_pct}%</div></div>
              </div>
            ))}
          </div>
          <form onSubmit={addWarehouse} className="lg:col-span-5 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs h-fit">
            <h4 className="font-extrabold text-sm m-0">➕ Thêm kho mới</h4>
            <input value={whForm.name} onChange={(e) => setWhForm({ ...whForm, name: e.target.value })} placeholder="Tên kho *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
            <input value={whForm.code} onChange={(e) => setWhForm({ ...whForm, code: e.target.value })} placeholder="Mã kho (VD: WH-Q7-01) *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
            <input value={whForm.address} onChange={(e) => setWhForm({ ...whForm, address: e.target.value })} placeholder="Địa chỉ *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
            <input type="number" value={whForm.capacity_m3} onChange={(e) => setWhForm({ ...whForm, capacity_m3: Number(e.target.value) })} placeholder="Sức chứa m³" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" />
            <button type="submit" className="w-full py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold shadow-md shadow-brand-500/20">Lưu kho mới</button>
          </form>
        </div>
      )}

      {tab === 'skus' && (
        <InventorySkuPanel
          products={invData.products}
          skuForm={skuForm}
          setSkuForm={setSkuForm}
          onAddSku={addSku}
          onDeleteSku={removeSku}
          onReload={load}
          showToast={showToast}
        />
      )}

      {tab === 'tx' && (
        <form onSubmit={submitTx} className="max-w-xl eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs">
          <h4 className="font-extrabold text-sm m-0">Thực hiện Giao dịch Kho (Ghi trực tiếp SQLite)</h4>
          <div className="grid grid-cols-2 gap-3">
            <select value={txForm.trans_type} onChange={(e) => setTxForm({ ...txForm, trans_type: e.target.value })} className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 font-bold">
              <option value="IN">Nhập kho (IN)</option>
              <option value="OUT">Xuất kho (OUT)</option>
              <option value="ADJUST">Kiểm kê thực tế (ADJUST)</option>
              <option value="TRANSFER">Điều chuyển giữa 2 kho (TRANSFER)</option>
            </select>
            <select value={txForm.product_id} onChange={(e) => setTxForm({ ...txForm, product_id: Number(e.target.value) })} className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70">
              {invData.products.map((p) => <option key={p.id} value={p.id}>{p.sku} - {p.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select value={txForm.warehouse_id} onChange={(e) => setTxForm({ ...txForm, warehouse_id: Number(e.target.value) })} className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70">
              {invData.warehouses.map((w) => <option key={w.id} value={w.id}>Kho: {w.name}</option>)}
            </select>
            {txForm.trans_type === 'TRANSFER' && (
              <select value={txForm.to_warehouse_id} onChange={(e) => setTxForm({ ...txForm, to_warehouse_id: Number(e.target.value) })} className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70">
                {invData.warehouses.map((w) => <option key={w.id} value={w.id}>Đến: {w.name}</option>)}
              </select>
            )}
          </div>
          <input type="number" value={txForm.quantity} onChange={(e) => setTxForm({ ...txForm, quantity: Number(e.target.value) })} placeholder="Số lượng" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
          <input value={txForm.note} onChange={(e) => setTxForm({ ...txForm, note: e.target.value })} placeholder="Ghi chú chứng từ" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
          <button type="submit" className="w-full py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold shadow-md shadow-brand-500/20">Xác nhận giao dịch</button>
        </form>
      )}

      {tab === 'history' && (
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">Thời gian</th><th className="p-2.5">Loại</th><th className="p-2.5">SKU</th><th className="p-2.5">Kho</th><th className="p-2.5">SL</th><th className="p-2.5">Ghi chú</th></tr></thead>
            <tbody>
              {invData.transactions.map((t) => (
                <tr key={t.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30 transition">
                  <td className="p-2.5 text-slate-500">{t.created_at}</td>
                  <td className="p-2.5 font-bold">{t.transaction_type}</td>
                  <td className="p-2.5 font-mono">{t.sku}</td>
                  <td className="p-2.5">{t.warehouse_name}</td>
                  <td className="p-2.5 font-bold">{t.quantity}</td>
                  <td className="p-2.5">{t.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InventorySkuPanel({ products, skuForm, setSkuForm, onAddSku, onDeleteSku, onReload, showToast }) {
  const [editing, setEditing] = useState(null);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [saving, setSaving] = useState(false);

  const saveEdit = async (e) => {
    e.preventDefault();
    if (!editing) return;
    setSaving(true);
    try {
      const r = await apiFetch(`/api/inventory/products/${editing.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editing.name,
          category: editing.category || 'Đồ uống',
          unit: editing.unit || 'Thùng',
          unit_price: Number(editing.unit_price),
          weight_kg: Number(editing.weight_kg),
          min_stock: Number(editing.min_stock || 40),
          max_stock: Number(editing.max_stock || 300),
        }),
      });
      showToast(r.message);
      setEditing(null);
      await onReload();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8 eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub">
              <tr>
                <th className="p-2.5">SKU</th>
                <th className="p-2.5">Tên sản phẩm</th>
                <th className="p-2.5">Danh mục</th>
                <th className="p-2.5">Giá</th>
                <th className="p-2.5">Tổng tồn</th>
                <th className="p-2.5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30 transition">
                  <td className="p-2.5 font-mono font-bold text-brand-700">{p.sku}</td>
                  <td className="p-2.5 font-semibold">{p.name}</td>
                  <td className="p-2.5 text-slate-500">{p.category}</td>
                  <td className="p-2.5 font-mono">{fmtVnd(p.unit_price)}</td>
                  <td className="p-2.5 font-bold text-brand-600">{p.total_stock} {p.unit}</td>
                  <td className="p-2.5 text-right space-x-2 whitespace-nowrap">
                    <button onClick={() => setEditing({ ...p })} className="text-brand-600 hover:underline font-bold">Sửa</button>
                    <button onClick={() => setConfirmTarget(p)} className="text-red-500 hover:underline font-bold">Xóa</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form onSubmit={onAddSku} className="lg:col-span-4 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-2.5 text-xs h-fit">
          <h4 className="font-extrabold text-sm m-0">➕ Thêm sản phẩm SKU</h4>
          <input value={skuForm.sku} onChange={(e) => setSkuForm({ ...skuForm, sku: e.target.value })} placeholder="Mã SKU *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
          <input value={skuForm.name} onChange={(e) => setSkuForm({ ...skuForm, name: e.target.value })} placeholder="Tên sản phẩm *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
          <div className="grid grid-cols-2 gap-2">
            <input value={skuForm.category} onChange={(e) => setSkuForm({ ...skuForm, category: e.target.value })} placeholder="Danh mục" className="px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
            <input value={skuForm.unit} onChange={(e) => setSkuForm({ ...skuForm, unit: e.target.value })} placeholder="Đơn vị" className="px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input type="number" value={skuForm.unit_price} onChange={(e) => setSkuForm({ ...skuForm, unit_price: Number(e.target.value) })} placeholder="Đơn giá" className="px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
            <input type="number" step="0.5" value={skuForm.weight_kg} onChange={(e) => setSkuForm({ ...skuForm, weight_kg: Number(e.target.value) })} placeholder="KL (kg)" className="px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
          </div>
          <button type="submit" className="w-full py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold shadow-md shadow-brand-500/20">Lưu SKU mới</button>
        </form>
      </div>

      <ModalShell open={!!editing} title={`✏️ Chỉnh sửa SKU ${editing?.sku || ''}`} onClose={() => setEditing(null)}>
        {editing && (
          <form onSubmit={saveEdit} className="space-y-3 text-xs">
            <div>
              <label className="font-bold text-slate-600 block mb-1">Tên sản phẩm *</label>
              <input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-slate-600 block mb-1">Danh mục</label>
                <input value={editing.category || ''} onChange={(e) => setEditing({ ...editing, category: e.target.value })} className="w-full px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
              <div>
                <label className="font-bold text-slate-600 block mb-1">Đơn vị tính</label>
                <input value={editing.unit || ''} onChange={(e) => setEditing({ ...editing, unit: e.target.value })} className="w-full px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-slate-600 block mb-1">Đơn giá (VNĐ)</label>
                <input type="number" value={editing.unit_price} onChange={(e) => setEditing({ ...editing, unit_price: Number(e.target.value) })} className="w-full px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50" required />
              </div>
              <div>
                <label className="font-bold text-slate-600 block mb-1">Khối lượng (kg)</label>
                <input type="number" step="0.5" value={editing.weight_kg} onChange={(e) => setEditing({ ...editing, weight_kg: Number(e.target.value) })} className="w-full px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50" required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-slate-600 block mb-1">Tồn tối thiểu (Min)</label>
                <input type="number" value={editing.min_stock ?? 40} onChange={(e) => setEditing({ ...editing, min_stock: Number(e.target.value) })} className="w-full px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
              <div>
                <label className="font-bold text-slate-600 block mb-1">Tồn tối đa (Max)</label>
                <input type="number" value={editing.max_stock ?? 300} onChange={(e) => setEditing({ ...editing, max_stock: Number(e.target.value) })} className="w-full px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="px-4 py-2 rounded-full border border-slate-300 font-bold text-slate-600">Hủy</button>
              <button type="submit" disabled={saving} className="px-5 py-2 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold">
                {saving ? 'Đang lưu...' : '💾 Lưu thay đổi'}
              </button>
            </div>
          </form>
        )}
      </ModalShell>

      <ConfirmModal
        open={!!confirmTarget}
        title="Xác nhận xóa SKU"
        message={`Bạn có chắc muốn xóa sản phẩm "${confirmTarget?.sku} - ${confirmTarget?.name}"? Thao tác này cũng xóa dữ liệu tồn kho liên quan.`}
        confirmText="Xóa SKU"
        onCancel={() => setConfirmTarget(null)}
        onConfirm={async () => {
          const id = confirmTarget.id;
          setConfirmTarget(null);
          await onDeleteSku(id);
        }}
      />
    </>
  );
}

Object.assign(window, { InventoryView });
