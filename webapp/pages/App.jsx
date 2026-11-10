const { useState, useEffect, useRef, useMemo } = React;

const PAGE_PATHS = {
  landing: '/',
  login: '/login',
  register: '/register',
  onboarding: '/onboarding',
  dashboard: '/dashboard',
  inventory: '/inventory',
  forecasting: '/forecasting',
  orders: '/orders',
  routing: '/routing',
  vehicles: '/vehicles',
  partners: '/partners',
  ai_assistant: '/ai-assistant',
  reports: '/reports',
  notifications: '/notifications',
  settings: '/settings',
};

function resolveInitialRoute() {
  const path = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
  if (path === '/register') return { page: 'login', loginMode: 'register' };
  const entry = Object.entries(PAGE_PATHS).find(([, p]) => p === path);
  if (entry) return { page: entry[0], loginMode: 'login' };
  if (path === '/ai_assistant') return { page: 'ai_assistant', loginMode: 'login' };
  return { page: 'landing', loginMode: 'login' };
}

// ==================== MAIN APP ====================
function App() {
  const initRoute = resolveInitialRoute();
  const [currentPage, setCurrentPageState] = useState(initRoute.page);
  const [loginMode, setLoginMode] = useState(initRoute.loginMode);
  const setCurrentPage = (page, opts = {}) => {
    if (page === 'register') {
      setLoginMode('register');
      setCurrentPageState('login');
      if (!opts.skipHistory && window.location.pathname !== '/register') {
        window.history.pushState({ page: 'register' }, '', '/register');
      }
      return;
    }
    if (page === 'login' && opts.mode) setLoginMode(opts.mode);
    else if (page === 'login') setLoginMode('login');
    setCurrentPageState(page);
    const targetUrl = PAGE_PATHS[page] || '/';
    if (!opts.skipHistory && window.location.pathname !== targetUrl) {
      window.history.pushState({ page }, '', targetUrl);
    }
  };
  const [viewMode, setViewMode] = useState('desktop');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('ecologix_user');
      return saved ? JSON.parse(saved) : { id: 1, name: 'Nguyễn Văn A', role: 'Manager', company_name: 'EcoLogix Logistics (SME)', email: 'nguyen.van.a@ecologix.vn' };
    } catch {
      return { id: 1, name: 'Nguyễn Văn A', role: 'Manager', company_name: 'EcoLogix Logistics (SME)' };
    }
  });
  const [unreadCount, setUnreadCount] = useState(3);
  const [searchQ, setSearchQ] = useState('');
  const [searchHits, setSearchHits] = useState([]);
  const [preloadedAiPrompt, setPreloadedAiPrompt] = useState('');

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const refreshHeaderStats = async () => {
    try {
      const d = await apiFetch('/api/dashboard');
      setUnreadCount(d.unread_notifications || 0);
      if (d.company_name) {
        setUser((prev) => ({ ...prev, company_name: d.company_name }));
      }
    } catch {}
  };

  useEffect(() => {
    if (!['landing', 'login', 'onboarding'].includes(currentPage)) {
      refreshHeaderStats();
    }
  }, [currentPage]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!searchQ.trim()) {
        setSearchHits([]);
        return;
      }
      try {
        const res = await apiFetch(`/api/search?q=${encodeURIComponent(searchQ)}`);
        setSearchHits(res.results || []);
      } catch {}
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQ]);

  useEffect(() => {
    const onPop = () => {
      const r = resolveInitialRoute();
      setLoginMode(r.loginMode);
      setCurrentPageState(r.page);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [currentPage]);

  const handleLoginSuccess = (u, remember) => {
    setUser(u);
    if (remember) {
      localStorage.setItem('ecologix_user', JSON.stringify(u));
    }
    setCurrentPage('dashboard');
    showToast(`Đăng nhập thành công! Xin chào ${u.name} (${u.role})`);
  };

  const handleLogout = () => {
    localStorage.removeItem('ecologix_user');
    setCurrentPage('login');
    showToast('Đã đăng xuất an toàn.', 'info');
  };

  const openAiWithPrompt = (promptText) => {
    setPreloadedAiPrompt(promptText);
    setCurrentPage('ai_assistant');
  };

  if (currentPage === 'landing') {
    return (
      <LandingView
        user={user}
        toast={toast}
        showToast={showToast}
        onLogin={() => setCurrentPage('login')}
        onRegister={() => setCurrentPage('onboarding')}
        onOnboardingComplete={(newComp) => {
          setUser((p) => ({ ...p, company_name: newComp }));
          setCurrentPage('dashboard');
          showToast('Thiết lập doanh nghiệp hoàn tất! Đã lưu vào SQLite & config.py.');
        }}
        onGoApp={(page = 'dashboard') => setCurrentPage(page)}
        onAskAi={openAiWithPrompt}
      />
    );
  }

  if (currentPage === 'login') {
    return (
      <LoginView
        key={loginMode}
        initialMode={loginMode}
        showToast={showToast}
        toast={toast}
        onLoginSuccess={handleLoginSuccess}
        onGoOnboarding={() => setCurrentPage('onboarding')}
        onGoHome={() => setCurrentPage('landing')}
      />
    );
  }

  if (currentPage === 'onboarding') {
    return (
      <OnboardingView
        user={user}
        showToast={showToast}
        toast={toast}
        onGoLogin={() => setCurrentPage('login')}
        onFinish={(newComp) => {
          setUser((p) => ({ ...p, company_name: newComp }));
          setCurrentPage('dashboard');
          showToast('Thiết lập doanh nghiệp hoàn tất! Đã lưu vào SQLite & config.py.');
        }}
        onBack={() => setCurrentPage('landing')}
      />
    );
  }

  if (viewMode === 'mobile_demo') {
    return <MobileDemoView onBackDesktop={() => setViewMode('desktop')} />;
  }

  const NAV_ITEMS = [
    { id: 'dashboard', name: 'Tổng quan', icon: 'fa-solid fa-grip', boxCls: 'bg-emerald-50 border-emerald-200/80', iconCls: 'text-emerald-600' },
    { id: 'inventory', name: 'Quản lý kho & SKU', icon: 'fa-solid fa-warehouse', boxCls: 'bg-amber-50 border-amber-200/80', iconCls: 'text-amber-600' },
    { id: 'forecasting', name: 'Dự báo nhu cầu', icon: 'fa-solid fa-chart-pie', boxCls: 'bg-sky-50 border-sky-200/80', iconCls: 'text-sky-600' },
    { id: 'orders', name: 'Quản lý đơn hàng', icon: 'fa-solid fa-cart-shopping', boxCls: 'bg-indigo-50 border-indigo-200/80', iconCls: 'text-indigo-600' },
    { id: 'routing', name: 'Tối ưu lộ trình', icon: 'fa-solid fa-map-location-dot', boxCls: 'bg-teal-50 border-teal-200/80', iconCls: 'text-teal-600' },
    { id: 'vehicles', name: 'Quản lý đội xe', icon: 'fa-solid fa-truck-fast', boxCls: 'bg-blue-50 border-blue-200/80', iconCls: 'text-blue-600' },
    { id: 'partners', name: 'Khách hàng & NCC', icon: 'fa-solid fa-users', boxCls: 'bg-purple-50 border-purple-200/80', iconCls: 'text-purple-600' },
    { id: 'ai_assistant', name: 'Trợ lý AI', icon: 'fa-solid fa-robot', boxCls: 'bg-cyan-50 border-cyan-200/80', iconCls: 'text-cyan-600' },
    { id: 'reports', name: 'Báo cáo & ESG', icon: 'fa-solid fa-file-invoice', boxCls: 'bg-lime-50 border-lime-200/80', iconCls: 'text-lime-700' },
    { id: 'notifications', name: 'Thông báo', icon: 'fa-solid fa-bell', boxCls: 'bg-rose-50 border-rose-200/80', iconCls: 'text-rose-600' },
    { id: 'settings', name: 'Cài đặt & Live-Code', icon: 'fa-solid fa-gear', boxCls: 'bg-slate-100 border-slate-200/90', iconCls: 'text-slate-700' },
  ];

  const PAGE_TITLES = {
    dashboard: 'Tổng quan',
    inventory: 'Quản lý kho & SKU',
    forecasting: 'Dự báo nhu cầu (LightGBM)',
    orders: 'Quản lý đơn hàng',
    routing: 'Tối ưu lộ trình (Green VRP)',
    vehicles: 'Quản lý đội xe',
    partners: 'Khách hàng & Nhà cung cấp',
    ai_assistant: 'Trợ lý Multi-Agent AI',
    reports: 'Báo cáo Tài chính & ESG',
    notifications: 'Trung tâm thông báo',
    settings: 'Cài đặt hệ thống & Live-Code',
  };

  return (
    <div className="flex min-h-screen eco-sky-canvas">
      {toast && (
        <div className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-xl text-white text-xs font-bold ${toast.type === 'error' ? 'bg-red-600' : toast.type === 'info' ? 'bg-blue-600' : 'bg-brand-600'}`}>
          <span>{toast.type === 'error' ? '❌' : toast.type === 'info' ? 'ℹ️' : '✅'}</span>
          <span>{toast.msg}</span>
        </div>
      )}

      {mobileSidebarOpen && (
        <div
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-900/35 backdrop-blur-xs lg:hidden"
        />
      )}

      {/* SIDEBAR LIGHT SKY-EMERALD GLASS (ĐỒNG BỘ PHONG CÁCH INDEX) */}
      <aside className={`${mobileSidebarOpen ? 'fixed inset-y-0 left-0 z-40 flex' : 'hidden lg:flex'} w-[268px] eco-sidebar-surface border-r border-sky-200/80 text-slate-700 flex-col justify-between p-4 sticky top-0 h-screen flex-shrink-0 shadow-[4px_0_30px_-10px_rgba(14,165,233,0.14)] overflow-y-auto custom-scrollbar`}>
        <div>
          <div onClick={() => setCurrentPage('landing')} className="flex items-center gap-3 px-3 py-3 border-b border-sky-100 mb-4 cursor-pointer rounded-2xl hover:bg-white/80 hover:shadow-[0_0_16px_rgba(16,185,129,0.16)] transition-all group">
            <BrandLogo sizeClass="w-10 h-10" className="shadow-brand-500/20 group-hover:scale-105 transition-transform" />
            <div>
              <div className="flex items-baseline">
                <span className="font-bold text-lg tracking-tight text-slate-900">EcoLogix</span>
                <span className="font-extrabold text-lg text-brand-600 ml-1">AI</span>
              </div>
              <p className="text-[10px] text-brand-700 font-bold m-0">Smart Logistics. Greener Future.</p>
            </div>
          </div>

          <nav className="space-y-1.5">
            {NAV_ITEMS.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => { setCurrentPage(item.id); setMobileSidebarOpen(false); }}
                  className={`group w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-bold text-xs ${
                    isActive ? 'eco-nav-item eco-nav-item-active' : 'eco-nav-item text-slate-600'
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <span className={`w-7 h-7 rounded-lg border flex items-center justify-center transition-all group-hover:scale-110 ${isActive ? 'bg-white/95 border-white shadow-sm' : item.boxCls}`}>
                      <i className={`${item.icon} text-xs ${item.iconCls}`}></i>
                    </span>
                    <span>{item.name}</span>
                  </span>
                  {item.id === 'notifications' && unreadCount > 0 && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-extrabold ${isActive ? 'bg-white text-brand-700' : 'bg-amber-100 text-amber-800 border border-amber-200'}`}>{unreadCount}</span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="space-y-3 pt-4">
          <div className="eco-card-glow bg-gradient-to-br from-sky-50/90 via-white to-emerald-50/90 border border-emerald-200/80 rounded-2xl p-3.5 text-left shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-brand-500 pulse-dot"></span>
              <span className="text-[11px] font-extrabold text-brand-800 uppercase tracking-wider">Chế độ xanh</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed m-0">
              Kết nối dữ liệu thời gian thực SQLite & LightGBM.
            </p>
          </div>

          <div className="pt-2.5 border-t border-sky-100 grid grid-cols-3 gap-1.5 text-[11px]">
            <button onClick={() => setCurrentPage('landing')} className="py-2 rounded-xl bg-white/80 border border-sky-100 hover:border-brand-300 hover:text-brand-700 hover:shadow-[0_0_14px_rgba(16,185,129,0.2)] font-bold text-slate-600 transition">🏠 Chủ</button>
            <button onClick={() => setViewMode('mobile_demo')} className="py-2 rounded-xl bg-white/80 border border-sky-100 hover:border-brand-300 hover:text-brand-700 hover:shadow-[0_0_14px_rgba(56,189,248,0.22)] font-bold text-brand-700 transition">📱 Mobile</button>
            <button onClick={handleLogout} className="py-2 rounded-xl bg-white/80 border border-sky-100 hover:border-red-300 hover:text-red-600 hover:shadow-[0_0_14px_rgba(239,68,68,0.18)] font-bold text-slate-600 transition">🚪 Thoát</button>
          </div>
        </div>
      </aside>

      {/* MAIN WORKSPACE */}
      <main className="flex-1 min-w-0 p-4 sm:p-7">
        <header className="flex flex-wrap justify-between items-center gap-3 bg-white/85 backdrop-blur-xl px-6 py-4 rounded-2xl border border-sky-200/75 shadow-[0_8px_30px_-10px_rgba(14,165,233,0.12)] mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)} className="lg:hidden p-2 rounded-xl bg-sky-50 border border-sky-100 text-text-main hover:shadow-[0_0_12px_rgba(16,185,129,0.2)] transition">
              <i className="fa-solid fa-bars"></i>
            </button>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight m-0">{PAGE_TITLES[currentPage]}</h2>
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1 rounded-full bg-emerald-100/80 text-brand-800 border border-emerald-300">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 pulse-dot"></span>
              <span>SQLite Live Sync</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative hidden md:block">
              <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
              <input
                type="text"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Tìm đơn hàng, SKU, xe, khách..."
                className="pl-9 pr-4 py-2 text-xs rounded-full border border-sky-200/80 bg-slate-50/80 focus:bg-white focus:outline-none focus:border-brand-500 focus:shadow-[0_0_16px_rgba(16,185,129,0.2)] w-64 text-text-main transition-all"
              />
              {searchHits.length > 0 && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-2xl shadow-xl border border-sky-100 z-50 p-2 space-y-1">
                  {searchHits.map((h, i) => (
                    <button
                      key={i}
                      onClick={() => { setCurrentPage(h.page); setSearchQ(''); setSearchHits([]); }}
                      className="w-full text-left px-3 py-2 rounded-xl text-xs hover:bg-emerald-50 font-semibold text-text-main flex items-center justify-between transition"
                    >
                      <span className="truncate">{h.label}</span>
                      <span className="text-[10px] text-brand-600 uppercase ml-2">{h.type}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button onClick={() => setCurrentPage('notifications')} className="relative p-2.5 rounded-xl bg-sky-50/80 border border-sky-100 hover:bg-white hover:border-brand-300 hover:shadow-[0_0_14px_rgba(16,185,129,0.22)] transition-all">
              <i className="fa-regular fa-bell text-sm text-slate-600"></i>
              {unreadCount > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center shadow-sm">{unreadCount}</span>}
            </button>

            <div className="flex items-center gap-2.5 pl-3 border-l border-sky-100">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-sky-100 to-emerald-100 border border-emerald-200 text-brand-700 flex items-center justify-center text-xs font-bold shadow-sm">
                {(user.name || 'NV').slice(0, 2).toUpperCase()}
              </div>
              <div className="leading-tight hidden sm:block">
                <div className="font-bold text-xs text-slate-900">{user.name} <span className="text-[10px] bg-emerald-100/80 text-brand-800 border border-emerald-200 px-1.5 py-0.5 rounded-full">{user.role}</span></div>
                <div className="text-[11px] text-slate-500 font-medium truncate max-w-[160px]">{user.company_name}</div>
              </div>
            </div>
          </div>
        </header>

        {currentPage === 'dashboard' && <DashboardView onNavigate={setCurrentPage} showToast={showToast} />}
        {currentPage === 'inventory' && <InventoryView showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
        {currentPage === 'forecasting' && <ForecastingView showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
        {currentPage === 'orders' && <OrdersView showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
        {currentPage === 'routing' && <RoutingView showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
        {currentPage === 'vehicles' && <VehiclesView showToast={showToast} />}
        {currentPage === 'partners' && <PartnersView showToast={showToast} />}
        {currentPage === 'ai_assistant' && <AiAssistantView user={user} preloadedPrompt={preloadedAiPrompt} clearPreloaded={() => setPreloadedAiPrompt('')} onNavigate={setCurrentPage} showToast={showToast} />}
        {currentPage === 'reports' && <ReportsView showToast={showToast} />}
        {currentPage === 'notifications' && <NotificationsView onRefreshHeader={refreshHeaderStats} showToast={showToast} />}
        {currentPage === 'settings' && <SettingsView user={user} setUser={setUser} showToast={showToast} />}
      </main>
    </div>
  );
}

Object.assign(window, { App });

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
