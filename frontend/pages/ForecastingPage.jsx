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

  const [csvOpen, setCsvOpen] = useState(false);
  const [csvText, setCsvText] = useState('date,quantity\n2026-10-01,42\n2026-10-02,48\n2026-10-03,55\n2026-10-04,63');
  const [csvSaving, setCsvSaving] = useState(false);

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

  const handleCsvFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setCsvText(String(ev.target?.result || ''));
    reader.readAsText(file, 'utf-8');
  };

  const submitCsv = async (e) => {
    e.preventDefault();
    setCsvSaving(true);
    try {
      const r = await apiFetch('/api/forecast/import-history', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId, csv_text: csvText }),
      });
      showToast(r.message);
      setCsvOpen(false);
      await loadForecast(productId, horizon, false);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setCsvSaving(false);
    }
  };

  if (!fc) return <LoadingSkeleton rows={5} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between items-center gap-3 border-b border-sky-100 pb-3">
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'tong_quan', label: '● Tổng quan LightGBM' },
            { id: 'chi_tiet', label: 'Phân tích chi tiết' },
            { id: 'khu_vuc', label: 'Dự báo theo khu vực' },
            { id: 'lich_su', label: 'Lịch sử dự báo' }
          ].map((t) => (
            <button key={t.id} onClick={() => setSubTab(t.id)} className={`px-4 py-2 rounded-full text-xs font-bold transition ${subTab === t.id ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-text-sub hover:bg-sky-50'}`}>{t.label}</button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <select value={productId} onChange={(e) => setProductId(Number(e.target.value))} className="text-xs px-3 py-2 rounded-xl border border-sky-200 bg-white font-semibold">
            {fc.products.map((p) => <option key={p.id} value={p.id}>{p.sku} - {p.name}</option>)}
          </select>
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="text-xs px-3 py-2 rounded-xl border border-sky-200 bg-white font-semibold">
            <option value={7}>7 ngày tới</option>
            <option value={30}>30 ngày tới</option>
            <option value={90}>90 ngày tới</option>
          </select>
          <button onClick={() => setCsvOpen(true)} className="px-3.5 py-2 rounded-full bg-white border border-sky-200 hover:border-brand-400 text-brand-700 text-xs font-bold transition">📥 Nhập CSV</button>
          <button onClick={() => loadForecast(productId, horizon, true)} className="px-4 py-2 rounded-full bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold transition">💾 Lưu</button>
        </div>
      </div>

      {subTab === 'tong_quan' && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-5 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm flex flex-col justify-between">
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
            <div className="lg:col-span-7 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm">
              <h3 className="font-extrabold text-base text-text-main mb-3 m-0">Actual vs LightGBM Forecast (95% Confidence Band)</h3>
              <div className="h-[260px] w-full"><canvas ref={lineRef}></canvas></div>
            </div>
          </div>
          <div className="bg-amber-50 border border-amber-200 p-4 rounded-3xl flex flex-wrap items-center justify-between gap-4">
            <div className="text-xs text-amber-900">
              💡 <strong>Khuyến nghị tồn kho thông minh:</strong> Tồn kho hiện hữu <strong>{fc.current_qty}</strong> {fc.selected_product.unit} | ROP: <strong>{fc.reorder_point}</strong> | Safety Stock: <strong>{fc.safety_stock}</strong>.
              {fc.suggested_po > 0 ? ` Đề xuất nhập thêm ${fc.suggested_po} ${fc.selected_product.unit}.` : ' Tồn kho đang an toàn.'}
            </div>
            {fc.suggested_po > 0 && <button onClick={applyPo} className="bg-gradient-to-r from-brand-600 to-emerald-500 text-white px-5 py-2.5 rounded-full text-xs font-bold shadow-sm">Áp dụng nhập kho (+{fc.suggested_po})</button>}
          </div>
        </>
      )}

      {subTab === 'chi_tiet' && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Độ chính xác LightGBM</div><div className="font-mono text-2xl font-extrabold text-brand-600 mt-1">{fc.accuracy_pct}%</div><div className="text-[11px] text-text-sub">MAPE {fc.mape_pct}%</div></div>
          <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Safety Stock (Z=1.65)</div><div className="font-mono text-2xl font-extrabold text-text-main mt-1">{fc.safety_stock}</div></div>
          <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Điểm đặt hàng lại (ROP)</div><div className="font-mono text-2xl font-extrabold text-text-main mt-1">{fc.reorder_point}</div></div>
          <div className="eco-card-glow bg-white p-5 rounded-3xl border border-sky-100 shadow-sm"><div className="text-xs text-text-sub">Tồn kho hiện tại</div><div className="font-mono text-2xl font-extrabold text-blue-600 mt-1">{fc.current_qty}</div></div>
        </div>
      )}

      {subTab === 'khu_vuc' && (
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <h4 className="font-extrabold text-sm mb-4 m-0">Phân bổ nhu cầu thực tế theo Tỉnh/TP (SQLite `orders` & `customers`)</h4>
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-3">Khu vực</th><th className="p-3">Số đơn hàng</th><th className="p-3">Tỷ trọng</th><th className="p-3">Tổng khối lượng</th><th className="p-3">Doanh thu</th></tr></thead>
            <tbody>
              {fc.regions.map((r, i) => (
                <tr key={i} className="border-t border-sky-100/80 hover:bg-emerald-50/30">
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
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">Ngày lưu</th><th className="p-2.5">SKU</th><th className="p-2.5">Khung</th><th className="p-2.5">Dự báo</th><th className="p-2.5">Safety Stock</th><th className="p-2.5">Chính xác</th></tr></thead>
            <tbody>
              {fc.forecast_history.map((h) => (
                <tr key={h.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30">
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

      <ModalShell open={csvOpen} title={`📥 Nhập CSV lịch sử bán hàng (${fc.selected_product.sku})`} onClose={() => setCsvOpen(false)}>
        <form onSubmit={submitCsv} className="space-y-3 text-xs">
          <p className="text-slate-600 m-0">
            Tải lên file <code>.csv</code> hoặc dán dữ liệu gồm 2 cột <code>date,quantity</code> (định dạng ngày <code>YYYY-MM-DD</code>). Dữ liệu sẽ được dùng để huấn luyện lại LightGBM cho sản phẩm đang chọn.
          </p>
          <input type="file" accept=".csv,.txt" onChange={handleCsvFile} className="block w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-emerald-50 file:text-brand-700 file:font-bold hover:file:bg-emerald-100" />
          <textarea
            rows={7}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            className="w-full p-3 rounded-2xl border border-sky-200 bg-slate-50 font-mono text-[11px] focus:bg-white focus:outline-none focus:border-brand-500"
            required
          />
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={() => setCsvOpen(false)} className="px-4 py-2 rounded-full border border-slate-300 font-bold text-slate-600">Đóng</button>
            <button type="submit" disabled={csvSaving} className="px-5 py-2 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold">
              {csvSaving ? 'Đang xử lý...' : '🚀 Nạp dữ liệu & Huấn luyện lại'}
            </button>
          </div>
        </form>
      </ModalShell>
    </div>
  );
}

Object.assign(window, { ForecastingView });
