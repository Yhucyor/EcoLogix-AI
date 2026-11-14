const { useState, useEffect, useRef, useMemo } = React;

// ==================== 12. AI ASSISTANT VIEW (LANGGRAPH MULTI-AGENT & PROPOSALS) ====================
function AiAssistantView({ user, preloadedPrompt, clearPreloaded, onNavigate, showToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastAction, setLastAction] = useState(null);
  const [activeProposal, setActiveProposal] = useState(null);
  const [deciding, setDeciding] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const loadHistory = () => {
    apiFetch(`/api/ai/messages?user_id=${user?.id || 1}`).then((d) => setMessages(d.messages || [])).catch(() => {});
  };

  useEffect(() => {
    loadHistory();
  }, [user?.id]);

  const sendMessage = async (text) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput('');
    setLoading(true);
    try {
      const res = await apiFetch('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({
          query: q,
          user_id: user?.id || 1,
        }),
      });
      setMessages(res.messages || []);
      setLastAction(res.action || null);
      if (res.proposal) {
        setActiveProposal(res.proposal);
      }
      if (res.status === 'needs_clarification') {
        showToast('Vui lòng cung cấp thêm thông tin theo hướng dẫn.', 'info');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (action) => {
    if (!activeProposal || deciding) return;
    setDeciding(true);
    try {
      const res = await apiFetch(`/api/ai/proposals/${activeProposal.id}/decision`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          expected_version: activeProposal.version || 1,
          request_id: `req_${Date.now()}`,
        }),
      });
      showToast(res.message, action === 'approve' ? 'success' : 'info');
      setActiveProposal((prev) => ({
        ...prev,
        status: action === 'approve' ? 'APPROVED' : 'REJECTED',
      }));
      loadHistory();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setDeciding(false);
    }
  };

  const resetChat = async () => {
    setConfirmClear(false);
    try {
      await apiFetch(`/api/ai/messages?user_id=${user?.id || 1}`, { method: 'DELETE' });
      setLastAction(null);
      setActiveProposal(null);
      loadHistory();
      showToast('Đã làm mới phiên hội thoại & xóa state đồ thị AI.');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  useEffect(() => {
    if (preloadedPrompt) {
      sendMessage(preloadedPrompt);
      clearPreloaded();
    }
  }, [preloadedPrompt]);

  const canApprove = ['Admin', 'Manager'].includes(user?.role || '');

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8 eco-card-glow bg-white p-4 sm:p-6 rounded-3xl border border-sky-100 shadow-sm flex flex-col justify-between h-[clamp(420px,68dvh,680px)]">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-sky-100">
            <div className="flex items-center gap-2 text-xs font-extrabold text-slate-800">
              <span className="w-2 h-2 rounded-full bg-brand-500 pulse-dot"></span>
              <span>EcoLogix Multi-Agent StateGraph (LangGraph Co-pilots)</span>
            </div>
            <button
              onClick={() => setConfirmClear(true)}
              className="px-3.5 py-1.5 rounded-full bg-sky-50 hover:bg-red-50 border border-sky-200 hover:border-red-200 text-[11px] font-bold text-slate-600 hover:text-red-600 transition"
            >
              🗑️ Xóa phiên & Reset State
            </button>
          </div>

          <div className="overflow-y-auto space-y-4 custom-scrollbar pr-2 flex-1">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}>
                <div
                  className={`max-w-[92%] sm:max-w-[82%] p-3.5 sm:p-4 rounded-2xl text-xs whitespace-pre-line leading-relaxed ${
                    m.sender === 'user'
                      ? 'bg-emerald-100 text-text-main font-semibold rounded-br-none border border-emerald-200'
                      : 'bg-sky-50/60 text-text-main rounded-bl-none border border-sky-100'
                  }`}
                >
                  {m.content}
                </div>
                {m.trace && m.trace.length > 0 && (
                  <details className="mt-1.5 max-w-[92%] sm:max-w-[82%] bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-[11px] text-slate-600">
                    <summary className="font-bold cursor-pointer text-brand-700">
                      🔍 Chuỗi điều phối đồ thị LangGraph ({m.trace.length} bước)
                    </summary>
                    <ul className="mt-1.5 space-y-1 list-disc pl-4">
                      {m.trace.map((st, sIdx) => (
                        <li key={sIdx}>
                          <strong>{st.agent}:</strong> {st.action}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
            {loading && (
              <div className="text-xs text-brand-600 font-bold animate-pulse flex items-center gap-2">
                <span>🤖</span>
                <span>LangGraph đang điều phối Multi-Agent (Intent ➔ Slots ➔ Routing ➔ Finance & ESG)...</span>
              </div>
            )}

            {/* BẢN DUYỆT ĐỀ XUẤT PROPOSAL (HUMAN-IN-THE-LOOP) */}
            {activeProposal && (
              <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 to-teal-50 border border-brand-200 shadow-sm mt-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">📋</span>
                    <strong className="text-xs text-brand-900 font-extrabold">
                      Bản đề xuất phê duyệt: {activeProposal.proposal_code}
                    </strong>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                      activeProposal.status === 'APPROVED'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : activeProposal.status === 'REJECTED'
                        ? 'bg-rose-100 text-rose-800 border border-rose-300'
                        : activeProposal.status === 'STALE'
                        ? 'bg-amber-100 text-amber-800 border border-amber-300'
                        : 'bg-sky-100 text-sky-800 border border-sky-300 animate-pulse'
                    }`}
                  >
                    {activeProposal.status}
                  </span>
                </div>
                <p className="text-xs text-slate-700 m-0">{activeProposal.summary}</p>

                {activeProposal.status === 'PENDING' && (
                  <div className="flex items-center gap-2 pt-2 border-t border-brand-100">
                    {canApprove ? (
                      <>
                        <button
                          onClick={() => handleDecision('approve')}
                          disabled={deciding}
                          className="px-4 py-1.5 rounded-full bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold shadow-sm transition disabled:opacity-50"
                        >
                          ✓ Duyệt & Áp dụng ngay
                        </button>
                        <button
                          onClick={() => handleDecision('reject')}
                          disabled={deciding}
                          className="px-4 py-1.5 rounded-full bg-white hover:bg-rose-50 border border-slate-300 hover:border-rose-300 text-slate-700 hover:text-rose-600 text-xs font-bold transition disabled:opacity-50"
                        >
                          ✕ Từ chối
                        </button>
                      </>
                    ) : (
                      <span className="text-[11px] text-amber-700 italic">
                        🔒 Vai trò '{user?.role || 'Auditor'}' chỉ có quyền xem. Cần vai trò Admin hoặc Manager để phê duyệt.
                      </span>
                    )}
                  </div>
                )}

                {activeProposal.status === 'APPROVED' && (
                  <div className="flex items-center gap-2 pt-1 text-[11px] text-emerald-700 font-semibold">
                    <span>✓ Đã lưu vào hệ thống và kích hoạt trạng thái giao hàng.</span>
                    <button
                      onClick={() => onNavigate('routing')}
                      className="text-brand-700 underline font-bold hover:text-brand-900"
                    >
                      Mở trang Lộ trình xem xe →
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {lastAction && (
            <div className="pt-2">
              <button
                onClick={() => onNavigate(lastAction.target_page === 'route_planner' ? 'routing' : lastAction.target_page)}
                className="px-4 py-1.5 rounded-full bg-emerald-50 border border-brand-300 text-brand-700 text-xs font-bold hover:bg-brand-600 hover:text-white transition"
              >
                ⚡ {lastAction.label} →
              </button>
            </div>
          )}

          <div className="pt-3 mt-2 border-t border-sky-100 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Hỏi về SKU, kho hàng hoặc lộ trình (VD: Kiểm tra tồn SKU-003 / Dự báo 14 ngày cho SKU đó)..."
              className="flex-1 text-xs px-4 py-3 rounded-full border border-sky-200 bg-slate-50/70 focus:bg-white focus:outline-none focus:border-brand-500"
            />
            <button
              onClick={() => sendMessage()}
              disabled={loading}
              className="bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-lg text-white px-6 rounded-full font-bold text-xs shadow-sm transition disabled:opacity-50"
            >
              Gửi
            </button>
          </div>
        </div>

        <div className="lg:col-span-4 eco-card-glow bg-white p-6 rounded-3xl border border-sky-100 shadow-sm space-y-4 h-fit">
          <h4 className="font-extrabold text-sm m-0">✨ Demo & Kịch bản thực tế (Issue #1)</h4>
          <div className="space-y-2">
            {[
              'Kiểm tra tồn kho SKU-003 tại Kho Thủ Đức',
              'Dự báo 14 ngày cho SKU đó',
              'Tối ưu giao 5 đơn Bình Dương và so chi phí, CO2',
              'Tính lượng CO2 phát thải và báo cáo ESG tháng này',
            ].map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                className="w-full text-left p-3.5 rounded-2xl bg-sky-50/60 hover:bg-emerald-50 border border-sky-100 hover:border-emerald-200 text-xs font-semibold flex justify-between items-center transition"
              >
                <span>💬 {s}</span>
                <span className="text-brand-600 ml-2">→</span>
              </button>
            ))}
          </div>
          <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-2xl text-[11px] text-brand-900 leading-relaxed">
            <strong>Stateful Multi-Agent (LangGraph):</strong> Hệ thống tự động ghi nhớ SKU và kho đã xác nhận trong phiên (`confirmed_slots`), hỗ trợ câu hỏi kế tiếp sau khi restart và quy trình duyệt đề xuất (Human-in-the-Loop) bảo đảm Idempotent.
          </div>
        </div>
      </div>

      <ConfirmModal
        open={confirmClear}
        title="Làm mới phiên hội thoại"
        message="Xóa lịch sử trò chuyện và reset toàn bộ state của đồ thị Multi-Agent để bắt đầu phiên mới sạch ngữ cảnh?"
        confirmText="Xóa lịch sử"
        onCancel={() => setConfirmClear(false)}
        onConfirm={resetChat}
      />
    </>
  );
}

Object.assign(window, { AiAssistantView });
