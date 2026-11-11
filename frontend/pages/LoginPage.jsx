const { useState, useEffect, useRef, useMemo } = React;

// ==================== 2. COMPLETE LOGIN / REGISTER / VERIFY / RESET VIEW ====================
function LoginView({ onLoginSuccess, onGoOnboarding, onGoHome, toast, showToast, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'register' | 'verify' | 'forgot'
  const [email, setEmail] = useState('nguyen.van.a@ecologix.vn');
  const [password, setPassword] = useState('password123');
  const [showPw, setShowPw] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Register state
  const [regName, setRegName] = useState('');
  const [regCompany, setRegCompany] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regRole, setRegRole] = useState('Manager');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPw, setRegConfirmPw] = useState('');

  // Verify & Forgot state
  const [otp, setOtp] = useState('');
  const [demoOtpHint, setDemoOtpHint] = useState('');
  const [emailSentInfo, setEmailSentInfo] = useState('');
  const [showRegPw, setShowRegPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [token, setToken] = useState('');
  const [demoTokenHint, setDemoTokenHint] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmNewPw, setConfirmNewPw] = useState('');

  const switchMode = (m) => {
    setErrorMsg('');
    setEmailSentInfo('');
    setMode(m);
  };

  const submitLogin = async (e, overrideEmail, overridePw) => {
    if (e) e.preventDefault();
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: (overrideEmail || email).trim(), password: overridePw || password }),
      });
      onLoginSuccess(res.user, res.access_token || '', remember);
    } catch (err) {
      const msg = err.message || 'Không thể đăng nhập.';
      setErrorMsg(msg);
      showToast(msg, 'error');
      if (msg.toLowerCase().includes('xác thực')) {
        setEmailSentInfo(`Tài khoản ${email.trim()} chưa kích hoạt OTP. Kiểm tra hộp thư hoặc bấm "Gửi lại OTP" bên dưới.`);
        setMode('verify');
      }
    } finally {
      setLoading(false);
    }
  };

  const submitRegister = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    if (regPassword.length < 6) {
      setErrorMsg('Mật khẩu phải có ít nhất 6 ký tự.');
      return;
    }
    if (regPassword !== regConfirmPw) {
      setErrorMsg('Mật khẩu xác nhận không khớp.');
      return;
    }
    setLoading(true);
    try {
      const cleanEmail = email.trim();
      const res = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          name: regName.trim(),
          email: cleanEmail,
          password: regPassword,
          phone: regPhone.trim(),
          role: regRole,
          company_name: regCompany.trim(),
        }),
      });
      showToast(res.message);
      setOtp(res.demo_otp || '');
      setDemoOtpHint(res.demo_otp || '');
      setEmailSentInfo(res.email_sent ? `Mã xác thực OTP 6 số đã được gửi tới email ${cleanEmail}. Vui lòng kiểm tra Hộp thư đến (hoặc mục Spam).` : '');
      setPassword(regPassword);
      setMode('verify');
    } catch (err) {
      setErrorMsg(err.message);
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setErrorMsg('');
    if (!email.trim()) {
      setErrorMsg('Vui lòng nhập email để gửi lại mã OTP.');
      return;
    }
    setLoading(true);
    try {
      const cleanEmail = email.trim();
      const res = await apiFetch('/api/auth/resend-otp', {
        method: 'POST',
        body: JSON.stringify({ email: cleanEmail }),
      });
      showToast(res.message);
      if (res.demo_otp) setOtp(res.demo_otp);
      setDemoOtpHint(res.demo_otp || '');
      setEmailSentInfo(res.email_sent ? `Đã gửi lại mã OTP mới tới email ${cleanEmail}. Vui lòng kiểm tra hộp thư.` : '');
    } catch (err) {
      setErrorMsg(err.message);
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const submitVerify = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);
    try {
      const res = await apiFetch('/api/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), otp_code: otp.trim() }),
      });
      showToast(res.message);
      setDemoOtpHint('');
      setMode('login');
    } catch (err) {
      setErrorMsg(err.message);
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const requestReset = async () => {
    setErrorMsg('');
    if (!email.trim()) {
      setErrorMsg('Vui lòng nhập Email đăng ký trước.');
      return;
    }
    setLoading(true);
    try {
      const cleanEmail = email.trim();
      const res = await apiFetch('/api/auth/forgot', {
        method: 'POST',
        body: JSON.stringify({ email: cleanEmail }),
      });
      showToast(res.message);
      setToken(res.demo_token || '');
      setDemoTokenHint(res.demo_token || '');
      setEmailSentInfo(res.email_sent ? `Mã khôi phục (RST-...) đã được gửi tới email ${cleanEmail}. Vui lòng kiểm tra Hộp thư đến (hoặc Spam).` : '');
    } catch (err) {
      setErrorMsg(err.message);
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    if (newPw.length < 6) {
      setErrorMsg('Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }
    if (newPw !== confirmNewPw) {
      setErrorMsg('Mật khẩu xác nhận không khớp.');
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch('/api/auth/reset', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), token: token.trim(), new_password: newPw }),
      });
      showToast(res.message);
      setPassword(newPw);
      setDemoTokenHint('');
      setMode('login');
    } catch (err) {
      setErrorMsg(err.message);
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[100dvh] lg:h-[100dvh] lg:overflow-hidden w-full grid grid-cols-1 lg:grid-cols-12 bg-white">
      {toast && (
        <div className={`fixed top-5 right-5 z-50 px-5 py-3 rounded-xl shadow-xl text-white text-xs font-bold ${toast.type === 'error' ? 'bg-red-600' : 'bg-brand-600'}`}>
          {toast.msg}
        </div>
      )}

      {/* Cột Trái Đồng bộ Phong Cách Trang Index - Tự Co Giãn Vừa Màn Hình Không Scroll */}
      <div className="lg:col-span-6 bg-gradient-to-br from-sky-100/75 via-white to-emerald-50/75 p-5 sm:p-7 lg:p-8 xl:p-11 flex flex-col justify-center relative overflow-hidden lg:h-full border-b lg:border-b-0 lg:border-r border-sky-100">
        <div className="absolute -top-24 -left-24 w-80 h-80 bg-sky-200/40 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 -right-24 w-80 h-80 bg-emerald-200/35 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 w-full max-w-xl mx-auto lg:h-full lg:max-h-[680px] flex flex-col justify-between gap-3">
          <div className="shrink-0">
            <div className="flex flex-wrap items-center justify-between gap-2.5 mb-3.5 xl:mb-4">
              <div onClick={onGoHome} className="inline-flex items-center gap-2.5 cursor-pointer group shrink-0">
                <BrandLogo sizeClass="w-10 h-10" className="shadow-brand-500/20 group-hover:scale-105 transition-transform" />
                <div className="flex items-baseline leading-none">
                  <span className="text-xl lg:text-2xl font-bold tracking-tight text-slate-900">EcoLogix</span>
                  <span className="text-xl lg:text-2xl font-extrabold text-brand-600 ml-1">AI</span>
                </div>
              </div>

              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-100/80 border border-emerald-300 text-brand-800 text-[11px] font-semibold tracking-wide shadow-sm whitespace-nowrap shrink-0">
                <span className="w-2 h-2 rounded-full bg-brand-500 pulse-dot"></span>
                <span>Nền tảng Multi-Agent AI Chuỗi cung ứng Xanh</span>
              </div>
            </div>

            <h1 className="text-2xl sm:text-3xl xl:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight mb-2 xl:mb-3">
              Quản trị chuỗi cung ứng &<br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-emerald-500">Logistics xanh</span> cho SMEs
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 mb-3 leading-relaxed">
              Dự báo thông minh • Lộ trình tối ưu né giờ cấm tải • Báo cáo phát thải CO₂ chuẩn GHG Protocol Scope 1.
            </p>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] sm:text-xs text-slate-500 font-medium mb-3 xl:mb-4">
              <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Dùng thử miễn phí 14 ngày</div>
              <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Xác thực Token & RBAC</div>
              <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Hỗ trợ kỹ thuật 24/7</div>
            </div>

            <div className="bg-white/90 backdrop-blur-sm border border-sky-100 rounded-2xl p-3 xl:p-3.5 text-xs text-slate-700 space-y-1.5 shadow-card">
              <div className="font-extrabold text-brand-800 flex items-center gap-2"><i className="fa-solid fa-key text-brand-600"></i> Đăng nhập nhanh Tài khoản Demo (SQLite):</div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-0.5">
                {[
                  { role: 'Manager', email: 'nguyen.van.a@ecologix.vn', desc: 'Toàn quyền vận hành' },
                  { role: 'Dispatcher', email: 'thuy.nguyen@abc.com', desc: 'Điều phối & Kho' },
                  { role: 'Auditor', email: 'tuan.tran@ecologix.vn', desc: 'Kiểm toán ESG' },
                ].map((acc) => (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => submitLogin(null, acc.email, 'password123')}
                    className="text-left p-2 rounded-xl bg-sky-50/70 hover:bg-emerald-50 border border-sky-100 hover:border-brand-300 transition"
                  >
                    <div className="font-extrabold text-brand-700 text-[11px] sm:text-xs">{acc.role} →</div>
                    <div className="text-[10px] text-slate-500 truncate">{acc.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex-1 min-h-0 lg:min-h-[72px] max-h-[220px] hidden sm:block">
            <img src="https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=900" alt="EcoLogix Smart Fleet" className="w-full h-full object-cover rounded-2xl shadow-xl border-2 border-white" />
          </div>
        </div>
      </div>

      {/* Cột Phải Form - Cố Định Vị Trí Hàng Nút Điều Hướng & Khung Tự Scale */}
      <div className="lg:col-span-6 bg-white p-5 sm:p-7 lg:p-8 xl:p-10 flex items-center justify-center lg:h-full lg:overflow-hidden">
        <div className="w-full max-w-lg min-h-[540px] lg:min-h-0 lg:h-[560px] lg:max-h-full flex flex-col justify-between">
          {/* Hàng nút chế độ & Về trang chủ luôn cố định vị trí */}
          <div className="shrink-0 flex flex-wrap sm:flex-nowrap items-center justify-between gap-2 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-1 bg-slate-100/90 p-1 rounded-full border border-slate-200/80 shrink-0">
              <button type="button" onClick={() => switchMode('login')} className={`whitespace-nowrap text-xs font-bold px-3 sm:px-3.5 py-1.5 rounded-full transition ${mode === 'login' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>Đăng nhập</button>
              <button type="button" onClick={() => switchMode('register')} className={`whitespace-nowrap text-xs font-bold px-3 sm:px-3.5 py-1.5 rounded-full transition ${mode === 'register' || mode === 'verify' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>Đăng ký</button>
              <button type="button" onClick={() => switchMode('forgot')} className={`whitespace-nowrap text-xs font-bold px-3 sm:px-3.5 py-1.5 rounded-full transition ${mode === 'forgot' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>Quên MK</button>
            </div>
            <button type="button" onClick={onGoHome} className="whitespace-nowrap shrink-0 px-3 sm:px-3.5 py-1.5 rounded-full border border-brand-600 text-brand-700 font-semibold text-xs hover:bg-brand-50 transition-all">← Về trang chủ</button>
          </div>

          {/* Nội dung Form ở giữa không làm xê dịch thanh trên & dưới */}
          <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-gutter:stable] py-4 pr-0.5 flex flex-col justify-start">
            {errorMsg && (
              <div className="mb-3 px-4 py-2.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-semibold flex items-center gap-2 shrink-0">
                <i className="fa-solid fa-circle-exclamation"></i>
                <span>{errorMsg}</span>
              </div>
            )}

            {mode === 'login' && (
              <form onSubmit={submitLogin} className="space-y-3.5">
                <div>
                  <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 m-0">Đăng nhập hệ thống</h3>
                  <p className="text-xs text-slate-500 mt-1">Chào mừng trở lại với không gian điều hành EcoLogix AI</p>
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Email doanh nghiệp</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full text-sm px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Mật khẩu</label>
                  <div className="relative">
                    <input type={showPw ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} className="w-full text-sm pl-4 pr-11 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
                    <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 text-xs px-1.5 py-1">
                      <i className={`fa-regular ${showPw ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <label className="flex items-center gap-2 text-slate-600 cursor-pointer"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="text-brand-600 rounded" /> Ghi nhớ phiên đăng nhập</label>
                  <button type="button" onClick={() => switchMode('forgot')} className="text-brand-600 font-bold hover:underline">Quên mật khẩu?</button>
                </div>
                <button disabled={loading} type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl disabled:opacity-60 text-white py-3 rounded-full font-bold text-sm shadow-lg shadow-brand-500/25 transition">
                  {loading ? '⏳ Đang xác thực...' : 'Đăng nhập ngay'}
                </button>
                <div className="text-center text-xs text-slate-500 pt-1">Hoặc đăng nhập nhanh (OAuth Demo)</div>
                <div className="grid grid-cols-2 gap-3">
                  <button type="button" disabled={loading} onClick={() => submitLogin(null, 'nguyen.van.a@ecologix.vn', 'password123')} className="border border-slate-200 rounded-full py-2 text-xs font-bold hover:bg-slate-50 flex items-center justify-center gap-2 transition"><i className="fa-brands fa-google text-red-500"></i> Google (Demo)</button>
                  <button type="button" disabled={loading} onClick={() => submitLogin(null, 'thuy.nguyen@abc.com', 'password123')} className="border border-slate-200 rounded-full py-2 text-xs font-bold hover:bg-slate-50 flex items-center justify-center gap-2 transition"><i className="fa-brands fa-microsoft text-blue-500"></i> Microsoft (Demo)</button>
                </div>
              </form>
            )}

            {mode === 'register' && (
              <form onSubmit={submitRegister} className="space-y-3">
                <div>
                  <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 m-0">Đăng ký tài khoản mới</h3>
                  <p className="text-xs text-slate-500 mt-1">Tạo tài khoản nhân sự & phân quyền vận hành trên SQLite</p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <input value={regName} onChange={(e) => setRegName(e.target.value)} placeholder="Họ và tên *" className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
                  <input value={regCompany} onChange={(e) => setRegCompany(e.target.value)} placeholder="Tên doanh nghiệp (tùy chọn)" className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" />
                </div>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email doanh nghiệp *" className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <input value={regPhone} onChange={(e) => setRegPhone(e.target.value)} placeholder="Số điện thoại (9–13 số)" className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" />
                  <select value={regRole} onChange={(e) => setRegRole(e.target.value)} className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none">
                    <option value="Manager">Manager (Quản lý vận hành)</option>
                    <option value="Dispatcher">Dispatcher (Điều phối xe)</option>
                    <option value="Auditor">Auditor (Kiểm toán ESG)</option>
                  </select>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div className="relative">
                    <input type={showRegPw ? 'text' : 'password'} value={regPassword} onChange={(e) => setRegPassword(e.target.value)} placeholder="Mật khẩu (>= 6 ký tự) *" className="w-full text-sm pl-3.5 pr-9 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
                    <button type="button" onClick={() => setShowRegPw(!showRegPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 text-xs px-1">
                      <i className={`fa-regular ${showRegPw ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                    </button>
                  </div>
                  <input type={showRegPw ? 'text' : 'password'} value={regConfirmPw} onChange={(e) => setRegConfirmPw(e.target.value)} placeholder="Xác nhận mật khẩu *" className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
                </div>
                <button disabled={loading} type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl disabled:opacity-60 text-white py-3 rounded-full text-sm font-bold shadow-lg shadow-brand-500/25 transition">
                  {loading ? '⏳ Đang gửi OTP qua Email...' : 'Đăng ký & Nhận mã OTP'}
                </button>
              </form>
            )}

            {mode === 'verify' && (
              <form onSubmit={submitVerify} className="space-y-3.5">
                <div>
                  <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 m-0">Xác thực tài khoản OTP</h3>
                  <p className="text-xs text-slate-500 mt-1">Email kích hoạt: <strong>{email}</strong></p>
                </div>
                {emailSentInfo && (
                  <div className="p-3 rounded-2xl bg-sky-50 border border-sky-200 text-xs text-sky-900">
                    📧 {emailSentInfo}
                  </div>
                )}
                {demoOtpHint && (
                  <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-brand-900">
                    🔐 <strong>Mã OTP (Demo):</strong> <span className="font-mono font-extrabold text-sm ml-1">{demoOtpHint}</span>
                  </div>
                )}
                <input value={otp} onChange={(e) => setOtp(e.target.value)} placeholder="Nhập mã OTP 6 số từ email *" className="w-full text-sm px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 font-mono outline-none" required />
                <div className="flex gap-2">
                  <button disabled={loading} type="submit" className="flex-1 bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl disabled:opacity-60 text-white py-3 rounded-full text-sm font-bold shadow-lg shadow-brand-500/25 transition">Xác thực tài khoản</button>
                  <button disabled={loading} type="button" onClick={handleResendOtp} className="px-4 py-3 rounded-full border border-sky-200 hover:bg-sky-50 text-sky-700 text-xs font-bold transition whitespace-nowrap">Gửi lại OTP</button>
                </div>
                <button type="button" onClick={() => switchMode('register')} className="text-xs text-slate-500 hover:text-brand-600 font-semibold">← Quay lại chỉnh sửa thông tin đăng ký</button>
              </form>
            )}

            {mode === 'forgot' && (
              <form onSubmit={submitReset} className="space-y-3.5">
                <div>
                  <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 m-0">Khôi phục mật khẩu</h3>
                  <p className="text-xs text-slate-500 mt-1">Nhận mã xác nhận qua Gmail và đặt lại mật khẩu truy cập mới</p>
                </div>
                <div className="flex gap-2">
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email đăng ký" className="flex-1 text-sm px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 outline-none" required />
                  <button disabled={loading} type="button" onClick={requestReset} className="px-5 py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 disabled:opacity-60 text-white text-xs font-bold transition whitespace-nowrap">
                    {loading ? 'Đang gửi...' : 'Gửi mã Email'}
                  </button>
                </div>
                {emailSentInfo && (
                  <div className="p-3 rounded-2xl bg-sky-50 border border-sky-200 text-xs text-sky-900">
                    📧 {emailSentInfo}
                  </div>
                )}
                {demoTokenHint && (
                  <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-brand-900">
                    🔑 <strong>Mã khôi phục (Demo):</strong> <span className="font-mono font-extrabold">{demoTokenHint}</span>
                  </div>
                )}
                <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Mã khôi phục (RST-...)" className="w-full text-sm px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 font-mono outline-none" required />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div className="relative">
                    <input type={showNewPw ? 'text' : 'password'} value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder="Mật khẩu mới (>= 6 ký tự) *" className="w-full text-sm pl-3.5 pr-9 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 outline-none" required />
                    <button type="button" onClick={() => setShowNewPw(!showNewPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 text-xs px-1">
                      <i className={`fa-regular ${showNewPw ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                    </button>
                  </div>
                  <input type={showNewPw ? 'text' : 'password'} value={confirmNewPw} onChange={(e) => setConfirmNewPw(e.target.value)} placeholder="Xác nhận MK mới *" className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50/70 outline-none" required />
                </div>
                <button disabled={loading} type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl disabled:opacity-60 text-white py-3 rounded-full text-sm font-bold shadow-lg shadow-brand-500/25 transition">Đặt lại mật khẩu</button>
              </form>
            )}
          </div>

          <div className="shrink-0 text-center text-xs text-slate-500 pt-3 border-t border-slate-100">
            Doanh nghiệp mới? <button type="button" onClick={onGoOnboarding} className="text-brand-600 font-bold hover:underline">Thiết lập Onboarding 3 bước →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { LoginView });
