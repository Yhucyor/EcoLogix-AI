const { useState, useEffect, useRef, useMemo } = React;

// ==================== 10 & 11. PARTNERS VIEW (CUSTOMERS & SUPPLIERS) ====================
function PartnersView({ showToast }) {
  const [tab, setTab] = useState('customers');
  const [data, setData] = useState({ customers: [], suppliers: [] });
  const [search, setSearch] = useState('');
  const [custOrders, setCustOrders] = useState(null);
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
      setCForm({ ...cForm, name: '', phone: '', address: '' });
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

  const updateDebt = async (id, current) => {
    const val = prompt('Nhập công nợ mới (VNĐ):', current);
    if (val === null) return;
    const r = await apiFetch(`/api/partners/suppliers/${id}/debt`, { method: 'PATCH', body: JSON.stringify({ debt_vnd: Number(val) }) });
    showToast(r.message);
    load();
  };

  return (
    <div className="space-y-5">
      {custOrders && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-3">
            <div className="flex justify-between"><strong className="text-sm">Lịch sử đơn: {custOrders.customer.name}</strong><button onClick={() => setCustOrders(null)}>✕</button></div>
            {custOrders.orders.length === 0 ? <EmptyState title="Chưa có đơn hàng" subtitle="" /> : custOrders.orders.map((o) => (
              <div key={o.id} className="flex justify-between text-xs p-2 bg-canvas rounded-lg"><span><strong>{o.order_code}</strong> ({o.status})</span><span className="font-mono font-bold">{fmtVnd(o.total_amount)}</span></div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap justify-between gap-3 border-b border-border-light pb-2">
        <div className="flex gap-2">
          <button onClick={() => setTab('customers')} className={`px-4 py-2 rounded-xl text-xs font-bold ${tab === 'customers' ? 'bg-brand-600 text-white' : 'text-text-sub'}`}>👥 Khách hàng ({data.customers.length})</button>
          <button onClick={() => setTab('suppliers')} className={`px-4 py-2 rounded-xl text-xs font-bold ${tab === 'suppliers' ? 'bg-brand-600 text-white' : 'text-text-sub'}`}>🏭 Nhà cung cấp ({data.suppliers.length})</button>
        </div>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm tên đối tác..." className="text-xs px-3 py-1.5 rounded-xl border border-border-light bg-white" />
      </div>

      {tab === 'customers' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-8 bg-white p-5 rounded-2xl border border-border-light overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-canvas text-text-sub"><tr><th className="p-2.5">Đại lý</th><th className="p-2.5">Khu vực</th><th className="p-2.5">Hạng</th><th className="p-2.5">Đơn</th><th className="p-2.5">Tổng chi</th><th className="p-2.5">Lịch sử</th></tr></thead>
              <tbody>
                {data.customers.map((c) => (
                  <tr key={c.id} className="border-t border-border-light">
                    <td className="p-2.5 font-bold">{c.name}</td>
                    <td className="p-2.5">{c.district}, {c.province}</td>
                    <td className="p-2.5"><span className={`px-2 py-0.5 rounded text-[10px] font-bold ${c.customer_tier === 'VIP' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100'}`}>{c.customer_tier}</span></td>
                    <td className="p-2.5 font-mono">{c.order_count}</td>
                    <td className="p-2.5 font-mono">{fmtVnd(c.lifetime_value)}</td>
                    <td className="p-2.5"><button onClick={() => viewHist(c)} className="text-brand-600 font-bold hover:underline">Xem đơn</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form onSubmit={addCust} className="lg:col-span-4 bg-white p-5 rounded-2xl border border-border-light space-y-2.5 text-xs h-fit">
            <h4 className="font-extrabold text-sm m-0">➕ Thêm Khách Hàng</h4>
            <input value={cForm.name} onChange={(e) => setCForm({ ...cForm, name: e.target.value })} placeholder="Tên khách hàng *" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" required />
            <input value={cForm.phone} onChange={(e) => setCForm({ ...cForm, phone: e.target.value })} placeholder="Số điện thoại" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" />
            <input value={cForm.address} onChange={(e) => setCForm({ ...cForm, address: e.target.value })} placeholder="Địa chỉ" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" />
            <div className="grid grid-cols-2 gap-2">
              <select value={cForm.district} onChange={(e) => setCForm({ ...cForm, district: e.target.value })} className="px-2 py-2 rounded-xl border border-border-light bg-canvas"><option>Quận 1</option><option>Quận 3</option><option>TP. Thủ Đức</option><option>Dĩ An</option><option>Biên Hòa</option></select>
              <select value={cForm.province} onChange={(e) => setCForm({ ...cForm, province: e.target.value })} className="px-2 py-2 rounded-xl border border-border-light bg-canvas"><option>TP.HCM</option><option>Bình Dương</option><option>Đồng Nai</option></select>
            </div>
            <button type="submit" className="w-full py-2.5 rounded-xl bg-brand-600 text-white font-bold">Lưu Khách Hàng</button>
          </form>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-8 bg-white p-5 rounded-2xl border border-border-light overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-canvas text-text-sub"><tr><th className="p-2.5">Nhà cung cấp</th><th className="p-2.5">Sản phẩm</th><th className="p-2.5">Công nợ</th><th className="p-2.5">Sửa nợ</th></tr></thead>
              <tbody>
                {data.suppliers.map((s) => (
                  <tr key={s.id} className="border-t border-border-light">
                    <td className="p-2.5"><strong>{s.name}</strong><div className="text-[10px] text-text-sub">{s.address}</div></td>
                    <td className="p-2.5">{s.products_supplied}</td>
                    <td className="p-2.5 font-mono font-bold text-red-600">{fmtVnd(s.debt_vnd)}</td>
                    <td className="p-2.5"><button onClick={() => updateDebt(s.id, s.debt_vnd)} className="text-brand-600 font-bold hover:underline">Cập nhật</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <form onSubmit={addSupp} className="lg:col-span-4 bg-white p-5 rounded-2xl border border-border-light space-y-2.5 text-xs h-fit">
            <h4 className="font-extrabold text-sm m-0">➕ Thêm Nhà Cung Cấp</h4>
            <input value={sForm.name} onChange={(e) => setSForm({ ...sForm, name: e.target.value })} placeholder="Tên NCC *" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" required />
            <input value={sForm.products_supplied} onChange={(e) => setSForm({ ...sForm, products_supplied: e.target.value })} placeholder="Mặt hàng cung ứng" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" />
            <input type="number" value={sForm.debt_vnd} onChange={(e) => setSForm({ ...sForm, debt_vnd: Number(e.target.value) })} placeholder="Công nợ (VNĐ)" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" />
            <button type="submit" className="w-full py-2.5 rounded-xl bg-brand-600 text-white font-bold">Lưu NCC</button>
          </form>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { PartnersView });
