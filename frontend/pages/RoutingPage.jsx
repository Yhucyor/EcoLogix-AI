const { useState, useEffect, useRef, useMemo } = React;

// ==================== 8. ROUTING VIEW (REAL CVRPTW + 100 POINTS) ====================
function RoutingView({ showToast, onRefreshHeader }) {
  const [subTab, setSubTab] = useState('orders'); // 'orders' | 'compare' | 'schedule' | '100points'
  const [initData, setInitData] = useState(null);
  const [selectedOrderIds, setSelectedOrderIds] = useState([]);
  const [vehicleId, setVehicleId] = useState(null);
  const [enforceTw, setEnforceTw] = useState(true);
  const [routeResult, setRouteResult] = useState(null);
  const [points100, setPoints100] = useState(null);
  const [scopeCount, setScopeCount] = useState(100);

  useEffect(() => {
    apiFetch('/api/routing').then((d) => {
      setInitData(d);
      setSelectedOrderIds((d.pending_orders || []).slice(0, 6).map((o) => o.id));
      if (d.vehicles?.length) setVehicleId(d.vehicles[0].id);
      if (d.preview) setRouteResult(d.preview);
    }).catch((e) => showToast(e.message, 'error'));
  }, []);

  const runOptimize = async (save = true) => {
    try {
      const r = await apiFetch('/api/routing/optimize', {
        method: 'POST',
        body: JSON.stringify({ mode: 'orders', order_ids: selectedOrderIds, vehicle_id: vehicleId, enforce_time_window: enforceTw, save_to_db: save })
      });
      setRouteResult(r.result);
      if (r.saved_routes) setInitData((p) => ({ ...p, saved_routes: r.saved_routes }));
      showToast(`Tối ưu tuyến ${r.result.route_code}: ${r.result.total_distance_km} km (Giảm ${r.result.saved_pct}%)!`);
      onRefreshHeader();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const run100Points = async (cnt) => {
    try {
      setScopeCount(cnt);
      const r = await apiFetch('/api/routing/optimize', {
        method: 'POST',
        body: JSON.stringify({ mode: '100points', scope_count: cnt, enforce_time_window: enforceTw })
      });
      setPoints100(r.result);
    } catch (err) { showToast(err.message, 'error'); }
  };

  useEffect(() => {
    if (subTab === '100points' && !points100) run100Points(scopeCount);
  }, [subTab]);

  const activeMapProps = useMemo(() => {
    const active = subTab === '100points' ? points100 : routeResult;
    const depot = active?.depot || { lat: 10.8505, lng: 106.7718, name: 'Kho Tổng EcoLogix (TP. Thủ Đức)' };
    if (subTab === '100points' && active?.routes) {
      const vCol = { 'XE-01': '#10B981', 'XE-02': '#3B82F6', 'XE-03': '#8B5CF6' };
      return {
        depot,
        routes: Object.entries(active.routes).map(([vId, pts]) => ({
          color: vCol[vId] || '#059669',
          stops: pts.map((p, idx) => ({
            lat: p.lat, lng: p.lng, label: p.name,
            popup: `<b>${vId} • #${idx + 1} ${p.name}</b><br/>${p.district}, ${p.province} (${p.demand_kg}kg)`
          })),
        })),
      };
    }
    return {
      depot,
      routes: active?.ordered_stops ? [{
        color: '#0284C7',
        stops: active.ordered_stops.map((s, idx) => ({
          lat: s.lat, lng: s.lng, label: s.customer_name,
          popup: `<b>#${idx + 1} ${s.customer_name}</b><br/>Đơn ${s.order_code} • Dự kiến ${s.arrival_time}`
        })),
      }] : [],
    };
  }, [subTab, points100, routeResult]);

  if (!initData) return <div className="p-8 text-xs text-text-sub">⏳ Đang tải bản đồ & đơn hàng...</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 border-b border-border-light pb-2">
        {[
          { id: 'orders', label: '● Điều phối đơn hàng thực tế' },
          { id: 'compare', label: 'So sánh Trước & Sau + Lịch sử' },
          { id: 'schedule', label: 'Lịch trình điểm dừng chi tiết' },
          { id: '100points', label: '🌐 Thực nghiệm 100 điểm TP.HCM - Đồng Nai' }
        ].map((t) => (
          <button key={t.id} onClick={() => setSubTab(t.id)} className={`px-4 py-2 rounded-xl text-xs font-bold ${subTab === t.id ? 'bg-brand-600 text-white' : 'text-text-sub hover:bg-canvas'}`}>{t.label}</button>
        ))}
      </div>

      {(subTab === 'orders' || subTab === '100points') && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-4 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-4 text-xs">
            {subTab === 'orders' ? (
              <>
                <h4 className="font-extrabold text-sm m-0">Chọn đơn hàng & Phương tiện</h4>
                <div className="max-h-48 overflow-y-auto space-y-1.5 border border-sky-100 rounded-2xl p-2.5 bg-slate-50/70">
                  {initData.pending_orders.map((o) => {
                    const checked = selectedOrderIds.includes(o.id);
                    return (
                      <label key={o.id} className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white cursor-pointer">
                        <input type="checkbox" checked={checked} onChange={() => setSelectedOrderIds(checked ? selectedOrderIds.filter((x) => x !== o.id) : [...selectedOrderIds, o.id])} className="text-brand-600" />
                        <span><strong>{o.order_code}</strong> • {o.district} ({o.total_weight_kg}kg)</span>
                      </label>
                    );
                  })}
                </div>
                <div>
                  <label className="font-bold text-text-sub block mb-1">Phương tiện vận tải:</label>
                  <select value={vehicleId || ''} onChange={(e) => setVehicleId(Number(e.target.value))} className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50/70 font-semibold">
                    {initData.vehicles.map((v) => <option key={v.id} value={v.id}>{v.vehicle_name} ({v.max_load_kg}kg - {v.fuel_type})</option>)}
                  </select>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={enforceTw} onChange={(e) => setEnforceTw(e.target.checked)} className="text-brand-600" />
                  <span>Né giờ cấm tải ({initData.config.restricted_time_window.join('–')})</span>
                </label>
                <button onClick={() => runOptimize(true)} className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-lg text-white py-3 rounded-full font-extrabold shadow-md shadow-brand-500/20 transition">🚀 Tối ưu & Lưu tuyến vào DB</button>
                {routeResult && (
                  <div className="pt-3 border-t border-sky-100 space-y-1">
                    {routeResult.overload_warning && <div className="text-amber-700 font-bold">⚠️ Vượt tải trọng tối đa xe ({routeResult.max_capacity_kg}kg)!</div>}
                    <div className="flex justify-between"><span>Quãng đường:</span><strong>{routeResult.total_distance_km} km (-{routeResult.saved_pct}%)</strong></div>
                    <div className="flex justify-between"><span>Giảm CO₂:</span><strong className="text-brand-600">🌱 {routeResult.saved_co2_kg} kg</strong></div>
                    <div className="flex justify-between"><span>Chi phí dự kiến:</span><strong>{fmtVnd(routeResult.total_cost_vnd)}</strong></div>
                  </div>
                )}
              </>
            ) : (
              <>
                <h4 className="font-extrabold text-sm m-0">Bộ dữ liệu 100 điểm thực nghiệm</h4>
                <div className="flex gap-2">
                  {[25, 50, 100].map((c) => (
                    <button key={c} onClick={() => run100Points(c)} className={`flex-1 py-2 rounded-full font-bold transition ${scopeCount === c ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'bg-sky-50 text-text-sub hover:bg-sky-100'}`}>{c} điểm</button>
                  ))}
                </div>
                {points100 && (
                  <div className="space-y-2 pt-3 border-t border-sky-100">
                    <div className="flex justify-between"><span>Tổng quãng đường 3 xe:</span><strong>{points100.total_distance_km} km (-{points100.saved_pct}%)</strong></div>
                    <div className="flex justify-between"><span>CO₂ cắt giảm:</span><strong className="text-brand-600">{points100.saved_co2_kg} kg</strong></div>
                    <div className="flex justify-between"><span>Tiết kiệm tiền:</span><strong className="text-brand-600">{fmtVnd(points100.saved_money_vnd)}</strong></div>
                    <div className="flex justify-between"><span>Tổng tải trọng:</span><strong>{points100.total_load_kg.toLocaleString()} kg</strong></div>
                  </div>
                )}
              </>
            )}
          </div>
          <div className="lg:col-span-8 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-bold text-text-sub">Bản đồ tuyến đường tối ưu CVRPTW 2-Opt</span>
              <span className="bg-emerald-50 text-brand-700 border border-emerald-200 font-extrabold text-xs px-3 py-1 rounded-full">
                {subTab === '100points' && points100 ? `${points100.total_distance_km} km (-${points100.saved_pct}%)` : routeResult ? `${routeResult.total_distance_km} km (-${routeResult.saved_pct}%)` : ''}
              </span>
            </div>
            <EcoLeafletMap
              depot={activeMapProps.depot}
              routes={activeMapProps.routes}
              showRestrictedZone={enforceTw}
              heightClass="h-[410px]"
              defaultTheme="osm"
              openDepotPopup={true}
            />
          </div>
        </div>
      )}

      {subTab === 'compare' && routeResult && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Quãng đường AI vs Cũ</div><div className="font-mono text-xl font-extrabold text-brand-600">{routeResult.total_distance_km} km</div><div className="text-[11px] text-text-sub">Truyền thống: {routeResult.baseline_distance_km} km</div></div>
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Nhiên liệu tiêu thụ</div><div className="font-mono text-xl font-extrabold">{routeResult.fuel_needed_liters} L</div><div className="text-[11px] text-brand-600">Tiết kiệm {routeResult.saved_fuel_liters} L</div></div>
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Phát thải CO₂</div><div className="font-mono text-xl font-extrabold">{routeResult.co2_emission_kg} kg</div><div className="text-[11px] text-brand-600">Giảm {routeResult.saved_co2_kg} kg</div></div>
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Chi phí vận chuyển</div><div className="font-mono text-xl font-extrabold">{fmtVnd(routeResult.total_cost_vnd)}</div><div className="text-[11px] text-brand-600">Tiết kiệm {fmtVnd(routeResult.saved_money_vnd)}</div></div>
          </div>
          <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
            <h4 className="font-extrabold text-sm mb-3 m-0">Lịch sử tuyến đã lưu (`routes`)</h4>
            <table className="w-full text-xs text-left">
              <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">Mã tuyến</th><th className="p-2.5">Xe</th><th className="p-2.5">Quãng đường</th><th className="p-2.5">Giảm CO₂</th><th className="p-2.5">Chi phí</th></tr></thead>
              <tbody>
                {initData.saved_routes.map((r) => (
                  <tr key={r.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30">
                    <td className="p-2.5 font-mono font-bold text-brand-700">{r.route_code}</td>
                    <td className="p-2.5">{r.vehicle_name}</td>
                    <td className="p-2.5 font-mono">{r.total_distance_km} km</td>
                    <td className="p-2.5 font-mono text-brand-600">{r.saved_co2_kg} kg</td>
                    <td className="p-2.5 font-mono">{fmtVnd(r.total_cost_vnd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {subTab === 'schedule' && routeResult && (
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">STT</th><th className="p-2.5">Mã đơn</th><th className="p-2.5">Khách hàng</th><th className="p-2.5">Khu vực</th><th className="p-2.5">Giờ đến</th><th className="p-2.5">Giờ rời</th><th className="p-2.5">KL</th></tr></thead>
            <tbody>
              {routeResult.ordered_stops.map((s) => (
                <tr key={s.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30">
                  <td className="p-2.5 font-bold">#{s.stop_sequence}</td>
                  <td className="p-2.5 font-mono font-bold">{s.order_code}</td>
                  <td className="p-2.5">{s.customer_name}</td>
                  <td className="p-2.5">{s.district}, {s.province}</td>
                  <td className="p-2.5 font-mono text-brand-600 font-bold">{s.arrival_time}</td>
                  <td className="p-2.5 font-mono">{s.departure_time}</td>
                  <td className="p-2.5 font-mono">{s.total_weight_kg} kg</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { RoutingView });
