const { useState, useEffect, useRef, useMemo } = React;

// ==================== 12. AI ASSISTANT VIEW (6 AGENTS + REASONING TRACE + DB PERSIST) ====================
function AiAssistantView({ user, preloadedPrompt, clearPreloaded, onNavigate, showToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastAction, setLastAction] = useState(null);

  useEffect(() => {
    apiFetch(`/api/ai/messages?user_id=${user?.id || 1}`).then((d) => setMessages(d.messages || [])).catch(() => {});
  }, []);

  const sendMessage = async (text) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput('');
    setLoading(true);
    try {
      const res = await apiFetch('/api/ai/chat', { method: 'POST', body: JSON.stringify({ query: q, user_id: user?.id || 1 }) });
      setMessages(res.messages || []);
      setLastAction(res.action || null);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (preloadedPrompt) {
      sendMessage(preloadedPrompt);
      clearPreloaded();
    }
  }, [preloadedPrompt]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-border-light shadow-sm flex flex-col justify-between h-[560px]">
        <div className="overflow-y-auto space-y-4 custom-scrollbar pr-2 flex-1">
          {messages.map((m, idx) => (
            <div key={idx} className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[82%] p-4 rounded-2xl text-xs whitespace-pre-line leading-relaxed ${
                m.sender === 'user' ? 'bg-emerald-100 text-text-main font-semibold rounded-br-none border border-emerald-200' : 'bg-canvas text-text-main rounded-bl-none border border-border-light'
              }`}>
                {m.content}
              </div>
              {m.trace && m.trace.length > 0 && (
                <details className="mt-1.5 max-w-[82%] bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-[11px] text-slate-600">
                  <summary className="font-bold cursor-pointer text-brand-700">🔍 Xem chuỗi suy luận 6 Agents ({m.trace.length} bước)</summary>
                  <ul className="mt-1.5 space-y-1 list-disc pl-4">
                    {m.trace.map((st, sIdx) => <li key={sIdx}><strong>{st.agent}:</strong> {st.action}</li>)}
                  </ul>
                </details>
              )}
            </div>
          ))}
          {loading && <div className="text-xs text-brand-600 font-bold animate-pulse">🤖 Supervisor & 5 Specialist Agents đang truy vấn SQLite...</div>}
        </div>

        {lastAction && (
          <div className="pt-2">
            <button onClick={() => onNavigate(lastAction.target_page === 'route_planner' ? 'routing' : lastAction.target_page)} className="px-4 py-1.5 rounded-xl bg-emerald-50 border border-brand-300 text-brand-700 text-xs font-bold hover:bg-brand-600 hover:text-white transition">
              ⚡ {lastAction.label} →
            </button>
          </div>
        )}

        <div className="pt-3 mt-2 border-t border-border-light flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendMessage()} placeholder="Nhập câu hỏi tiếng Việt (VD: Kho còn bao nhiêu? / Tối nay đi 5 đơn Bình Dương...)..." className="flex-1 text-xs px-4 py-3 rounded-xl border border-border-light bg-canvas" />
          <button onClick={() => sendMessage()} disabled={loading} className="bg-brand-600 hover:bg-brand-700 text-white px-5 rounded-xl font-bold text-xs">Gửi</button>
        </div>
      </div>

      <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-border-light shadow-sm space-y-4">
        <h4 className="font-extrabold text-sm m-0">✨ Gợi ý câu lệnh thực tế</h4>
        <div className="space-y-2">
          {[
            'Tối nay đi 5 đơn Bình Dương dùng xe nào rẻ nhất?',
            'Kho hàng hiện còn bao nhiêu sản phẩm và có mặt hàng nào sắp hết?',
            'Dự báo nhu cầu sản phẩm 30 ngày tới bằng LightGBM',
            'Tính lượng CO2 phát thải và báo cáo ESG tháng này'
          ].map((s, i) => (
            <button key={i} onClick={() => sendMessage(s)} className="w-full text-left p-3 rounded-xl bg-canvas hover:bg-emerald-50 border border-border-light text-xs font-semibold flex justify-between items-center">
              <span>💬 {s}</span><span className="text-brand-600">→</span>
            </button>
          ))}
        </div>
        <div className="bg-emerald-50 border border-emerald-200 p-3.5 rounded-xl text-[11px] text-brand-900">
          <strong>Ghi chú minh bạch:</strong> Hệ thống chạy Pipeline 6 Agents truy vấn SQLite & LightGBM nội bộ. Kết quả tính toán thời gian thực không bịa số liệu.
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { AiAssistantView });
