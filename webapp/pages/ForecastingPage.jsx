const { useState, useEffect, useRef, useMemo } = React;

// ==================== 6. FORECASTING VIEW (REAL LIGHTGBM) ====================
function ForecastingView({ showToast, onRefreshHeader }) {
  const [subTab, setSubTab] = useState('tong_quan');
  const [productId, setProductId] = useState(1);
  const [horizon, setHorizon] = useState(30);
  const [fc, setFc] = useState(null);
  const barRef = useRef(null);
  const barInst = useRef(null);
  const lineRef = useRef(null);
  const lineInst = useRef(null);

  const loadForecast = async (pid = productId, h = horizon, save = false) => {
    try {
      const d = await apiFetch(`/api/forecast?product_id=${pid}&horizon_days=${h}&save=${save}`);
      setFc(d);
      if (save) showToast('Đã lưu kết quả dự báo LightGBM vào bảng forecasts!');
    } catch (err) { showToast(err.message, 'error'); }
  };

  useEffect(() => { loadForecast(productId, horizon, false); }, [productId, horizon]);

  useEffect(() => {
    if (!fc || subTab !== 'tong_quan') return;
    if (barRef.current) {
      if (barInst.current) barInst.current.destroy();
      barInst.current = new Chart(barRef.current.getContext('2d'), {
        type: 'bar',
        data: {
          labels: fc.weekly_buckets.map((b) => b.week),
          datasets: [{ data: fc.weekly_buckets.map((b) => b.units), backgroundColor: '#A7F3D0', borderColor: '#059669', borderWidth: 1.5, borderRadius: 6 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } }
      });
    }
    if (lineRef.current) {
      if (lineInst.current) lineInst.current.destroy();
      const hLabels = fc.hist_series.map((x) => x.date);
      const fLabels = fc.fut_series.map((x) => x.date);
      const allLabels = [...hLabels, ...fLabels];
      const histVals = [...fc.hist_series.map((x) => x.actual), ...fLabels.map(() => null)];
      const futVals = [...hLabels.map(() => null), ...fc.fut_series.map((x) => x.forecast)];
      const upperVals = [...hLabels.map(() => null), ...fc.fut_series.map((x) => x.upper)];
      lineInst.current = new Chart(lineRef.current.getContext('2d'), {
        type: 'line',
        data: {
          labels: allLabels,
          datasets: [
            { label: 'Thực tế', data: histVals, borderColor: '#3B82F6', tension: 0.3, pointRadius: 2.5 },
            { label: 'Dự báo LightGBM', data: futVals, borderColor: '#059669', borderDash: [5, 5], tension: 0.3, pointRadius: 2.5 },
            { label: 'Cận trên 95% CI', data: upperVals, borderColor: 'rgba(16,185,129,0.25)', fill: '-1', backgroundColor: 'rgba(16,185,129,0.1)', pointRadius: 0 },
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { grid: { display: false } } } }
      });
    }
    return () => {
      if (barInst.current) barInst.current.destroy();
      if (lineInst.current) lineInst.current.destroy();
    };
  }, [fc, subTab]);

  const applyPo = async () => {
    try {
      const r = await apiFetch('/api/forecast/apply-po', {
        method: 'POST',
        body: JSON.stringify({ product_id: fc.selected_product.id, quantity: fc.suggested_po, warehouse_id: 1 })
      });
      showToast(r.message);
      loadForecast(productId, horizon, false);
      onRefreshHeader();
    } catch (err) { showToast(err.message, 'error'); }
  };

  if (!fc) return <div className="p-8 text-xs text-text-sub">⏳ Đang huấn luyện LightGBM Regressor...</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between items-center gap-3 border-b border-border-light pb-3">
        <div className="flex gap-2">
          {[
            { id: 'tong_quan', label: '● Tổng quan LightGBM' },
            { id: 'chi_tiet', label: 'Phân tích chi tiết' },
            { id: 'khu_vuc', label: 'Dự báo theo khu vực' },
            { id: 'lich_su', label: 'Lịch sử dự báo' }
          ].map((t) => (
            <button key={t.id} onClick={() => setSubTab(t.id)} className={`px-4 py-2 rounded-xl text-xs font-bold ${subTab === t.id ? 'bg-brand-600 text-white' : 'text-text-sub hover:bg-canvas'}`}>{t.label}</button>
          ))}
        </div>
        <div className="flex gap-2 items-center">
          <select value={productId} onChange={(e) => setProductId(Number(e.target.value))} className="text-xs px-3 py-2 rounded-xl border border-border-light bg-white font-semibold">
            {fc.products.map((p) => <option key={p.id} value={p.id}>{p.sku} - {p.name}</option>)}
          </select>
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="text-xs px-3 py-2 rounded-xl border border-border-light bg-white font-semibold">
            <option value={7}>7 ngày tới</option>
            <option value={30}>30 ngày tới</option>
            <option value={90}>90 ngày tới</option>
          </select>
          <button onClick={() => loadForecast(productId, horizon, true)} className="px-3.5 py-2 rounded-xl bg-slate-800 text-white text-xs font-bold">💾 Lưu</button>
        </div>
      </div>

      {subTab === 'tong_quan' && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-border-light shadow-sm flex flex-col justify-between">
              <div>
                <div className="text-xs font-bold text-text-sub mb-1">Kết quả dự báo ({fc.model_name})</div>
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-3xl font-extrabold text-text-main">{fc.total_forecast.toLocaleString('vi-VN')}</span>
                  <span className="text-sm font-semibold text-text-sub">{fc.selected_product.unit}</span>
                  <span className="text-xs font-bold text-brand-600 bg-emerald-50 px-2.5 py-0.5 rounded-full">{fc.growth_pct >= 0 ? '↑ +' : '↓ '}{fc.growth_pct}%</span>
                </div>
                <p className="text-xs text-text-sub mt-1">Độ chính xác Out-of-Sample: <strong>{fc.accuracy_pct}%</strong> (MAPE {fc.mape_pct}%)</p>
              </div>
              <div className="h-[200px] w-full mt-4"><canvas ref={barRef}></canvas></div>
            </div>
            <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-border-light shadow-sm">
              <h3 className="font-extrabold text-base text-text-main mb-3 m-0">Actual vs LightGBM Forecast (95% Confidence Band)</h3>
              <div className="h-[260px] w-full"><canvas ref={lineRef}></canvas></div>
            </div>
          </div>
          <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4">
            <div className="text-xs text-amber-900">
              💡 <strong>Khuyến nghị tồn kho thông minh:</strong> Tồn kho hiện hữu <strong>{fc.current_qty}</strong> {fc.selected_product.unit} | ROP: <strong>{fc.reorder_point}</strong> | Safety Stock: <strong>{fc.safety_stock}</strong>.
              {fc.suggested_po > 0 ? ` Đề xuất nhập thêm ${fc.suggested_po} ${fc.selected_product.unit}.` : ' Tồn kho đang an toàn.'}
            </div>
            {fc.suggested_po > 0 && <button onClick={applyPo} className="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl text-xs font-bold">Áp dụng nhập kho (+{fc.suggested_po})</button>}
          </div>
        </>
      )}

      {subTab === 'chi_tiet' && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Độ chính xác LightGBM</div><div className="font-mono text-2xl font-extrabold text-brand-600 mt-1">{fc.accuracy_pct}%</div><div className="text-[11px] text-text-sub">MAPE {fc.mape_pct}%</div></div>
          <div className="bg-white p-5 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Safety Stock (Z=1.65)</div><div className="font-mono text-2xl font-extrabold text-text-main mt-1">{fc.safety_stock}</div></div>
          <div className="bg-white p-5 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Điểm đặt hàng lại (ROP)</div><div className="font-mono text-2xl font-extrabold text-text-main mt-1">{fc.reorder_point}</div></div>
          <div className="bg-white p-5 rounded-2xl border border-border-light"><div className="text-xs text-text-sub">Tồn kho hiện tại</div><div className="font-mono text-2xl font-extrabold text-blue-600 mt-1">{fc.current_qty}</div></div>
        </div>
      )}

      {subTab === 'khu_vuc' && (
        <div className="bg-white p-6 rounded-2xl border border-border-light shadow-sm overflow-x-auto">
          <h4 className="font-extrabold text-sm mb-4 m-0">Phân bổ nhu cầu thực tế theo Tỉnh/TP (SQLite `orders` & `customers`)</h4>
          <table className="w-full text-xs text-left">
            <thead className="bg-canvas text-text-sub"><tr><th className="p-3">Khu vực</th><th className="p-3">Số đơn hàng</th><th className="p-3">Tỷ trọng</th><th className="p-3">Tổng khối lượng</th><th className="p-3">Doanh thu</th></tr></thead>
            <tbody>
              {fc.regions.map((r, i) => (
                <tr key={i} className="border-t border-border-light">
                  <td className="p-3 font-bold">{r.province}</td>
                  <td className="p-3 font-mono">{r.order_count}</td>
                  <td className="p-3 font-bold text-brand-600">{r.share_pct}%</td>
                  <td className="p-3 font-mono">{r.weight_kg} kg</td>
                  <td className="p-3 font-mono">{fmtVnd(r.revenue_vnd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {subTab === 'lich_su' && (
        <div className="bg-white p-6 rounded-2xl border border-border-light shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-canvas text-text-sub"><tr><th className="p-2.5">Ngày lưu</th><th className="p-2.5">SKU</th><th className="p-2.5">Khung</th><th className="p-2.5">Dự báo</th><th className="p-2.5">Safety Stock</th><th className="p-2.5">Chính xác</th></tr></thead>
            <tbody>
              {fc.forecast_history.map((h) => (
                <tr key={h.id} className="border-t border-border-light">
                  <td className="p-2.5 text-slate-500">{h.created_at}</td>
                  <td className="p-2.5 font-bold">{h.sku} - {h.product_name}</td>
                  <td className="p-2.5">{h.horizon_days} ngày</td>
                  <td className="p-2.5 font-mono font-bold">{h.predicted_demand}</td>
                  <td className="p-2.5 font-mono">{h.safety_stock}</td>
                  <td className="p-2.5 text-brand-600 font-bold">{h.accuracy_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { ForecastingView });
