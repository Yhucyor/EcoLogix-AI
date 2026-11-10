const { useState, useEffect, useRef, useMemo } = React;

// ==================== 13 & 14. REPORTS VIEW (REAL DB + REAL PDF/XLSX) ====================
function ReportsView({ showToast }) {
  const [tab, setTab] = useState('overview');
  const [rep, setRep] = useState(null);
  const finRef = useRef(null);
  const finInst = useRef(null);

  useEffect(() => { apiFetch('/api/reports').then(setRep).catch((e) => showToast(e.message, 'error')); }, []);

  useEffect(() => {
    if (!rep || tab !== 'overview' || !finRef.current) return;
    if (finInst.current) finInst.current.destroy();
    finInst.current = new Chart(finRef.current.getContext('2d'), {
      type: 'bar',
      data: {
        labels: rep.monthly_financial.map((m) => m.month),
        datasets: [
          { label: 'Chi phí (M)', data: rep.monthly_financial.map((m) => +(m.cost_vnd / 1e6).toFixed(1)), backgroundColor: '#3B82F6', borderRadius: 4 },
          { label: 'Lợi nhuận (M)', data: rep.monthly_financial.map((m) => +(m.profit_vnd / 1e6).toFixed(1)), backgroundColor: '#059669', borderRadius: 4 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
    return () => { if (finInst.current) finInst.current.destroy(); };
  }, [rep, tab]);

  if (!rep) return <div className="p-8 text-xs text-text-sub">⏳ Đang tổng hợp báo cáo từ SQLite...</div>;
  const esg = rep.esg_summary;
  const fin = rep.financial_summary;
  const deg = Math.round(esg.green_score);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2 border-b border-border-light pb-2">
        {[
          { id: 'overview', label: '● Tổng quan ESG & Kinh tế' },
          { id: 'financial', label: 'Báo cáo Tài chính' },
          { id: 'esg', label: 'Kiểm toán CO₂ theo Xe & Tuyến' }
        ].map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-xl text-xs font-bold ${tab === t.id ? 'bg-brand-600 text-white' : 'text-text-sub hover:bg-canvas'}`}>{t.label}</button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-border-light shadow-sm flex flex-col justify-between">
            <h4 className="font-extrabold text-sm m-0">Chỉ số ESG nổi bật (SQLite)</h4>
            <div className="flex items-center justify-around my-4">
              <div className="text-center">
                <div className="w-24 h-24 rounded-full flex items-center justify-center mx-auto" style={{ background: `conic-gradient(#059669 0% ${deg}%, #E2E8F0 ${deg}% 100%)` }}>
                  <div className="w-[74px] h-[74px] bg-white rounded-full flex items-center justify-center"><span className="font-mono text-lg font-extrabold text-brand-600">{esg.green_score}%</span></div>
                </div>
                <div className="text-xs font-bold mt-2">Mục tiêu xanh</div>
              </div>
              <div className="text-center bg-canvas p-4 rounded-xl border border-border-light">
                <div className="text-lg">🌱</div>
                <div className="text-[11px] text-text-sub">Phát thải CO₂</div>
                <div className="font-mono text-lg font-extrabold text-brand-600">-{esg.co2_reduction_pct}%</div>
                <div className="text-[10px] text-text-sub">Giảm {esg.co2_saved_kg} kg</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-border-light shadow-sm">
            <h4 className="font-extrabold text-sm mb-3 m-0">Chi phí vs Lợi nhuận theo tháng (Triệu VNĐ)</h4>
            <div className="h-[220px] w-full"><canvas ref={finRef}></canvas></div>
          </div>

          <div className="lg:col-span-3 bg-white p-6 rounded-2xl border border-border-light shadow-sm flex flex-col justify-between">
            <div>
              <h4 className="font-extrabold text-sm mb-3 m-0">Xuất Báo cáo Thật</h4>
              <p className="text-xs text-text-sub">Tạo trực tiếp bằng ReportLab UTF-8 PDF & OpenPyXL Workbook 3 sheets.</p>
            </div>
            <div className="space-y-2.5 mt-4">
              <a href="/api/reports/export/pdf" className="block text-center w-full bg-brand-600 hover:bg-brand-700 text-white py-2.5 rounded-xl text-xs font-bold">📄 Tải Báo cáo PDF</a>
              <a href="/api/reports/export/xlsx" className="block text-center w-full bg-slate-800 hover:bg-slate-900 text-white py-2.5 rounded-xl text-xs font-bold">📊 Tải Workbook Excel (.xlsx)</a>
            </div>
          </div>
        </div>
      )}

      {tab === 'financial' && (
        <div className="bg-white p-6 rounded-2xl border border-border-light space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div className="bg-canvas p-4 rounded-xl"><div>Doanh thu đơn hàng</div><strong className="text-lg font-mono">{fmtVnd(fin.total_revenue_vnd)}</strong></div>
            <div className="bg-canvas p-4 rounded-xl"><div>Chi phí kỳ gần nhất</div><strong className="text-lg font-mono">{fmtVnd(fin.latest_month_cost_vnd)}</strong></div>
            <div className="bg-canvas p-4 rounded-xl"><div>Chi phí nhiên liệu</div><strong className="text-lg font-mono">{fmtVnd(fin.fuel_cost_vnd)}</strong></div>
            <div className="bg-canvas p-4 rounded-xl"><div>Hoàn vốn (ROI)</div><strong className="text-lg font-mono text-brand-600">{fin.payback_months} tháng</strong></div>
          </div>
          <table className="w-full text-xs text-left">
            <thead className="bg-canvas text-text-sub"><tr><th className="p-2.5">Hạng mục chi phí</th><th className="p-2.5">Tổng chi</th><th className="p-2.5">Tỷ trọng</th></tr></thead>
            <tbody>{rep.cost_breakdown.map((b, i) => <tr key={i} className="border-t"><td className="p-2.5 font-bold">{b.category}</td><td className="p-2.5 font-mono">{fmtVnd(b.amount_vnd)}</td><td className="p-2.5 font-bold text-brand-600">{b.pct}%</td></tr>)}</tbody>
          </table>
        </div>
      )}

      {tab === 'esg' && (
        <div className="bg-white p-6 rounded-2xl border border-border-light overflow-x-auto">
          <h4 className="font-extrabold text-sm mb-3 m-0">Phát thải CO₂ theo từng Phương tiện (`vehicles` & `routes`)</h4>
          <table className="w-full text-xs text-left">
            <thead className="bg-canvas text-text-sub"><tr><th className="p-2.5">Biển số</th><th className="p-2.5">Tên xe</th><th className="p-2.5">Nhiên liệu</th><th className="p-2.5">Số chuyến</th><th className="p-2.5">Quãng đường</th><th className="p-2.5">CO₂ phát thải</th><th className="p-2.5">CO₂ tiết kiệm</th></tr></thead>
            <tbody>
              {rep.vehicle_performance.map((v) => (
                <tr key={v.id} className="border-t border-border-light">
                  <td className="p-2.5 font-mono font-bold">{v.plate_number}</td>
                  <td className="p-2.5">{v.vehicle_name}</td>
                  <td className="p-2.5">{v.fuel_type}</td>
                  <td className="p-2.5 font-mono">{v.total_routes}</td>
                  <td className="p-2.5 font-mono">{v.total_distance_km} km</td>
                  <td className="p-2.5 font-mono">{v.total_co2_kg} kg</td>
                  <td className="p-2.5 font-mono font-bold text-brand-600">{v.total_saved_co2_kg} kg</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { ReportsView });
