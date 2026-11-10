const { useState, useEffect, useRef, useMemo } = React;

// ==================== 2. LOGIN / REGISTER / VERIFY / RESET VIEW ====================
function LoginView({ onLoginSuccess, onGoOnboarding, onGoHome, toast, showToast, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('nguyen.van.a@ecologix.vn');
  const [password, setPassword] = useState('password123');
  const [remember, setRemember] = useState(true);
  const [regName, setRegName] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regRole, setRegRole] = useState('Manager');
  const [otp, setOtp] = useState('');
  const [token, setToken] = useState('');
  const [newPw, setNewPw] = useState('');

  const submitLogin = async (e, overrideEmail, overridePw) => {
    if (e) e.preventDefault();
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: overrideEmail || email, password: overridePw || password }),
      });
      onLoginSuccess(res.user, remember);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const submitRegister = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name: regName, email, password, phone: regPhone, role: regRole }),
      });
      showToast(res.message);
      setOtp(res.demo_otp || '');
      setMode('verify');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const submitVerify = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/auth/verify', { method: 'POST', body: JSON.stringify({ email, otp_code: otp }) });
      showToast(res.message);
      setMode('login');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const requestReset = async () => {
    try {
      const res = await apiFetch('/api/auth/forgot', { method: 'POST', body: JSON.stringify({ email }) });
      showToast(res.message);
      setToken(res.demo_token || '');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/auth/reset', { method: 'POST', body: JSON.stringify({ email, token, new_password: newPw }) });
      showToast(res.message);
      setMode('login');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="min-h-screen w-full grid grid-cols-1 lg:grid-cols-12 bg-white">
      {toast && <div className={`fixed top-5 right-5 z-50 px-5 py-3 rounded-xl shadow-xl text-white text-xs font-bold ${toast.type === 'error' ? 'bg-red-600' : 'bg-brand-600'}`}>{toast.msg}</div>}

      {/* Cột Trái Đồng bộ Phong Cách Trang Index Full Height & Width */}
      <div className="lg:col-span-6 bg-gradient-to-br from-sky-100/75 via-white to-emerald-50/75 p-8 sm:p-12 lg:p-14 xl:p-16 flex flex-col justify-between relative overflow-hidden lg:min-h-screen border-b lg:border-b-0 lg:border-r border-sky-100">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-sky-200/40 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-emerald-200/35 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-xl">
          <div onClick={onGoHome} className="inline-flex items-center gap-3 mb-7 cursor-pointer group">
            <BrandLogo sizeClass="w-11 h-11" className="shadow-brand-500/20 group-hover:scale-105 transition-transform" />
            <div className="flex items-baseline">
              <span className="text-2xl font-bold tracking-tight text-slate-900">EcoLogix</span>
              <span className="text-2xl font-extrabold text-brand-600 ml-1">AI</span>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-100/80 border border-emerald-300 text-brand-800 text-xs font-semibold tracking-wide shadow-sm mb-4">
            <span className="w-2 h-2 rounded-full bg-brand-500 pulse-dot"></span>
            <span>Nền tảng Multi-Agent AI Chuỗi cung ứng Xanh</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight mb-4">
            Quản trị chuỗi cung ứng &<br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-emerald-500">Logistics xanh</span> cho SMEs
          </h1>
          <p className="text-sm text-slate-600 mb-5 leading-relaxed">
            Dự báo thông minh • Lộ trình tối ưu né giờ cấm tải • Báo cáo phát thải CO₂ chuẩn GHG Protocol Scope 1.
          </p>

          <div className="flex flex-wrap items-center gap-5 text-xs text-slate-500 font-medium mb-6">
            <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Dùng thử miễn phí 14 ngày</div>
            <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Không cần thẻ tín dụng</div>
            <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Hỗ trợ kỹ thuật 24/7</div>
          </div>

          <div className="bg-white/90 backdrop-blur-sm border border-sky-100 rounded-2xl p-4 text-xs text-slate-700 space-y-1.5 shadow-card">
            <div className="font-extrabold text-brand-800 flex items-center gap-2"><i className="fa-solid fa-key text-brand-600"></i> Tài khoản Demo trong SQLite:</div>
            <div className="flex flex-wrap justify-between gap-1"><span>• Manager:</span><code className="bg-slate-100 px-1.5 py-0.5 rounded">nguyen.van.a@ecologix.vn / password123</code></div>
            <div className="flex flex-wrap justify-between gap-1"><span>• Dispatcher:</span><code className="bg-slate-100 px-1.5 py-0.5 rounded">thuy.nguyen@abc.com / password123</code></div>
            <div className="flex flex-wrap justify-between gap-1"><span>• Auditor:</span><code className="bg-slate-100 px-1.5 py-0.5 rounded">tuan.tran@ecologix.vn / password123</code></div>
          </div>
        </div>

        <div className="relative z-10 mt-8">
          <img src="https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=900" alt="EcoLogix Smart Fleet" className="w-full h-48 sm:h-60 xl:h-64 object-cover rounded-2xl shadow-xl border-2 border-white" />
        </div>
      </div>

      {/* Cột Phải Form Full Height & Width */}
      <div className="lg:col-span-6 bg-white p-6 sm:p-12 lg:p-16 flex flex-col justify-center lg:min-h-screen">
        <div className="w-full max-w-lg mx-auto">
          <div className="flex flex-wrap justify-between items-center gap-3 mb-7">
            <div className="flex gap-1.5 bg-slate-100/80 p-1 rounded-full border border-slate-200/80">
              <button onClick={() => setMode('login')} className={`text-xs font-bold px-4 py-2 rounded-full transition ${mode === 'login' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>Đăng nhập</button>
              <button onClick={() => setMode('register')} className={`text-xs font-bold px-4 py-2 rounded-full transition ${mode === 'register' || mode === 'verify' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>Đăng ký</button>
              <button onClick={() => setMode('forgot')} className={`text-xs font-bold px-4 py-2 rounded-full transition ${mode === 'forgot' ? 'bg-gradient-to-r from-brand-600 to-emerald-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>Quên MK</button>
            </div>
            <button onClick={onGoHome} className="px-3.5 py-1.5 rounded-full border border-brand-600 text-brand-700 font-semibold text-xs hover:bg-brand-50 transition-all">← Về trang chủ</button>
          </div>

          {mode === 'login' && (
            <form onSubmit={submitLogin} className="space-y-4">
              <div>
                <h3 className="text-2xl font-extrabold text-slate-900 m-0">Đăng nhập hệ thống</h3>
                <p className="text-xs text-slate-500 mt-1">Chào mừng trở lại với không gian điều hành EcoLogix AI</p>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1.5">Email doanh nghiệp</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1.5">Mật khẩu</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600 outline-none" required />
              </div>
              <div className="flex justify-between items-center text-xs pt-1">
                <label className="flex items-center gap-2 text-slate-600 cursor-pointer"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="text-brand-600 rounded" /> Ghi nhớ phiên đăng nhập</label>
                <button type="button" onClick={() => setMode('forgot')} className="text-brand-600 font-bold hover:underline">Quên mật khẩu?</button>
              </div>
              <button type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl text-white py-3.5 rounded-full font-bold text-sm shadow-lg shadow-brand-500/25 transition">Đăng nhập ngay</button>
              <div className="text-center text-xs text-slate-500 pt-2">Hoặc đăng nhập nhanh (OAuth Demo)</div>
              <div className="grid grid-cols-2 gap-3">
                <button type="button" onClick={() => submitLogin(null, 'nguyen.van.a@ecologix.vn', 'password123')} className="border border-slate-200 rounded-full py-2.5 text-xs font-bold hover:bg-slate-50 flex items-center justify-center gap-2 transition"><i className="fa-brands fa-google text-red-500"></i> Google (Demo)</button>
                <button type="button" onClick={() => submitLogin(null, 'thuy.nguyen@abc.com', 'password123')} className="border border-slate-200 rounded-full py-2.5 text-xs font-bold hover:bg-slate-50 flex items-center justify-center gap-2 transition"><i className="fa-brands fa-microsoft text-blue-500"></i> Microsoft (Demo)</button>
              </div>
            </form>
          )}

          {mode === 'register' && (
            <form onSubmit={submitRegister} className="space-y-3.5">
              <div>
                <h3 className="text-2xl font-extrabold text-slate-900 m-0">Đăng ký tài khoản mới</h3>
                <p className="text-xs text-slate-500 mt-1">Tạo tài khoản nhân sự & phân quyền vận hành trên SQLite</p>
              </div>
              <input value={regName} onChange={(e) => setRegName(e.target.value)} placeholder="Họ và tên *" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600" required />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email doanh nghiệp *" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600" required />
              <input value={regPhone} onChange={(e) => setRegPhone(e.target.value)} placeholder="Số điện thoại" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600" />
              <select value={regRole} onChange={(e) => setRegRole(e.target.value)} className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600">
                <option value="Manager">Manager (Quản lý vận hành)</option>
                <option value="Dispatcher">Dispatcher (Điều phối xe)</option>
                <option value="Auditor">Auditor (Kiểm toán ESG)</option>
              </select>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Mật khẩu (>= 6 ký tự) *" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-brand-600" required />
              <button type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl text-white py-3.5 rounded-full text-sm font-bold shadow-lg shadow-brand-500/25 transition">Đăng ký tài khoản</button>
            </form>
          )}

          {mode === 'verify' && (
            <form onSubmit={submitVerify} className="space-y-4">
              <h3 className="text-2xl font-extrabold text-slate-900 m-0">Xác thực tài khoản OTP</h3>
              <p className="text-xs text-slate-500">Nhập mã OTP 6 số hiển thị trên thông báo để kích hoạt tài khoản:</p>
              <input value={otp} onChange={(e) => setOtp(e.target.value)} placeholder="Mã OTP 6 số *" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 font-mono" required />
              <button type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl text-white py-3.5 rounded-full text-sm font-bold shadow-lg shadow-brand-500/25 transition">Xác thực tài khoản</button>
            </form>
          )}

          {mode === 'forgot' && (
            <form onSubmit={submitReset} className="space-y-4">
              <div>
                <h3 className="text-2xl font-extrabold text-slate-900 m-0">Khôi phục mật khẩu</h3>
                <p className="text-xs text-slate-500 mt-1">Nhận mã xác nhận và đặt lại mật khẩu truy cập mới</p>
              </div>
              <div className="flex gap-2">
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email đăng ký" className="flex-1 text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70" />
                <button type="button" onClick={requestReset} className="px-5 py-3 rounded-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition">Lấy mã</button>
              </div>
              <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Mã khôi phục (RST-...)" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70 font-mono" required />
              <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder="Mật khẩu mới *" className="w-full text-sm px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/70" required />
              <button type="submit" className="w-full bg-gradient-to-r from-brand-600 to-emerald-500 hover:shadow-xl text-white py-3.5 rounded-full text-sm font-bold shadow-lg shadow-brand-500/25 transition">Đặt lại mật khẩu</button>
            </form>
          )}

          <div className="text-center text-xs text-slate-500 mt-6 pt-5 border-t border-slate-100">
            Doanh nghiệp mới? <button onClick={onGoOnboarding} className="text-brand-600 font-bold hover:underline">Thiết lập Onboarding 3 bước →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { LoginView });
