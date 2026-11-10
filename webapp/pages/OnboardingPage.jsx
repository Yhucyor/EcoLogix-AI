const { useState, useEffect, useRef, useMemo } = React;

// ==================== 3. ONBOARDING 3-STEP WIZARD (POPUP GIỮA MÀN HÌNH & STANDALONE, PHONG CÁCH INDEX) ====================
function OnboardingView({ user, onFinish, onBack, showToast, toast, isModal = false, onGoLogin }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    company_name: 'Công Ty TNHH Phân Phối Hàng Tiêu Dùng Sài Gòn',
    tax_code: '0318992211',
    address: 'Khu Công Nghệ Cao, TP. Thủ Đức',
    city: 'TP. Hồ Chí Minh',
    industry: 'Phân phối hàng tiêu dùng (FMCG)',
    size: 'Doanh nghiệp nhỏ (10 - 50 nhân viên)',
    warehouse_name: 'Kho Trung Tâm Quận 9',
    warehouse_code: 'WH-Q9-01',
    warehouse_address: 'Xa Lộ Hà Nội, TP. Thủ Đức',
    vehicle_name: 'Xe Tải Eco 2.0T Mới',
    vehicle_plate: '51D-668.88',
    max_load_kg: 1500,
    fuel_price: 23500,
    cost_per_km: 3800,
    user_id: user?.id || 1,
  });

  useEffect(() => {
    if (!isModal) return;
    const onKey = (e) => {
      if (e.key === 'Escape' && onBack) onBack();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isModal, onBack]);

  const handleComplete = async () => {
    try {
      await apiFetch('/api/onboarding', { method: 'POST', body: JSON.stringify(form) });
      onFinish(form.company_name);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const STEPS = [
    { n: 1, label: 'Thông tin doanh nghiệp' },
    { n: 2, label: 'Kho & Phương tiện' },
    { n: 3, label: 'Hoàn tất' },
  ];

  const card = (
    <div
      onClick={(e) => e.stopPropagation()}
      className="relative w-full max-w-2xl bg-white rounded-3xl border border-sky-100 shadow-2xl overflow-hidden my-auto"
    >
      {/* Header đồng bộ phong cách trang index */}
      <div className="relative bg-gradient-to-br from-sky-100/80 via-white to-emerald-50/85 px-6 sm:px-8 pt-6 pb-5 border-b border-sky-100">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <BrandLogo sizeClass="w-11 h-11" className="shadow-brand-500/20" />
            <div>
              <div className="flex items-baseline">
                <span className="text-xl font-bold tracking-tight text-slate-900">EcoLogix</span>
                <span className="text-xl font-extrabold text-brand-600 ml-1">AI</span>
              </div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100/80 border border-emerald-300 text-brand-800 text-[10px] font-bold mt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-500 pulse-dot"></span>
                <span>Thiết lập Doanh nghiệp Chuỗi cung ứng Xanh</span>
              </div>
            </div>
          </div>

          {isModal ? (
            <button
              type="button"
              onClick={onBack}
              aria-label="Đóng popup"
              className="w-9 h-9 rounded-full bg-white/90 hover:bg-slate-100 border border-slate-200 text-slate-600 flex items-center justify-center text-sm font-bold shadow-sm transition"
            >
              ✕
            </button>
          ) : (
            <button
              type="button"
              onClick={onBack}
              className="px-3.5 py-1.5 rounded-full border border-brand-600 text-brand-700 font-semibold text-xs hover:bg-brand-50 transition"
            >
              ← Trang chủ
            </button>
          )}
        </div>

        {/* Thanh 3 bước */}
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-4 mt-5 pt-4 border-t border-sky-100/80">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.n}>
              <button
                type="button"
                onClick={() => setStep(s.n)}
                className="flex items-center gap-2 focus:outline-none"
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition ${
                  step >= s.n
                    ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm'
                    : 'bg-white border border-slate-200 text-slate-400'
                }`}>
                  {step > s.n ? '✓' : s.n}
                </div>
                <span className={`text-xs font-bold ${step >= s.n ? 'text-slate-900' : 'text-slate-400'}`}>{s.label}</span>
              </button>
              {i < 2 && <div className={`hidden sm:block w-8 h-0.5 rounded-full ${step > s.n ? 'bg-brand-500' : 'bg-slate-200'}`}></div>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Nội dung 1 cột sạch sẽ */}
      <div className="p-6 sm:p-8 bg-white">
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 m-0">Bước 1: Thông tin Doanh nghiệp</h3>
              <p className="text-xs text-slate-500 mt-1">Khai báo hồ sơ doanh nghiệp để khởi tạo không gian điều hành trên SQLite</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-sm">
              <div className="sm:col-span-2">
                <label className="text-xs font-bold text-slate-600 block mb-1">Tên doanh nghiệp *</label>
                <input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-500 text-xs sm:text-sm" />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1">Mã số thuế *</label>
                <input value={form.tax_code} onChange={(e) => setForm({ ...form, tax_code: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-500 text-xs sm:text-sm" />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1">Thành phố</label>
                <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-500 text-xs sm:text-sm" />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-bold text-slate-600 block mb-1">Địa chỉ trụ sở</label>
                <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-500 text-xs sm:text-sm" />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1">Ngành nghề</label>
                <select value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-500 text-xs sm:text-sm">
                  <option>Phân phối hàng tiêu dùng (FMCG)</option>
                  <option>Bán lẻ & Siêu thị</option>
                  <option>Vận tải & Giao nhận 3PL</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1">Quy mô</label>
                <select value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-500 text-xs sm:text-sm">
                  <option>Doanh nghiệp nhỏ (10 - 50 nhân viên)</option>
                  <option>Doanh nghiệp vừa (50 - 200 nhân viên)</option>
                  <option>Siêu nhỏ (&lt; 10 nhân viên)</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 pt-3">
              <button type="button" onClick={onBack} className="px-5 py-3 rounded-full border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition">Đóng</button>
              <button type="button" onClick={() => setStep(2)} className="flex-1 py-3 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-xs sm:text-sm font-bold shadow-lg shadow-brand-500/25 hover:shadow-xl transition">Tiếp tục Bước 2 →</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 m-0">Bước 2: Thiết lập Kho bãi, Phương tiện & Chi phí</h3>
              <p className="text-xs text-slate-500 mt-1">Cấu hình kho trung tâm, tải trọng xe chuẩn và giá nhiên liệu cho VRP</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-sm">
              <div><label className="text-xs font-bold text-slate-600 block mb-1">Tên kho hàng mới</label><input value={form.warehouse_name} onChange={(e) => setForm({ ...form, warehouse_name: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 text-xs sm:text-sm" /></div>
              <div><label className="text-xs font-bold text-slate-600 block mb-1">Mã kho</label><input value={form.warehouse_code} onChange={(e) => setForm({ ...form, warehouse_code: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 text-xs sm:text-sm" /></div>
              <div><label className="text-xs font-bold text-slate-600 block mb-1">Tên phương tiện mới</label><input value={form.vehicle_name} onChange={(e) => setForm({ ...form, vehicle_name: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 text-xs sm:text-sm" /></div>
              <div><label className="text-xs font-bold text-slate-600 block mb-1">Biển số xe</label><input value={form.vehicle_plate} onChange={(e) => setForm({ ...form, vehicle_plate: e.target.value })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 text-xs sm:text-sm" /></div>
              <div><label className="text-xs font-bold text-slate-600 block mb-1">Tải trọng chuẩn (kg)</label><input type="number" value={form.max_load_kg} onChange={(e) => setForm({ ...form, max_load_kg: Number(e.target.value) })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 text-xs sm:text-sm" /></div>
              <div><label className="text-xs font-bold text-slate-600 block mb-1">Giá xăng dầu (VNĐ/Lít)</label><input type="number" value={form.fuel_price} onChange={(e) => setForm({ ...form, fuel_price: Number(e.target.value) })} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 text-xs sm:text-sm" /></div>
            </div>
            <div className="flex gap-3 pt-3">
              <button type="button" onClick={() => setStep(1)} className="px-5 py-3 rounded-full border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition">← Quay lại</button>
              <button type="button" onClick={() => setStep(3)} className="flex-1 py-3 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-xs sm:text-sm font-bold shadow-lg shadow-brand-500/25 hover:shadow-xl transition">Tiếp tục Bước 3 →</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 m-0">Bước 3: Xác nhận & Kích hoạt Nền tảng</h3>
              <p className="text-xs text-slate-500 mt-1">Kiểm tra thông số trước khi đồng bộ vào SQLite & config.py</p>
            </div>
            <div className="bg-gradient-to-br from-sky-50/80 via-emerald-50/60 to-white border border-emerald-200 rounded-2xl p-4 sm:p-5 text-xs space-y-2 text-slate-700 leading-relaxed">
              <div>• <strong>Doanh nghiệp:</strong> {form.company_name} (MST: {form.tax_code})</div>
              <div>• <strong>Địa chỉ:</strong> {form.address}, {form.city} ({form.industry})</div>
              <div>• <strong>Kho thiết lập:</strong> {form.warehouse_name} ({form.warehouse_code})</div>
              <div>• <strong>Phương tiện:</strong> {form.vehicle_name} ({form.vehicle_plate}) • Tải tối đa {form.max_load_kg} kg</div>
              <div>• <strong>Giá nhiên liệu áp dụng:</strong> {fmtVnd(form.fuel_price)}/Lít</div>
            </div>
            <div className="flex gap-3 pt-3">
              <button type="button" onClick={() => setStep(2)} className="px-5 py-3 rounded-full border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition">← Quay lại sửa</button>
              <button type="button" onClick={handleComplete} className="flex-1 py-3 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-xs sm:text-sm font-bold shadow-lg shadow-brand-500/30 hover:shadow-xl transition">🚀 Hoàn tất & Vào Dashboard</button>
            </div>
          </div>
        )}

        <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
          <div className="flex items-center gap-4">
            <span><i className="fa-solid fa-check text-brand-500 mr-1"></i>Dùng thử 14 ngày</span>
            <span><i className="fa-solid fa-check text-brand-500 mr-1"></i>Không cần thẻ</span>
          </div>
          {onGoLogin && (
            <button type="button" onClick={onGoLogin} className="text-brand-600 font-bold hover:underline">
              Đã có tài khoản? Đăng nhập →
            </button>
          )}
        </div>
      </div>
    </div>
  );

  if (isModal) {
    return (
      <div
        onClick={onBack}
        className="fixed inset-0 z-[70] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
      >
        {card}
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full eco-sky-canvas relative overflow-hidden flex items-center justify-center p-4 sm:p-8">
      <div className="absolute top-10 left-1/4 w-[480px] h-[340px] bg-sky-200/40 blur-3xl rounded-full pointer-events-none"></div>
      <div className="absolute bottom-10 right-1/4 w-[480px] h-[340px] bg-emerald-200/35 blur-3xl rounded-full pointer-events-none"></div>
      {toast && <div className="fixed top-5 right-5 z-50 px-5 py-3 rounded-xl shadow-xl bg-red-600 text-white text-xs font-bold">{toast.msg}</div>}
      {card}
    </div>
  );
}

Object.assign(window, { OnboardingView });
