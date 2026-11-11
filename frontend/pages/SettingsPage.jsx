const { useState, useEffect, useRef, useMemo } = React;

// ==================== 16. SETTINGS & LIVE-CODE VIEW ====================
function SettingsView({ user, setUser, showToast }) {
  const [tab, setTab] = useState('live');
  const [data, setData] = useState(null);
  const [prof, setProf] = useState({ name: user?.name || '', phone: '' });
  const [comp, setComp] = useState({ name: '', tax_code: '', phone: '', address: '', industry: '' });
  const [aiCfg, setAiCfg] = useState({ mode: 'Hybrid-Demo', api_key: '' });
  const [live, setLive] = useState({ fuel_price: 23500, carbon_tax: 500, max_load_kg: 1500, restricted_start: '16:00', restricted_end: '18:00' });

  const load = async () => {
    try {
      const d = await apiFetch(`/api/settings?user_id=${user?.id || 1}`);
      setData(d);
      if (d.user) setProf({ name: d.user.name, phone: d.user.phone || '' });
      if (d.company) setComp(d.company);
      if (d.ai_config) setAiCfg({ mode: d.ai_config.mode, api_key: '' });
      if (d.config) {
        setLive({
          fuel_price: d.config.fuel_price_per_liter,
          carbon_tax: d.config.carbon_tax_rate,
          max_load_kg: d.config.max_vehicle_load_kg,
          restricted_start: d.config.restricted_time_window[0],
          restricted_end: d.config.restricted_time_window[1],
        });
      }
    } catch (err) { showToast(err.message, 'error'); }
  };

  useEffect(() => { load(); }, []);

  const saveProfile = async (e) => {
    e.preventDefault();
    const r = await apiFetch('/api/settings/profile', { method: 'PUT', body: JSON.stringify({ user_id: user?.id || 1, ...prof }) });
    setUser((p) => ({ ...p, name: prof.name }));
    showToast(r.message);
    load();
  };

  const saveCompany = async (e) => {
    e.preventDefault();
    const r = await apiFetch('/api/settings/company', { method: 'PUT', body: JSON.stringify(comp) });
    setUser((p) => ({ ...p, company_name: comp.name }));
    showToast(r.message);
    load();
  };

  const changeRole = async (uid, role) => {
    const r = await apiFetch(`/api/settings/rbac/${uid}`, { method: 'PUT', body: JSON.stringify({ role }) });
    showToast(r.message);
    load();
  };

  const saveAi = async (e) => {
    e.preventDefault();
    const r = await apiFetch('/api/settings/ai', { method: 'PUT', body: JSON.stringify(aiCfg) });
    showToast(r.message);
    load();
  };

  const saveLiveCode = async () => {
    try {
      const r = await apiFetch('/api/settings/live-code', { method: 'POST', body: JSON.stringify(live) });
      setData((p) => ({ ...p, sensitivity: r.sensitivity, config: r.config }));
      showToast(r.message);
      load();
    } catch (err) { showToast(err.message, 'error'); }
  };

  if (!data) return <div className="p-8 text-xs text-text-sub">⏳ Đang tải cấu hình hệ thống...</div>;

  return (
    <div className="space-y-5">
      <div className="flex gap-2 border-b border-border-light pb-2 overflow-x-auto">
        {[
          { id: 'live', label: '⚡ 15 Phút Live-Code' },
          { id: 'profile', label: '👤 Hồ sơ cá nhân' },
          { id: 'company', label: '🏢 Doanh nghiệp' },
          { id: 'rbac', label: '🛡️ Phân quyền RBAC' },
          { id: 'ai', label: '🤖 Cấu hình AI Key' },
          { id: 'logs', label: '📜 Nhật ký hoạt động' }
        ].map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-full text-xs font-bold whitespace-nowrap transition ${tab === t.id ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-text-sub hover:bg-sky-50'}`}>{t.label}</button>
        ))}
      </div>

      {!['Admin', 'Manager'].includes(user?.role || '') && ['live', 'company', 'rbac', 'ai'].includes(tab) && (
        <div className="bg-amber-50 border border-amber-200 px-4 py-3 rounded-2xl text-xs text-amber-900">
          🛡️ <strong>Chế độ chỉ xem ({user?.role}):</strong> Chỉ vai trò <strong>Admin</strong> hoặc <strong>Manager</strong> mới có quyền chỉnh sửa cấu hình doanh nghiệp, RBAC, AI Key và Live-Code.
        </div>
      )}

      {tab === 'live' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-6 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-4 text-xs">
            <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-2xl text-amber-900">
              <strong>⚡ Trạm Sửa Code 15 Phút Chung Kết:</strong> Cập nhật trực tiếp tham số kinh tế xuống file <code>backend/config.py</code> & SQLite, đồng bộ ngay cho cả Routing & Multi-Agent!
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div><label className="font-bold text-text-sub block mb-1">Giá xăng (VNĐ/Lít)</label><input type="number" step="500" value={live.fuel_price} onChange={(e) => setLive({ ...live, fuel_price: Number(e.target.value) })} className="w-full p-2.5 rounded-xl border border-sky-200 bg-slate-50 font-mono font-bold" /></div>
              <div><label className="font-bold text-text-sub block mb-1">Thuế Carbon (VNĐ/kg CO₂)</label><input type="number" step="100" value={live.carbon_tax} onChange={(e) => setLive({ ...live, carbon_tax: Number(e.target.value) })} className="w-full p-2.5 rounded-xl border border-sky-200 bg-slate-50 font-mono font-bold" /></div>
              <div><label className="font-bold text-text-sub block mb-1">Tải trọng chuẩn (kg)</label><input type="number" step="100" value={live.max_load_kg} onChange={(e) => setLive({ ...live, max_load_kg: Number(e.target.value) })} className="w-full p-2.5 rounded-xl border border-sky-200 bg-slate-50 font-mono font-bold" /></div>
              <div><label className="font-bold text-text-sub block mb-1">Khung giờ cấm tải</label><div className="flex gap-1"><input value={live.restricted_start} onChange={(e) => setLive({ ...live, restricted_start: e.target.value })} className="w-1/2 p-2.5 rounded-xl border border-sky-200 bg-slate-50 font-mono" /><input value={live.restricted_end} onChange={(e) => setLive({ ...live, restricted_end: e.target.value })} className="w-1/2 p-2.5 rounded-xl border border-sky-200 bg-slate-50 font-mono" /></div></div>
            </div>
            <button onClick={saveLiveCode} disabled={!['Admin', 'Manager'].includes(user?.role || '')} className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 disabled:opacity-50 text-white py-3 rounded-full font-extrabold shadow-md shadow-brand-500/20">🚀 Ghi vào config & Tính lại độ nhạy</button>
          </div>
          <div className="lg:col-span-6 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs">
            <h4 className="font-extrabold text-sm m-0">📊 Độ Nhạy Kinh Tế (145 km vận hành/ngày)</h4>
            <div className="p-4 rounded-2xl bg-sky-50/70 border border-sky-100 flex justify-between"><span>Chi phí nhiên liệu / ngày:</span><strong className="font-mono text-base">{fmtVnd(data.sensitivity.current.fuel_cost_vnd)} ({data.sensitivity.diff_fuel_vnd >= 0 ? '+' : ''}{fmtVnd(data.sensitivity.diff_fuel_vnd)})</strong></div>
            <div className="p-4 rounded-2xl bg-sky-50/70 border border-sky-100 flex justify-between"><span>Thuế Carbon / ngày:</span><strong className="font-mono text-base">{fmtVnd(data.sensitivity.current.carbon_tax_cost_vnd)}</strong></div>
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 flex justify-between"><span>Tổng chi phí vận hành / ngày:</span><strong className="font-mono text-base text-brand-700">{fmtVnd(data.sensitivity.current.total_cost_vnd)} ({data.sensitivity.diff_pct >= 0 ? '+' : ''}{data.sensitivity.diff_pct}%)</strong></div>
          </div>
        </div>
      )}

      {tab === 'profile' && (
        <form onSubmit={saveProfile} className="max-w-lg eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs">
          <h4 className="font-extrabold text-sm m-0">Hồ sơ cá nhân (`users`)</h4>
          <input value={prof.name} onChange={(e) => setProf({ ...prof, name: e.target.value })} placeholder="Họ tên" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
          <input value={prof.phone} onChange={(e) => setProf({ ...prof, phone: e.target.value })} placeholder="Số điện thoại" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
          <button type="submit" className="px-6 py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold">Lưu hồ sơ</button>
        </form>
      )}

      {tab === 'company' && (
        <form onSubmit={saveCompany} className="max-w-lg eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs">
          <h4 className="font-extrabold text-sm m-0">Thông tin Doanh nghiệp (`companies`)</h4>
          <input value={comp.name} onChange={(e) => setComp({ ...comp, name: e.target.value })} placeholder="Tên doanh nghiệp" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
          <input value={comp.tax_code || ''} onChange={(e) => setComp({ ...comp, tax_code: e.target.value })} placeholder="Mã số thuế" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
          <input value={comp.address || ''} onChange={(e) => setComp({ ...comp, address: e.target.value })} placeholder="Địa chỉ" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
          <button type="submit" disabled={!['Admin', 'Manager'].includes(user?.role || '')} className="px-6 py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 disabled:opacity-50 text-white font-bold">Lưu doanh nghiệp</button>
        </form>
      )}

      {tab === 'rbac' && (
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2.5">Họ tên</th><th className="p-2.5">Email</th><th className="p-2.5">Vai trò (RBAC)</th></tr></thead>
            <tbody>
              {data.users.map((u) => (
                <tr key={u.id} className="border-t border-sky-100/80 hover:bg-emerald-50/30">
                  <td className="p-2.5 font-bold">{u.name}</td>
                  <td className="p-2.5">{u.email}</td>
                  <td className="p-2.5">
                    <select disabled={!['Admin', 'Manager'].includes(user?.role || '')} value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} className="px-2.5 py-1 rounded-lg border border-sky-200 bg-slate-50 font-bold disabled:opacity-50">
                      <option>Admin</option><option>Manager</option><option>Dispatcher</option><option>Auditor</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'ai' && (
        <form onSubmit={saveAi} className="max-w-lg eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-3 text-xs">
          <div className="flex items-center justify-between gap-2">
            <h4 className="font-extrabold text-sm m-0">Cấu hình Multi-Agent Engine & API Key</h4>
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${data?.ai_config?.has_api_key ? 'bg-emerald-100 text-brand-700' : 'bg-slate-100 text-slate-600'}`}>
              {data?.ai_config?.has_api_key ? `Key: ${data.ai_config.api_key_masked}` : 'Chưa lưu API Key'}
            </span>
          </div>
          <select value={aiCfg.mode} onChange={(e) => setAiCfg({ ...aiCfg, mode: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50 font-bold">
            <option value="Hybrid-Demo">Hybrid-Demo (SQLite + LightGBM Engine Nội Bộ)</option>
            <option value="Gemini">Gemini LLM + SQLite Context</option>
          </select>
          <input type="password" value={aiCfg.api_key} onChange={(e) => setAiCfg({ ...aiCfg, api_key: e.target.value })} placeholder="Nhập Gemini API Key mới (để trống nếu giữ nguyên key cũ)" className="w-full px-3.5 py-2.5 rounded-xl border border-sky-200 bg-slate-50" />
          <button type="submit" disabled={!['Admin', 'Manager'].includes(user?.role || '')} className="px-6 py-2.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 disabled:opacity-50 text-white font-bold">Lưu cấu hình AI</button>
        </form>
      )}

      {tab === 'logs' && (
        <div className="eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-sky-50/70 text-text-sub"><tr><th className="p-2">Thời gian</th><th className="p-2">Người dùng</th><th className="p-2">Hành động</th><th className="p-2">Chi tiết</th></tr></thead>
            <tbody>
              {data.activity_logs.map((l) => <tr key={l.id} className="border-t border-sky-100/80"><td className="p-2 text-slate-500">{l.timestamp}</td><td className="p-2 font-bold">{l.user_name || 'Hệ thống'}</td><td className="p-2 font-mono">{l.action}</td><td className="p-2">{l.details}</td></tr>)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { SettingsView });
