const { useState, useEffect, useRef, useMemo } = React;

// ==================== 15. NOTIFICATIONS VIEW ====================
function NotificationsView({ onRefreshHeader, showToast }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('ALL');
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = () => {
    setLoading(true);
    apiFetch(`/api/notifications?notif_type=${filterType}&unread_only=${unreadOnly}`)
      .then((d) => setItems(d.notifications || []))
      .catch((e) => showToast(e.message, 'error'))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [filterType, unreadOnly]);

  const readAll = async () => {
    await apiFetch('/api/notifications/read-all', { method: 'POST' });
    showToast('Đã đánh dấu đã đọc tất cả!');
    load();
    onRefreshHeader();
  };

  const readOne = async (id) => {
    await apiFetch(`/api/notifications/${id}/read`, { method: 'POST' });
    load();
    onRefreshHeader();
  };

  return (
    <div className="space-y-4">
      <div className="eco-card-glow flex flex-wrap justify-between items-center gap-3 bg-white p-4 rounded-3xl border border-sky-100 shadow-sm">
        <div className="flex gap-3 items-center text-xs">
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="px-3.5 py-2 rounded-xl border border-sky-200 bg-slate-50 font-semibold">
            <option value="ALL">Tất cả mức độ</option><option value="warning">Cảnh báo (warning)</option><option value="success">Thành công (success)</option><option value="info">Thông tin (info)</option>
          </select>
          <label className="flex items-center gap-1.5 cursor-pointer font-semibold text-slate-600"><input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Chỉ chưa đọc</label>
        </div>
        <button onClick={readAll} className="px-5 py-2 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-xs font-bold shadow-md shadow-brand-500/20">✓ Đánh dấu đọc tất cả</button>
      </div>
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : items.length === 0 ? (
        <EmptyState title="Không có thông báo" />
      ) : (
        items.map((n) => (
          <div key={n.id} className={`eco-card-glow p-5 rounded-3xl border flex justify-between items-center gap-4 shadow-sm ${n.is_read === 0 ? 'bg-gradient-to-r from-emerald-50/85 to-sky-50/70 border-emerald-200' : 'bg-white border-sky-100'}`}>
            <div>
              <div className="font-bold text-xs text-text-main">{n.title} {n.is_read === 0 && <span className="ml-2 bg-brand-600 text-white text-[9px] px-2 py-0.5 rounded-full">MỚI</span>}</div>
              <div className="text-xs text-text-sub mt-1">{n.message}</div>
              <div className="text-[10px] text-slate-400 mt-1">{n.created_at}</div>
            </div>
            {n.is_read === 0 && <button onClick={() => readOne(n.id)} className="px-3.5 py-1.5 rounded-full bg-white border border-sky-200 text-xs font-bold hover:border-brand-400 hover:text-brand-700 transition">Đã đọc</button>}
          </div>
        ))
      )}
    </div>
  );
}

Object.assign(window, { NotificationsView });
