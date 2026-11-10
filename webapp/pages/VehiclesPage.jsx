const { useState, useEffect, useRef, useMemo } = React;

// ==================== 9. VEHICLES VIEW (MODULE 09) ====================
function VehiclesView({ showToast }) {
  const [vehicles, setVehicles] = useState([]);
  const [form, setForm] = useState({ plate_number: '', vehicle_name: '', vehicle_type: 'Tải nhẹ đô thị', max_load_kg: 2500, fuel_type: 'Diesel', fuel_consumption_per_100km: 13.5, operational_cost_per_km: 4000 });

  const load = () => apiFetch('/api/vehicles').then((d) => setVehicles(d.vehicles || [])).catch((e) => showToast(e.message, 'error'));
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
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <div className="lg:col-span-8 space-y-3">
        {vehicles.map((v) => (
          <div key={v.id} className="bg-white p-5 rounded-2xl border border-border-light shadow-sm flex flex-wrap justify-between items-center gap-4">
            <div>
              <div className="font-extrabold text-sm text-text-main">{v.vehicle_name} <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded ml-1">{v.plate_number}</span></div>
              <div className="text-xs text-text-sub mt-1">{v.vehicle_type} • Tải: <strong>{v.max_load_kg} kg</strong> • {v.fuel_type} ({v.fuel_consumption_per_100km} L/100km)</div>
              <div className="text-xs text-brand-700 font-semibold mt-1">Số chuyến: {v.total_routes} • Tổng km: {v.total_distance_km} km • CO₂: {v.total_co2_kg} kg</div>
            </div>
            <div className="flex items-center gap-2">
              <select value={v.status} onChange={(e) => updateStatus(v, e.target.value)} className="text-xs px-2.5 py-1.5 rounded-xl border border-border-light bg-canvas font-bold">
                <option value="Available">Available</option><option value="In Transit">In Transit</option><option value="Maintenance">Maintenance</option>
              </select>
              <button onClick={() => delVeh(v.id)} className="text-xs text-red-500 font-bold px-2">Xóa</button>
            </div>
          </div>
        ))}
      </div>
      <form onSubmit={addVeh} className="lg:col-span-4 bg-white p-5 rounded-2xl border border-border-light shadow-sm space-y-3 text-xs h-fit">
        <h4 className="font-extrabold text-sm m-0">➕ Thêm Phương Tiện Mới</h4>
        <input value={form.plate_number} onChange={(e) => setForm({ ...form, plate_number: e.target.value })} placeholder="Biển số (VD: 51D-998.12) *" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" required />
        <input value={form.vehicle_name} onChange={(e) => setForm({ ...form, vehicle_name: e.target.value })} placeholder="Tên xe *" className="w-full px-3 py-2 rounded-xl border border-border-light bg-canvas" required />
        <div className="grid grid-cols-2 gap-2">
          <input type="number" value={form.max_load_kg} onChange={(e) => setForm({ ...form, max_load_kg: Number(e.target.value) })} placeholder="Tải trọng (kg)" className="px-3 py-2 rounded-xl border border-border-light bg-canvas" />
          <select value={form.fuel_type} onChange={(e) => setForm({ ...form, fuel_type: e.target.value })} className="px-3 py-2 rounded-xl border border-border-light bg-canvas"><option>Diesel</option><option>Xăng E5</option><option>Electric</option></select>
        </div>
        <button type="submit" className="w-full py-2.5 rounded-xl bg-brand-600 text-white font-bold">Lưu phương tiện</button>
      </form>
    </div>
  );
}

Object.assign(window, { VehiclesView });
