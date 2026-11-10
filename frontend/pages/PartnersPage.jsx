const { useState, useEffect, useRef, useMemo } = React;

// ==================== 10 & 11. PARTNERS VIEW (CUSTOMERS & SUPPLIERS) ====================
function PartnersView({ showToast }) {
  const [tab, setTab] = useState('customers');
  const [data, setData] = useState({ customers: [], suppliers: [] });
  const [search, setSearch] = useState('');
  const [custOrders, setCustOrders] = useState(null);
  const [editCustomer, setEditCustomer] = useState(null);
  const [editSupplier, setEditSupplier] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null); // { kind: 'customer'|'supplier', item }
  const [cForm, setCForm] = useState({ name: '', phone: '', email: '', address: '', district: 'Quận 1', province: 'TP.HCM', customer_tier: 'Standard' });
  const [sForm, setSForm] = useState({ name: '', phone: '', email: '', address: '', products_supplied: '', debt_vnd: 0 });

  const load = () => apiFetch(`/api/partners?search=${encodeURIComponent(search)}`).then(setData).catch((e) => showToast(e.message, 'error'));
  useEffect(() => { load(); }, [search]);

  const viewHist = async (c) => {
    const res = await apiFetch(`/api/partners/customers/${c.id}/orders`);
    setCustOrders({ customer: c, orders: res.orders || [] });
  };

  const addCust = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/partners/customers', { method: 'POST', body: JSON.stringify(cForm) });
      showToast(r.message);
      setCForm({ ...cForm, name: '', phone: '', email: '', address: '' });
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const saveEditCust = async (e) => {
    e.preventDefault();
    if (!editCustomer) return;
    try {
      const r = await apiFetch(`/api/partners/customers/${editCustomer.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editCustomer.name,
          phone: editCustomer.phone || '',
          email: editCustomer.email || '',
          address: editCustomer.address || '',
          district: editCustomer.district || 'Quận 1',
          province: editCustomer.province || 'TP.HCM',
          customer_tier: editCustomer.customer_tier || 'Standard',
        }),
      });
      showToast(r.message);
      setEditCustomer(null);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const addSupp = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/partners/suppliers', { method: 'POST', body: JSON.stringify(sForm) });
      showToast(r.message);
      setSForm({ name: '', phone: '', email: '', address: '', products_supplied: '', debt_vnd: 0 });
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const saveEditSupp = async (e) => {
    e.preventDefault();
    if (!editSupplier) return;
    try {
      const r = await apiFetch(`/api/partners/suppliers/${editSupplier.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editSupplier.name,
          phone: editSupplier.phone || '',
          email: editSupplier.email || '',
          address: editSupplier.address || '',
          products_supplied: editSupplier.products_supplied || '',
          debt_vnd: Number(editSupplier.debt_vnd || 0),
        }),
      });
      showToast(r.message);
      setEditSupplier(null);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const handleConfirmDelete = async () => {
    if (!confirmDel) return;
    const { kind, item } = confirmDel;
    setConfirmDel(null);
    try {
      const endpoint = kind === 'customer' ? `/api/partners/customers/${item.id}` : `/api/partners/suppliers/${item.id}`;
      const r = await apiFetch(endpoint, { method: 'DELETE' });
      showToast(r.message);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  return (
    <div className="space-y-5">
      <ModalShell open={!!custOrders} title={`Lịch sử đơn hàng: ${custOrders?.customer?.name || ''}`} onClose={() => setCustOrders(null)} maxWidth="max-w-md">
        {custOrders && (
          <div className="space-y-2.5">
            {custOrders.orders.length === 0 ? <EmptyState title="Chưa có đơn hàng" subtitle="" /> : custOrders.orders.map((o) => (
              <div key={o.id} className="flex justify-between text-xs p-3 bg-sky-50/70 border border-sky-100 rounded-xl">
                <span><strong>{o.order_code}</strong> ({o.status})</span>
                <span className="font-mono font-bold text-brand-700">{fmtVnd(o.total_amount)}</span>
              </div>
            ))}
          </div>
        )}
      </ModalShell>

      <ModalShell open={!!editCustomer} title={`✏️ Sửa thông tin Khách hàng`} onClose={() => setEditCustomer(null)}>
        {editCustomer && (
          <form onSubmit={saveEditCust} className="space-y-3 text-xs">
            <input value={editCustomer.name} onChange={(e) => setEditCustomer({ ...editCustomer, name: e.target.value })} placeholder="Tên khách hàng *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" required />
            <div className="grid grid-cols-2 gap-3">
              <input value={editCustomer.phone || ''} onChange={(e) => setEditCustomer({ ...editCustomer, phone: e.target.value })} placeholder="Số điện thoại" className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
              <input value={editCustomer.email || ''} onChange={(e) => setEditCustomer({ ...editCustomer, email: e.target.value })} placeholder="Email" className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
            </div>
            <input value={editCustomer.address || ''} onChange={(e) => setEditCustomer({ ...editCustomer, address: e.target.value })} placeholder="Địa chỉ" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
            <div className="grid grid-cols-3 gap-2">
              <select value={editCustomer.district || 'Quận 1'} onChange={(e) => setEditCustomer({ ...editCustomer, district: e.target.value })} className="px-2 py-2.5 rounded-xl border border-sky-200 bg-slate-50"><option>Quận 1</option><option>Quận 3</option><option>TP. Thủ Đức</option><option>Dĩ An</option><option>Biên Hòa</option></select>
              <select value={editCustomer.province || 'TP.HCM'} onChange={(e) => setEditCustomer({ ...editCustomer, province: e.target.value })} className="px-2 py-2.5 rounded-xl border border-sky-200 bg-slate-50"><option>TP.HCM</option><option>Bình Dương</option><option>Đồng Nai</option></select>
              <select value={editCustomer.customer_tier || 'Standard'} onChange={(e) => setEditCustomer({ ...editCustomer, customer_tier: e.target.value })} className="px-2 py-2.5 rounded-xl border border-sky-200 bg-slate-50"><option>Standard</option><option>VIP</option><option>Enterprise</option></select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditCustomer(null)} className="px-4 py-2 rounded-full border border-slate-300 font-bold text-slate-600">Hủy</button>
              <button type="submit" className="px-5 py-2 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold">💾 Lưu khách hàng</button>
            </div>
          </form>
        )}
      </ModalShell>

      <ModalShell open={!!editSupplier} title={`✏️ Cập nhật Nhà cung cấp`} onClose={() => setEditSupplier(null)}>
        {editSupplier && (
          <form onSubmit={saveEditSupp} className="space-y-3 text-xs">
            <input value={editSupplier.name} onChange={(e) => setEditSupplier({ ...editSupplier, name: e.target.value })} placeholder="Tên NCC *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" required />
            <div className="grid grid-cols-2 gap-3">
              <input value={editSupplier.phone || ''} onChange={(e) => setEditSupplier({ ...editSupplier, phone: e.target.value })} placeholder="Số điện thoại" className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
              <input value={editSupplier.email || ''} onChange={(e) => setEditSupplier({ ...editSupplier, email: e.target.value })} placeholder="Email" className="px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
            </div>
            <input value={editSupplier.address || ''} onChange={(e) => setEditSupplier({ ...editSupplier, address: e.target.value })} placeholder="Địa chỉ" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
            <input value={editSupplier.products_supplied || ''} onChange={(e) => setEditSupplier({ ...editSupplier, products_supplied: e.target.value })} placeholder="Mặt hàng cung ứng" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
            <div>
              <label className="font-bold text-slate-600 block mb-1">Công nợ (VNĐ)</label>
              <input type="number" step="50000" value={editSupplier.debt_vnd ?? 0} onChange={(e) => setEditSupplier({ ...editSupplier, debt_vnd: Number(e.target.value) })} className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50 font-mono" />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditSupplier(null)} className="px-4 py-2 rounded-full border border-slate-300 font-bold text-slate-600">Hủy</button>
              <button type="submit" className="px-5 py-2 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold">💾 Lưu NCC</button>
            </div>
          </form>
        )}
      </ModalShell>

      <ConfirmModal
        open={!!confirmDel}
        title="Xác nhận xóa đối tác"
        message={`Bạn có chắc muốn xóa ${confirmDel?.kind === 'customer' ? 'khách hàng' : 'nhà cung cấp'} "${confirmDel?.item?.name}"?`}
        confirmText="Xác nhận xóa"
        onCancel={() => setConfirmDel(null)}
        onConfirm={handleConfirmDelete}
      />

      <div className="flex flex-wrap justify-between gap-3 border-b border-sky-100 pb-3">
        <div className="flex gap-2">
          <button onClick={() => setTab('customers')} className={`px-4 py-2 rounded-full text-xs font-bold transition ${tab === 'customers' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-text-sub hover:bg-sky-50'}`}>👥 Khách hàng ({data.customers.length})</button>
          <button onClick={() => setTab('suppliers')} className={`px-4 py-2 rounded-full text-xs font-bold transition ${tab === 'suppliers' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-text-sub hover:bg-sky-50'}`}>🏭 Nhà cung cấp ({data.suppliers.length})</button>
        </div>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm tên đối tác..." className="text-xs px-4 py-2 rounded-full border border-sky-200 bg-white focus:outline-none focus:border-brand-500" />
      </div>

      {tab === 'customers' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-8 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">Đại lý</th><th className="p-2.5">Khu vực</th><th className="p-2.5">Hạng</th><th className="p-2.5">Đơn</th><th className="p-2.5">Tổng chi</th><th className="p-2.5 text-right">Thao tác</th></tr></thead>
              <tbody>
                {data.customers.map((c) => (
                  <tr key={c.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30 transition">
                    <td className="p-2.5 font-bold">{c.name}<div className="text-[10px] font-normal text-slate-400">{c.phone}</div></td>
                    <td className="p-2.5">{c.district}, {c.province}</td>
                    <td className="p-2.5"><span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${c.customer_tier === 'VIP' ? 'bg-amber-100 text-amber-800' : 'bg-sky-50 text-slate-700'}`}>{c.customer_tier}</span></td>
                    <td className="p-2.5 font-mono">{c.order_count}</td>
                    <td className="p-2.5 font-mono">{fmtVnd(c.lifetime_value)}</td>
                    <td className="p-2.5 text-right space-x-2 whitespace-nowrap">
                      <button onClick={() => viewHist(c)} className="text-blue-600 font-bold hover:underline">Đơn</button>
                      <button onClick={() => setEditCustomer({ ...c })} className="text-brand-600 font-bold hover:underline">Sửa</button>
                      <button onClick={() => setConfirmDel({ kind: 'customer', item: c })} className="text-red-500 font-bold hover:underline">Xóa</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form onSubmit={addCust} className="lg:col-span-4 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-2.5 text-xs h-fit">
            <h4 className="font-extrabold text-sm m-0">➕ Thêm Khách Hàng</h4>
            <input value={cForm.name} onChange={(e) => setCForm({ ...cForm, name: e.target.value })} placeholder="Tên khách hàng *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" required />
            <div className="grid grid-cols-2 gap-2">
              <input value={cForm.phone} onChange={(e) => setCForm({ ...cForm, phone: e.target.value })} placeholder="Số điện thoại" className="px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
              <input value={cForm.email} onChange={(e) => setCForm({ ...cForm, email: e.target.value })} placeholder="Email" className="px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
            </div>
            <input value={cForm.address} onChange={(e) => setCForm({ ...cForm, address: e.target.value })} placeholder="Địa chỉ" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
            <div className="grid grid-cols-3 gap-2">
              <select value={cForm.district} onChange={(e) => setCForm({ ...cForm, district: e.target.value })} className="px-2 py-2 rounded-xl border border-sky-200 bg-slate-50/70"><option>Quận 1</option><option>Quận 3</option><option>TP. Thủ Đức</option><option>Dĩ An</option><option>Biên Hòa</option></select>
              <select value={cForm.province} onChange={(e) => setCForm({ ...cForm, province: e.target.value })} className="px-2 py-2 rounded-xl border border-sky-200 bg-slate-50/70"><option>TP.HCM</option><option>Bình Dương</option><option>Đồng Nai</option></select>
              <select value={cForm.customer_tier} onChange={(e) => setCForm({ ...cForm, customer_tier: e.target.value })} className="px-2 py-2 rounded-xl border border-sky-200 bg-slate-50/70"><option>Standard</option><option>VIP</option><option>Enterprise</option></select>
            </div>
            <button type="submit" className="w-full py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold shadow-md shadow-brand-500/20">Lưu Khách Hàng</button>
          </form>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-8 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">Nhà cung cấp</th><th className="p-2.5">Sản phẩm</th><th className="p-2.5">Công nợ</th><th className="p-2.5 text-right">Thao tác</th></tr></thead>
              <tbody>
                {data.suppliers.map((s) => (
                  <tr key={s.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30 transition">
                    <td className="p-2.5"><strong>{s.name}</strong><div className="text-[10px] text-text-sub">{s.address}</div></td>
                    <td className="p-2.5">{s.products_supplied}</td>
                    <td className="p-2.5 font-mono font-bold text-red-600">{fmtVnd(s.debt_vnd)}</td>
                    <td className="p-2.5 text-right space-x-2 whitespace-nowrap">
                      <button onClick={() => setEditSupplier({ ...s })} className="text-brand-600 font-bold hover:underline">Sửa</button>
                      <button onClick={() => setConfirmDel({ kind: 'supplier', item: s })} className="text-red-500 font-bold hover:underline">Xóa</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form onSubmit={addSupp} className="lg:col-span-4 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-2.5 text-xs h-fit">
            <h4 className="font-extrabold text-sm m-0">➕ Thêm Nhà Cung Cấp</h4>
            <input value={sForm.name} onChange={(e) => setSForm({ ...sForm, name: e.target.value })} placeholder="Tên NCC *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" required />
            <div className="grid grid-cols-2 gap-2">
              <input value={sForm.phone} onChange={(e) => setSForm({ ...sForm, phone: e.target.value })} placeholder="Điện thoại" className="px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
              <input value={sForm.email} onChange={(e) => setSForm({ ...sForm, email: e.target.value })} placeholder="Email" className="px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
            </div>
            <input value={sForm.address} onChange={(e) => setSForm({ ...sForm, address: e.target.value })} placeholder="Địa chỉ" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
            <input value={sForm.products_supplied} onChange={(e) => setSForm({ ...sForm, products_supplied: e.target.value })} placeholder="Mặt hàng cung ứng" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
            <input type="number" value={sForm.debt_vnd} onChange={(e) => setSForm({ ...sForm, debt_vnd: Number(e.target.value) })} placeholder="Công nợ (VNĐ)" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
            <button type="submit" className="w-full py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold shadow-md shadow-brand-500/20">Lưu NCC</button>
          </form>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { PartnersView });
