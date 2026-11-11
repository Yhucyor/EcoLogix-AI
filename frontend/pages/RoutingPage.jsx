const { useState, useEffect, useMemo } = React;

// ==================== 8. ROUTING VIEW (GREEN VRPTW: SA + CLARKE-WRIGHT + 2-OPT/OR-OPT) ====================
const ROUTING_ALGORITHMS = [
  { id: 'auto', label: 'Auto Ensemble (Best-of-3: SA + Clarke-Wright + Or-Opt)' },
  { id: 'simulated_annealing', label: 'Simulated Annealing (SA-GVRPTW)' },
  { id: 'clarke_wright', label: 'Clarke-Wright Savings (CVRP)' },
  { id: 'nn_or_opt', label: 'TW Nearest Neighbor + 2-Opt & Or-Opt' },
];

function RoutingView({ showToast, onRefreshHeader }) {
  const [subTab, setSubTab] = useState('orders'); // 'orders' | 'compare' | 'schedule' | '100points'
  const [initData, setInitData] = useState(null);
  const [selectedOrderIds, setSelectedOrderIds] = useState([]);
  const [vehicleId, setVehicleId] = useState(null);
  const [enforceTw, setEnforceTw] = useState(true);
  const [algorithm, setAlgorithm] = useState('auto');
  const [multiVehicle, setMultiVehicle] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
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

  const runOptimize = async (save = true, overrideOpts = {}) => {
    if (!selectedOrderIds.length) {
      showToast('Vui lòng chọn ít nhất 1 đơn hàng để tối ưu!', 'error');
      return;
    }
    const useAlgo = overrideOpts.algorithm !== undefined ? overrideOpts.algorithm : algorithm;
    const useMulti = overrideOpts.multiVehicle !== undefined ? overrideOpts.multiVehicle : multiVehicle;
    const useVehId = overrideOpts.vehicleId !== undefined ? overrideOpts.vehicleId : vehicleId;
    setOptimizing(true);
    try {
      const r = await apiFetch('/api/routing/optimize', {
        method: 'POST',
        body: JSON.stringify({
          mode: 'orders',
          order_ids: selectedOrderIds,
          vehicle_id: useVehId,
          enforce_time_window: enforceTw,
          save_to_db: save,
          algorithm: useAlgo,
          multi_vehicle: useMulti,
        }),
      });
      setRouteResult(r.result);
      if (r.saved_routes) setInitData((p) => ({ ...p, saved_routes: r.saved_routes }));
      showToast(
        `${save ? 'Đã lưu' : 'Xem trước'} tuyến ${r.result.route_code}: ${r.result.total_distance_km} km (-${r.result.saved_pct}%) [${r.result.algorithm_name || useAlgo}]!`
      );
      if (save && onRefreshHeader) onRefreshHeader();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setOptimizing(false);
    }
  };

  const run100Points = async (cnt) => {
    setOptimizing(true);
    try {
      setScopeCount(cnt);
      const r = await apiFetch('/api/routing/optimize', {
        method: 'POST',
        body: JSON.stringify({ mode: '100points', scope_count: cnt, enforce_time_window: enforceTw }),
      });
      setPoints100(r.result);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setOptimizing(false);
    }
  };

  useEffect(() => {
    if (subTab === '100points' && !points100) run100Points(scopeCount);
  }, [subTab]);

  const activeMapProps = useMemo(() => {
    const active = subTab === '100points' ? points100 : routeResult;
    const depot = active?.depot || initData?.depot || { lat: 10.8505, lng: 106.7718, name: 'Kho Tổng EcoLogix (TP. Thủ Đức)' };
    if (subTab === '100points' && active?.routes) {
      const vCol = { 'XE-01': '#10B981', 'XE-02': '#3B82F6', 'XE-03': '#8B5CF6' };
      return {
        depot,
        routes: Object.entries(active.routes).map(([vId, pts]) => ({
          color: vCol[vId] || '#059669',
          stops: pts.map((p, idx) => ({
            lat: p.lat,
            lng: p.lng,
            label: p.name,
            popup: `<b>${vId} • #${idx + 1} ${p.name}</b><br/>${p.district}, ${p.province} (${p.demand_kg}kg)`,
          })),
        })),
      };
    }
    if (active?.multi_vehicle && active?.multi_vehicle_routes?.length > 0) {
      return {
        depot,
        routes: active.multi_vehicle_routes.map((rt) => ({
          color: rt.color || '#059669',
          geometry: rt.geometry,
          stops: (rt.stops || []).map((s, idx) => ({
            lat: s.lat,
            lng: s.lng,
            label: s.customer_name,
            popup: `<b>${rt.vehicle_name} (#${idx + 1}) • ${s.customer_name}</b><br/>Đơn ${s.order_code} (${s.total_weight_kg}kg) • Đến ${s.arrival_time}`,
          })),
        })),
      };
    }
    const isEv = active?.vehicle?.fuel_type === 'Electric';
    return {
      depot,
      routes: active?.ordered_stops ? [{
        color: isEv ? '#059669' : '#0284C7',
        geometry: active.geometry,
        stops: active.ordered_stops.map((s, idx) => ({
          lat: s.lat,
          lng: s.lng,
          label: s.customer_name,
          popup: `<b>#${idx + 1} ${s.customer_name}</b><br/>Đơn ${s.order_code} (${s.total_weight_kg}kg) • Đến ${s.arrival_time}${isEv ? '<br/><span style="color:#059669;font-weight:700">⚡ Xe điện 0 phát thải CO₂</span>' : ''}`,
        })),
      }] : [],
    };
  }, [subTab, points100, routeResult]);

  if (!initData) return <LoadingSkeleton rows={4} />;

  const activeTotalWeight = initData.pending_orders
    .filter((o) => selectedOrderIds.includes(o.id))
    .reduce((acc, o) => acc + Number(o.total_weight_kg || 0), 0);

  const selectAllPending = () => {
    const allIds = initData.pending_orders.map((o) => o.id);
    setSelectedOrderIds(selectedOrderIds.length === allIds.length ? [] : allIds);
  };

  const applyRecommendedVehicle = (rec) => {
    setVehicleId(rec.vehicle_id);
    setMultiVehicle(false);
    runOptimize(false, { vehicleId: rec.vehicle_id, multiVehicle: false });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 border-b border-border-light pb-2">
        {[
          { id: 'orders', label: '● Điều phối đơn hàng thực tế' },
          { id: 'compare', label: 'So sánh Thuật toán & Xe Xanh' },
          { id: 'schedule', label: 'Lịch trình điểm dừng chi tiết' },
          { id: '100points', label: '🌐 Thực nghiệm 100 điểm TP.HCM - Đồng Nai' },
        ].map((t) => (
          <button key={t.id} onClick={() => setSubTab(t.id)} className={`px-4 py-2 rounded-xl text-xs font-bold transition ${subTab === t.id ? 'bg-brand-600 text-white shadow-sm' : 'text-text-sub hover:bg-canvas'}`}>{t.label}</button>
        ))}
      </div>

      {(subTab === 'orders' || subTab === '100points') && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-4 eco-card-glow bg-white p-5 sm:p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3.5 text-xs">
            {subTab === 'orders' ? (
              <>
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-extrabold text-sm m-0">Chọn đơn hàng & Thuật toán</h4>
                  <button type="button" onClick={selectAllPending} className="text-[11px] font-bold text-brand-600 hover:underline">
                    {selectedOrderIds.length === initData.pending_orders.length ? 'Bỏ chọn' : `Chọn tất cả (${initData.pending_orders.length})`}
                  </button>
                </div>
                <div className="text-[11px] text-text-sub flex justify-between bg-sky-50/70 px-3 py-1.5 rounded-xl border border-sky-100">
                  <span>Đã chọn: <strong>{selectedOrderIds.length} đơn</strong></span>
                  <span>Tổng tải: <strong className="text-brand-700">{activeTotalWeight.toLocaleString()} kg</strong></span>
                </div>
                <div className="max-h-44 overflow-y-auto space-y-1.5 border border-sky-100 rounded-2xl p-2.5 bg-slate-50/70">
                  {initData.pending_orders.map((o) => {
                    const checked = selectedOrderIds.includes(o.id);
                    return (
                      <label key={o.id} className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white cursor-pointer">
                        <input type="checkbox" checked={checked} onChange={() => setSelectedOrderIds(checked ? selectedOrderIds.filter((x) => x !== o.id) : [...selectedOrderIds, o.id])} className="text-brand-600" />
                        <span className="flex-1 truncate"><strong>{o.order_code}</strong> • {o.district} ({o.total_weight_kg}kg)</span>
                        {o.is_urban_restricted ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">Nội đô</span> : null}
                      </label>
                    );
                  })}
                </div>
                <div>
                  <label className="font-bold text-text-sub block mb-1">Thuật toán tối ưu Green VRPTW:</label>
                  <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)} disabled={multiVehicle} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70 font-semibold disabled:opacity-60">
                    {ROUTING_ALGORITHMS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                  </select>
                </div>
                <label className="flex items-start gap-2 cursor-pointer p-2 rounded-xl bg-emerald-50/70 border border-emerald-100">
                  <input type="checkbox" checked={multiVehicle} onChange={(e) => setMultiVehicle(e.target.checked)} className="text-brand-600 mt-0.5" />
                  <span>
                    <strong className="block text-emerald-900">Tự động chia tải đa xe (Clarke-Wright CVRP)</strong>
                    <span className="text-[11px] text-emerald-700">Tự tách tuyến nhiều xe khi vượt tải & ưu tiên EV nội đô.</span>
                  </span>
                </label>
                <div>
                  <label className="font-bold text-text-sub block mb-1">Phương tiện vận tải:</label>
                  <select value={vehicleId || ''} onChange={(e) => setVehicleId(Number(e.target.value))} disabled={multiVehicle} className="w-full px-3 py-2 rounded-xl border border-sky-200 bg-slate-50/70 font-semibold disabled:opacity-60">
                    {initData.vehicles.map((v) => <option key={v.id} value={v.id}>{v.vehicle_name} ({v.max_load_kg}kg - {v.fuel_type})</option>)}
                  </select>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={enforceTw} onChange={(e) => setEnforceTw(e.target.checked)} className="text-brand-600" />
                  <span>Né giờ cấm tải ({initData.config.restricted_time_window.join('–')})</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-2">
                  <button type="button" disabled={optimizing} onClick={() => runOptimize(false)} className="w-full bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200 py-2.5 rounded-full font-bold transition disabled:opacity-60">
                    {optimizing ? '⏳ Đang giải...' : '⚡ Chạy thử AI'}
                  </button>
                  <button type="button" disabled={optimizing} onClick={() => runOptimize(true)} className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-lg text-white py-2.5 rounded-full font-extrabold shadow-md shadow-brand-500/20 transition disabled:opacity-60">
                    {optimizing ? '⏳ Đang tối ưu...' : '🚀 Lưu tuyến DB'}
                  </button>
                </div>
                {routeResult && (
                  <div className="pt-3 border-t border-sky-100 space-y-1.5">
                    {routeResult.algorithm_name && (
                      <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-brand-700 font-bold text-[11px]">
                        🧠 {routeResult.algorithm_name}
                      </div>
                    )}
                    {routeResult.overload_warning && (
                      <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 space-y-1.5">
                        <div className="font-bold">⚠️ Vượt tải trọng tối đa ({routeResult.max_capacity_kg}kg)!</div>
                        {!multiVehicle && (
                          <button type="button" onClick={() => { setMultiVehicle(true); runOptimize(false, { multiVehicle: true }); }} className="px-2.5 py-1 rounded-lg bg-amber-600 text-white font-bold text-[11px] hover:bg-amber-700">
                            Bật chia tải đa xe ngay →
                          </button>
                        )}
                      </div>
                    )}
                    {routeResult.multi_vehicle && routeResult.multi_vehicle_routes?.length > 0 && (
                      <div className="space-y-1 pt-1">
                        {routeResult.multi_vehicle_routes.map((rt) => (
                          <div key={rt.vehicle_id} className="flex items-center justify-between px-2.5 py-1.5 rounded-xl bg-slate-50 border border-sky-100">
                            <span className="flex items-center gap-1.5 font-bold">
                              <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: rt.color }} />
                              {rt.vehicle_name} ({rt.stops.length} điểm)
                            </span>
                            <span className="font-mono text-[11px]">{rt.load_kg}/{rt.max_capacity_kg}kg • {rt.distance_km}km</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="flex justify-between"><span>Quãng đường:</span><strong>{routeResult.total_distance_km} km (-{routeResult.saved_pct}%)</strong></div>
                    <div className="flex justify-between"><span>Giảm phát thải CO₂:</span><strong className="text-brand-600">🌱 {routeResult.saved_co2_kg} kg</strong></div>
                    <div className="flex justify-between"><span>Chi phí dự kiến:</span><strong>{fmtVnd(routeResult.total_cost_vnd)}</strong></div>
                    <div className="flex justify-between"><span>Đúng khung giờ KH:</span><strong className={routeResult.late_stops ? 'text-amber-600' : 'text-brand-600'}>{routeResult.total_stops - (routeResult.late_stops || 0)}/{routeResult.total_stops} điểm</strong></div>
                    <div className="flex justify-between"><span>Né giờ cấm tải:</span><strong>{routeResult.restricted_conflicts_avoided || 0} điểm nội đô</strong></div>
                  </div>
                )}
              </>
            ) : (
              <>
                <h4 className="font-extrabold text-sm m-0">Bộ dữ liệu 100 điểm thực nghiệm</h4>
                <div className="flex gap-2">
                  {[25, 50, 100].map((c) => (
                    <button key={c} disabled={optimizing} onClick={() => run100Points(c)} className={`flex-1 py-2 rounded-full font-bold transition ${scopeCount === c ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'bg-sky-50 text-text-sub hover:bg-sky-100'}`}>{c} điểm</button>
                  ))}
                </div>
                {points100 && (
                  <div className="space-y-2.5 pt-3 border-t border-sky-100">
                    {points100.algorithm_name && (
                      <div className="inline-block px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-brand-700 font-bold text-[11px]">
                        🧠 {points100.algorithm_name}
                      </div>
                    )}
                    <div className="flex justify-between"><span>Tổng quãng đường 3 xe:</span><strong>{points100.total_distance_km} km (-{points100.saved_pct}%)</strong></div>
                    <div className="flex justify-between"><span>CO₂ cắt giảm:</span><strong className="text-brand-600">{points100.saved_co2_kg} kg</strong></div>
                    <div className="flex justify-between"><span>Tiết kiệm tiền:</span><strong className="text-brand-600">{fmtVnd(points100.saved_money_vnd)}</strong></div>
                    <div className="flex justify-between"><span>Tổng tải trọng:</span><strong>{points100.total_load_kg.toLocaleString()} kg</strong></div>
                    {points100.metrics_by_vehicle && (
                      <div className="space-y-1.5 pt-2 border-t border-sky-100">
                        <div className="font-bold text-text-sub text-[11px]">Phân bổ đội 3 xe:</div>
                        {Object.entries(points100.metrics_by_vehicle).map(([vId, m]) => (
                          <div key={vId} className="p-2 rounded-xl bg-slate-50 border border-sky-100 flex justify-between items-center text-[11px]">
                            <div>
                              <strong className="text-text-main">{vId}</strong> <span className="text-text-sub">({m.fuel_type})</span>
                              <div className="text-text-sub">{m.stops} điểm • {m.load_kg}/{m.capacity_kg} kg</div>
                            </div>
                            <div className="text-right font-mono">
                              <div className="font-bold">{m.distance_km} km</div>
                              <div className="text-brand-600">{m.co2_kg ?? 0} kg CO₂</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          <div className="lg:col-span-8 eco-card-glow bg-white p-4 sm:p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3">
            <div className="flex flex-wrap justify-between items-center gap-2">
              <span className="text-xs font-bold text-text-sub">
                {subTab === '100points'
                  ? `Bản đồ ${points100?.algorithm_name || 'Clarke-Wright Savings + 2-Opt/Or-Opt (3 Xe)'}`
                  : routeResult?.algorithm_name
                    ? `Bản đồ tối ưu: ${routeResult.algorithm_name}`
                    : 'Bản đồ tuyến đường tối ưu Green VRPTW'}
              </span>
              <span className="bg-emerald-50 text-brand-700 border border-emerald-200 font-extrabold text-xs px-3 py-1 rounded-full">
                {subTab === '100points' && points100 ? `${points100.total_distance_km} km (-${points100.saved_pct}%)` : routeResult ? `${routeResult.total_distance_km} km (-${routeResult.saved_pct}%)` : ''}
              </span>
            </div>
            <EcoLeafletMap
              depot={activeMapProps.depot}
              routes={activeMapProps.routes}
              showRestrictedZone={enforceTw}
              heightClass="h-[290px] sm:h-[360px] lg:h-[clamp(380px,54dvh,540px)]"
              defaultTheme="osm"
              openDepotPopup={true}
            />
          </div>
        </div>
      )}

      {subTab === 'orders' && routeResult && !routeResult.multi_vehicle && routeResult.vehicle_recommendations?.length > 0 && (
        <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h4 className="font-extrabold text-sm m-0">🌱 Gợi ý Xe Xanh Tối Ưu (So sánh Diesel vs Xe điện EV)</h4>
            <span className="text-[11px] text-text-sub">Xếp hạng dựa trên tổng chi phí vận hành & phát thải CO₂ trên tuyến vừa tối ưu</span>
          </div>
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub">
              <tr>
                <th className="p-2.5">Phương tiện</th>
                <th className="p-2.5">Nhiên liệu</th>
                <th className="p-2.5">Tải tối đa</th>
                <th className="p-2.5">Chi phí dự kiến</th>
                <th className="p-2.5">Phát thải CO₂</th>
                <th className="p-2.5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {routeResult.vehicle_recommendations.map((rec) => {
                const isSelected = rec.vehicle_id === vehicleId;
                return (
                  <tr key={rec.vehicle_id} className={`border-t border-sky-100/80 ${isSelected ? 'bg-emerald-50/60' : 'hover:bg-slate-50'}`}>
                    <td className="p-2.5 font-bold">{rec.vehicle_name} <span className="text-text-sub font-mono">({rec.plate_number})</span></td>
                    <td className="p-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${rec.fuel_type === 'Electric' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'}`}>
                        {rec.fuel_type === 'Electric' ? '⚡ Electric' : `⛽ ${rec.fuel_type}`}
                      </span>
                    </td>
                    <td className="p-2.5 font-mono">
                      {rec.max_load_kg} kg {rec.fits_load ? <span className="text-brand-600 font-bold">✓ Đủ tải</span> : <span className="text-amber-600 font-bold">⚠️ Quá tải</span>}
                    </td>
                    <td className="p-2.5 font-mono font-bold">{fmtVnd(rec.total_cost_vnd)}</td>
                    <td className="p-2.5 font-mono text-brand-600 font-bold">{rec.co2_emission_kg} kg</td>
                    <td className="p-2.5 text-right">
                      {isSelected ? (
                        <span className="px-2.5 py-1 rounded-full bg-brand-600 text-white text-[11px] font-bold">Đang chọn</span>
                      ) : (
                        <button type="button" onClick={() => applyRecommendedVehicle(rec)} className="px-3 py-1 rounded-full bg-sky-50 hover:bg-brand-600 hover:text-white text-sky-700 font-bold text-[11px] transition">
                          Chọn xe này
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {subTab === 'compare' && routeResult && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Quãng đường AI vs Cũ</div><div className="font-mono text-xl font-extrabold text-brand-600">{routeResult.total_distance_km} km</div><div className="text-[11px] text-text-sub">Truyền thống FIFO: {routeResult.baseline_distance_km} km</div></div>
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Nhiên liệu / Điện tiêu thụ</div><div className="font-mono text-xl font-extrabold">{routeResult.fuel_needed_liters}</div><div className="text-[11px] text-brand-600">Tiết kiệm {routeResult.saved_fuel_liters}</div></div>
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Phát thải CO₂</div><div className="font-mono text-xl font-extrabold">{routeResult.co2_emission_kg} kg</div><div className="text-[11px] text-brand-600">Giảm {routeResult.saved_co2_kg} kg CO₂</div></div>
            <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Chi phí vận chuyển</div><div className="font-mono text-xl font-extrabold">{fmtVnd(routeResult.total_cost_vnd)}</div><div className="text-[11px] text-brand-600">Tiết kiệm {fmtVnd(routeResult.saved_money_vnd)}</div></div>
          </div>

          {routeResult.algorithm_benchmarks?.length > 0 && (
            <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
              <h4 className="font-extrabold text-sm mb-3 m-0">📊 Benchmark So Sánh Các Thuật Toán Green VRPTW</h4>
              <table className="w-full text-xs text-left">
                <thead className="bg-sky-50/70 text-text-sub">
                  <tr>
                    <th className="p-2.5">Thuật toán</th>
                    <th className="p-2.5">Quãng đường</th>
                    <th className="p-2.5">Phát thải CO₂</th>
                    <th className="p-2.5">Chi phí vận hành</th>
                    <th className="p-2.5">Điểm trễ giờ</th>
                    <th className="p-2.5">Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {routeResult.algorithm_benchmarks.map((b) => (
                    <tr key={b.id} className={`border-t border-sky-100/80 ${b.selected ? 'bg-emerald-50/70 font-semibold' : 'hover:bg-slate-50'}`}>
                      <td className="p-2.5">{b.name}</td>
                      <td className="p-2.5 font-mono">{b.distance_km} km</td>
                      <td className="p-2.5 font-mono text-brand-600">{b.co2_kg} kg</td>
                      <td className="p-2.5 font-mono">{fmtVnd(b.total_cost_vnd)}</td>
                      <td className="p-2.5 font-mono">{b.late_stops}</td>
                      <td className="p-2.5">
                        {b.selected ? (
                          <span className="px-2.5 py-0.5 rounded-full bg-brand-600 text-white text-[11px] font-bold">★ Tối ưu nhất</span>
                        ) : (
                          <span className="text-text-sub text-[11px]">Tham chiếu</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

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
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-extrabold text-sm m-0">Lịch trình giao hàng chi tiết ({routeResult.route_code})</h4>
            <span className="text-xs font-bold text-brand-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">{routeResult.algorithm_name}</span>
          </div>
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub">
              <tr>
                <th className="p-2.5">STT</th>
                <th className="p-2.5">Mã đơn</th>
                <th className="p-2.5">Xe phụ trách</th>
                <th className="p-2.5">Khách hàng</th>
                <th className="p-2.5">Khu vực</th>
                <th className="p-2.5">Khung giờ KH</th>
                <th className="p-2.5">Giờ đến</th>
                <th className="p-2.5">Giờ rời</th>
                <th className="p-2.5">Giao / Tải xe</th>
                <th className="p-2.5">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {routeResult.ordered_stops.map((s) => (
                <tr key={s.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30">
                  <td className="p-2.5 font-bold">#{s.stop_sequence}</td>
                  <td className="p-2.5 font-mono font-bold">{s.order_code}</td>
                  <td className="p-2.5">{s.assigned_vehicle || routeResult.vehicle?.vehicle_name || '-'}</td>
                  <td className="p-2.5 font-medium">{s.customer_name}</td>
                  <td className="p-2.5">{s.district}, {s.province}</td>
                  <td className="p-2.5 font-mono text-text-sub">{s.time_window_start || '08:00'}–{s.time_window_end || '17:30'}</td>
                  <td className="p-2.5 font-mono text-brand-600 font-bold">{s.arrival_time}</td>
                  <td className="p-2.5 font-mono">{s.departure_time}</td>
                  <td className="p-2.5 font-mono">{s.total_weight_kg} / {s.remaining_load_kg !== undefined ? s.remaining_load_kg : '-'} kg</td>
                  <td className="p-2.5">
                    {s.curfew_avoided ? (
                      <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[11px]">Né cấm tải</span>
                    ) : (s.late_minutes || 0) > 0 ? (
                      <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-bold text-[11px]">Trễ {s.late_minutes}p</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-bold text-[11px]">Đúng giờ</span>
                    )}
                  </td>
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
