const { useState, useEffect, useRef, useMemo } = React;

// ==================== 4. DASHBOARD VIEW (100% REAL SQLITE) ====================
function DashboardView({ onNavigate, showToast }) {
  const [data, setData] = useState(null);
  const chartRef = useRef(null);
  const chartInst = useRef(null);

  useEffect(() => {
    apiFetch('/api/dashboard').then(setData).catch((e) => showToast(e.message, 'error'));
  }, []);

  useEffect(() => {
    if (!data || !chartRef.current) return;
    if (chartInst.current) chartInst.current.destroy();
    const labels = (data.monthly_financial || []).map((m) => m.month);
    const costs = (data.monthly_financial || []).map((m) => Math.round(m.cost_vnd / 1000000));
    const revs = (data.monthly_financial || []).map((m) => Math.round(m.revenue_vnd / 1000000));
    chartInst.current = new Chart(chartRef.current.getContext('2d'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Chi phí (Triệu đ)', data: costs, borderColor: '#3B82F6', tension: 0.35, pointRadius: 4, borderWidth: 2.5 },
          { label: 'Doanh thu (Triệu đ)', data: revs, borderColor: '#059669', tension: 0.35, pointRadius: 4, borderWidth: 2.5 },
        ]
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } } }
    });
    return () => { if (chartInst.current) chartInst.current.destroy(); };
  }, [data]);

  const dashRoutes = useMemo(() => {
    if (!data?.map_routes) return [];
    const colors = ['#059669', '#3B82F6', '#8B5CF6'];
    return data.map_routes.map((rt, idx) => ({
      color: colors[idx % colors.length],
      stops: (rt.stops || []).map((s, sIdx) => ({
        lat: s.lat,
        lng: s.lng,
        label: s.address,
        popup: `<b>${rt.route_code} • Điểm #${sIdx + 1}</b><br/>${s.address} (${s.arrival_time})`
      })),
    }));
  }, [data]);

  if (!data) return <div className="p-10 text-center text-xs font-bold text-text-sub">⏳ Đang tải dữ liệu thực tế từ SQLite...</div>;

  const f = data.financial;
  const e = data.esg;
  const inv = data.inventory;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="eco-card-glow bg-white/95 p-5 rounded-3xl border border-sky-100 shadow-card"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 text-brand-600 flex items-center justify-center"><i className="fa-solid fa-cloud-arrow-down"></i></div><div className="text-xs font-bold text-slate-500">Giảm CO₂</div></div><div className="font-mono text-3xl font-extrabold text-slate-900 my-2">-{e.co2_reduction_pct}%</div><div className="text-xs font-bold text-brand-700 bg-emerald-50 border border-emerald-200/70 w-fit px-2.5 py-1 rounded-full">Giảm {e.co2_saved_kg} kg CO₂</div></div>
        <div className="eco-card-glow bg-white/95 p-5 rounded-3xl border border-sky-100 shadow-card"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center"><i className="fa-solid fa-wallet"></i></div><div className="text-xs font-bold text-slate-500">Tiết kiệm chi phí</div></div><div className="font-mono text-3xl font-extrabold text-slate-900 my-2">{f.cost_saving_pct}%</div><div className="text-xs font-bold text-sky-700 bg-sky-50 border border-sky-200/70 w-fit px-2.5 py-1 rounded-full">Tổng {f.total_orders} đơn hàng</div></div>
        <div className="eco-card-glow bg-white/95 p-5 rounded-3xl border border-sky-100 shadow-card"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center"><i className="fa-solid fa-truck"></i></div><div className="text-xs font-bold text-slate-500">Đang vận chuyển</div></div><div className="font-mono text-3xl font-extrabold text-slate-900 my-2">{f.shipping_orders} đơn</div><div className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/70 w-fit px-2.5 py-1 rounded-full">Né cấm tải {data.config.restricted_time_window.join('-')}</div></div>
        <div className="eco-card-glow bg-white/95 p-5 rounded-3xl border border-sky-100 shadow-card"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-100 text-teal-600 flex items-center justify-center"><i className="fa-solid fa-boxes-stacked"></i></div><div className="text-xs font-bold text-slate-500">Hiệu suất tồn kho</div></div><div className="font-mono text-3xl font-extrabold text-slate-900 my-2">{inv.inventory_efficiency_pct}%</div><div className="text-xs font-bold text-amber-800 bg-amber-50 border border-amber-200/70 w-fit px-2.5 py-1 rounded-full">{inv.low_stock_alerts} cảnh báo tồn</div></div>
      </div>

      {data.low_stock_items?.length > 0 && (
        <div className="eco-card-glow bg-gradient-to-r from-amber-50/90 via-white to-amber-50/70 border border-amber-200 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm">
          <div className="text-xs text-amber-900">
            ⚠️ <strong>Cảnh báo AI từ SQLite:</strong> {data.low_stock_items[0].sku} ({data.low_stock_items[0].product_name}) tại {data.low_stock_items[0].warehouse_name} chỉ còn <strong>{data.low_stock_items[0].quantity}</strong> (Ngưỡng an toàn {data.low_stock_items[0].safety_stock}).
          </div>
          <button onClick={() => onNavigate('inventory')} className="px-4 py-2 rounded-full bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-sm transition">Xử lý nhập kho →</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 eco-card-glow bg-white/95 p-6 rounded-3xl border border-sky-100 shadow-card">
          <div className="flex justify-between items-center mb-3"><h3 className="font-extrabold text-base text-slate-900 m-0">Xu hướng Chi phí vs Doanh thu (DB)</h3><span className="text-xs font-semibold text-brand-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">T7 - T11 / 2026</span></div>
          <div className="h-[270px] w-full"><canvas ref={chartRef}></canvas></div>
        </div>
        <div className="lg:col-span-5 eco-card-glow bg-white/95 p-6 rounded-3xl border border-sky-100 shadow-card">
          <div className="flex justify-between items-center mb-3"><h3 className="font-extrabold text-base text-slate-900 m-0">Bản đồ Tuyến Vận Chuyển</h3><button onClick={() => onNavigate('routing')} className="text-[11px] font-bold text-white bg-gradient-to-r from-brand-600 to-emerald-500 px-3.5 py-1.5 rounded-full shadow-sm hover:shadow-md transition">Tối ưu thêm →</button></div>
          <EcoLeafletMap depot={data.depot} routes={dashRoutes} showRestrictedZone={true} heightClass="h-[250px]" defaultTheme="osm" openDepotPopup={true} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 eco-card-glow bg-white/95 p-6 rounded-3xl border border-sky-100 shadow-card">
          <div className="flex justify-between items-center mb-4"><h3 className="font-extrabold text-base text-slate-900 m-0">Nhật ký hoạt động thực tế (`activity_logs`)</h3><button onClick={() => onNavigate('settings')} className="text-xs font-bold text-brand-600 hover:underline">Xem tất cả →</button></div>
          <div className="space-y-2.5">
            {(data.activity_logs || []).map((lg) => (
              <div key={lg.id} className="flex items-center justify-between p-3 rounded-2xl bg-sky-50/45 border border-sky-100/80 hover:bg-white hover:border-brand-200 hover:shadow-[0_0_14px_rgba(16,185,129,0.14)] transition-all">
                <div><div className="font-bold text-xs text-slate-900">{lg.action}</div><div className="text-[11px] text-slate-500">{lg.details}</div></div>
                <span className="text-[10px] text-slate-400 font-medium">{lg.timestamp}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="lg:col-span-5 eco-card-glow bg-gradient-to-br from-sky-100/80 via-white to-emerald-100/75 text-slate-900 p-6 rounded-3xl border border-sky-200/80 shadow-card flex flex-col justify-between relative overflow-hidden">
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 text-[10px] uppercase font-extrabold bg-emerald-100/90 text-brand-800 border border-emerald-300 px-3 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 pulse-dot"></span>
              ESG Score {e.green_score}%
            </span>
            <h4 className="text-xl font-extrabold mt-3 mb-1 text-slate-900">Hành động hôm nay<br /><span className="bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-emerald-500">Vì một tương lai xanh hơn</span></h4>
            <p className="text-xs text-slate-600 mt-2">Doanh thu ghi nhận: <strong className="text-slate-900">{fmtVnd(f.total_revenue_vnd)}</strong> | Tiết kiệm <strong className="text-brand-700">{e.fuel_saved_liters} Lít</strong> dầu.</p>
          </div>
          <div className="relative z-10 mt-4 pt-3 border-t border-sky-200/70 flex items-center justify-between text-xs text-brand-800 font-semibold">
            <span>🌳 Quy đổi tương đương <strong>{e.trees_equivalent.toLocaleString('vi-VN')} cây xanh</strong></span>
            <button onClick={() => onNavigate('reports')} className="px-3 py-1.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-[11px] font-bold shadow-sm hover:shadow-md transition">Xem ESG →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { DashboardView });
