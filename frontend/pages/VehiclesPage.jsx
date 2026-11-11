const { useState, useEffect, useRef, useMemo } = React;

// ==================== 9. VEHICLES VIEW (MODULE 09) ====================
function VehiclesView({ showToast }) {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editVeh, setEditVeh] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null);
  const [form, setForm] = useState({ plate_number: '', vehicle_name: '', vehicle_type: 'Tải nhẹ đô thị', max_load_kg: 2500, fuel_type: 'Diesel', fuel_consumption_per_100km: 13.5, operational_cost_per_km: 4000 });

  const load = () => {
    setLoading(true);
    apiFetch('/api/vehicles')
      .then((d) => setVehicles(d.vehicles || []))
      .catch((e) => showToast(e.message, 'error'))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const addVeh = async (e) => {
    e.preventDefault();
    try {
      const r = await apiFetch('/api/vehicles', { method: 'POST', body: JSON.stringify(form) });
      showToast(r.message);
      setForm({ ...form, plate_number: '', vehicle_name: '' });
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    if (!editVeh) return;
    try {
      const r = await apiFetch(`/api/vehicles/${editVeh.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          plate_number: editVeh.plate_number || '',
          vehicle_name: editVeh.vehicle_name,
          vehicle_type: editVeh.vehicle_type,
          max_load_kg: Number(editVeh.max_load_kg),
          fuel_type: editVeh.fuel_type,
          fuel_consumption_per_100km: Number(editVeh.fuel_consumption_per_100km),
          operational_cost_per_km: Number(editVeh.operational_cost_per_km),
          status: editVeh.status,
        }),
      });
      showToast(r.message);
      setEditVeh(null);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const updateStatus = async (v, newStatus) => {
    try {
      const r = await apiFetch(`/api/vehicles/${v.id}`, { method: 'PUT', body: JSON.stringify({ ...v, status: newStatus }) });
      showToast(r.message);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const delVeh = async (id) => {
    try {
      const r = await apiFetch(`/api/vehicles/${id}`, { method: 'DELETE' });
      showToast(r.message);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8 space-y-3">
          {loading ? (
            <LoadingSkeleton rows={3} />
          ) : vehicles.length === 0 ? (
            <EmptyState title="Chưa có phương tiện nào" />
          ) : (
            vehicles.map((v) => (
              <div key={v.id} className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm flex flex-wrap justify-between items-center gap-4">
                <div>
                  <div className="font-extrabold text-sm text-text-main">
                    {v.vehicle_name}
                    <span className="font-mono text-xs bg-sky-50 border border-sky-100 px-2 py-0.5 rounded ml-1.5">{v.plate_number}</span>
                    {v.fuel_type === 'Electric' && <span className="ml-1.5 text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-brand-700 font-bold">⚡ EV Xanh</span>}
                  </div>
                  <div className="text-xs text-text-sub mt-1">{v.vehicle_type} • Tải: <strong>{v.max_load_kg} kg</strong> • {v.fuel_type} ({v.fuel_consumption_per_100km} L/100km)</div>
                  <div className="text-xs text-brand-700 font-semibold mt-1">Số chuyến: {v.total_routes} • Tổng km: {v.total_distance_km} km • CO₂: {v.total_co2_kg} kg</div>
                </div>
                <div className="flex items-center gap-2.5">
                  <select value={v.status} onChange={(e) => updateStatus(v, e.target.value)} className="text-xs px-3 py-1.5 rounded-xl border border-sky-200 bg-slate-50 font-bold">
                    <option value="Available">Available</option><option value="In Transit">In Transit</option><option value="Maintenance">Maintenance</option>
                  </select>
                  <button onClick={() => setEditVeh({ ...v })} className="text-xs text-brand-600 font-bold px-2 hover:underline">Sửa</button>
                  <button onClick={() => setConfirmDel(v)} className="text-xs text-red-500 font-bold px-2 hover:underline">Xóa</button>
                </div>
              </div>
            ))
          )}
        </div>
        <form onSubmit={addVeh} className="lg:col-span-4 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs h-fit">
          <h4 className="font-extrabold text-sm m-0">➕ Thêm Phương Tiện Mới</h4>
          <input value={form.plate_number} onChange={(e) => setForm({ ...form, plate_number: e.target.value })} placeholder="Biển số (VD: 51D-998.12) *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
          <input value={form.vehicle_name} onChange={(e) => setForm({ ...form, vehicle_name: e.target.value })} placeholder="Tên xe *" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500" required />
          <input value={form.vehicle_type} onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })} placeholder="Loại xe" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input type="number" value={form.max_load_kg} onChange={(e) => setForm({ ...form, max_load_kg: Number(e.target.value) })} placeholder="Tải trọng (kg)" className="px-3 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70" />
            <select value={form.fuel_type} onChange={(e) => setForm({ ...form, fuel_type: e.target.value })} className="px-3 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70"><option>Diesel</option><option>Xăng E5</option><option>Electric</option></select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input type="number" step="0.5" value={form.fuel_consumption_per_100km} onChange={(e) => setForm({ ...form, fuel_consumption_per_100km: Number(e.target.value) })} placeholder="L/100km" className="px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
            <input type="number" step="500" value={form.operational_cost_per_km} onChange={(e) => setForm({ ...form, operational_cost_per_km: Number(e.target.value) })} placeholder="VNĐ/km" className="px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70" />
          </div>
          <button type="submit" className="w-full py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold shadow-md shadow-brand-500/20">Lưu phương tiện</button>
        </form>
      </div>

      <ModalShell open={!!editVeh} title={`✏️ Cập nhật phương tiện ${editVeh?.plate_number || ''}`} onClose={() => setEditVeh(null)}>
        {editVeh && (
          <form onSubmit={saveEdit} className="space-y-3 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-slate-600 block mb-1">Tên phương tiện *</label>
                <input value={editVeh.vehicle_name} onChange={(e) => setEditVeh({ ...editVeh, vehicle_name: e.target.value })} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50" required />
              </div>
              <div>
                <label className="font-bold text-slate-600 block mb-1">Loại xe</label>
                <input value={editVeh.vehicle_type} onChange={(e) => setEditVeh({ ...editVeh, vehicle_type: e.target.value })} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-slate-600 block mb-1">Tải trọng tối đa (kg)</label>
                <input type="number" value={editVeh.max_load_kg} onChange={(e) => setEditVeh({ ...editVeh, max_load_kg: Number(e.target.value) })} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50" required />
              </div>
              <div>
                <label className="font-bold text-slate-600 block mb-1">Nhiên liệu</label>
                <select value={editVeh.fuel_type} onChange={(e) => setEditVeh({ ...editVeh, fuel_type: e.target.value })} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50">
                  <option>Diesel</option><option>Xăng E5</option><option>Electric</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-slate-600 block mb-1">Định mức (L/100km)</label>
                <input type="number" step="0.5" value={editVeh.fuel_consumption_per_100km} onChange={(e) => setEditVeh({ ...editVeh, fuel_consumption_per_100km: Number(e.target.value) })} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
              <div>
                <label className="font-bold text-slate-600 block mb-1">Chi phí vận hành (VNĐ/km)</label>
                <input type="number" step="500" value={editVeh.operational_cost_per_km} onChange={(e) => setEditVeh({ ...editVeh, operational_cost_per_km: Number(e.target.value) })} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50" />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditVeh(null)} className="px-4 py-2 rounded-full border border-slate-300 font-bold text-slate-600">Hủy</button>
              <button type="submit" className="px-5 py-2 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold">💾 Lưu thay đổi</button>
            </div>
          </form>
        )}
      </ModalShell>

      <ConfirmModal
        open={!!confirmDel}
        title="Xác nhận xóa phương tiện"
        message={`Bạn có chắc muốn xóa phương tiện "${confirmDel?.vehicle_name} (${confirmDel?.plate_number})"?`}
        confirmText="Xóa xe"
        onCancel={() => setConfirmDel(null)}
        onConfirm={async () => {
          const id = confirmDel.id;
          setConfirmDel(null);
          await delVeh(id);
        }}
      />
    </>
  );
}

Object.assign(window, { VehiclesView });
