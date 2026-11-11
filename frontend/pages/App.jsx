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
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [fleetMenuOpen, setFleetMenuOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('ecologix_dark_mode') === '1');
  const sidebarSearchRef = useRef(null);
  const [toast, setToast] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!(typeof getAuthToken === 'function' && getAuthToken()));
  const [user, setUser] = useState(() => {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    const saved = typeof getStoredUser === 'function' ? getStoredUser() : null;
    if (token && saved) return saved;
    return { id: 1, name: 'Nguyễn Văn A', role: 'Manager', company_name: '', has_company: false, email: 'nguyen.van.a@ecologix.vn' };
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
    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    if (!token) return;
    apiFetch('/api/auth/me')
      .then((res) => {
        if (res && res.user) {
          setUser(res.user);
          const remembered = !!localStorage.getItem('ecologix_token');
          saveAuthSession(res.user, token, remembered);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      clearAuthSession();
      setCurrentPage('login');
      showToast('Phiên đăng nhập đã hết hạn hoặc chưa được xác thực.', 'error');
    };
    window.addEventListener('ecologix:unauthorized', onUnauthorized);
    return () => window.removeEventListener('ecologix:unauthorized', onUnauthorized);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [currentPage]);

  useEffect(() => {
    const onShortcut = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        sidebarSearchRef.current && sidebarSearchRef.current.focus();
      }
    };
    window.addEventListener('keydown', onShortcut);
    return () => window.removeEventListener('keydown', onShortcut);
  }, []);

  const handleLoginSuccess = (u, accessToken = '', remember = true) => {
    setIsAuthenticated(true);
    setUser(u);
    if (typeof saveAuthSession === 'function') {
      saveAuthSession(u, accessToken, remember);
    } else if (remember) {
      localStorage.setItem('ecologix_user', JSON.stringify(u));
    }
    setCurrentPage('dashboard');
    showToast(`Đăng nhập thành công! Xin chào ${u.name} (${u.role})`);
  };

  const handleLogout = async () => {
    try {
      if (typeof getAuthToken === 'function' && getAuthToken()) {
        await apiFetch('/api/auth/logout', { method: 'POST' });
      }
    } catch {}
    if (typeof clearAuthSession === 'function') {
      clearAuthSession();
    } else {
      localStorage.removeItem('ecologix_user');
    }
    setIsAuthenticated(false);
    setUser({ id: 1, name: 'Nguyễn Văn A', role: 'Manager', company_name: '', has_company: false, email: 'nguyen.van.a@ecologix.vn' });
    setCurrentPage('login');
    showToast('Đã đăng xuất an toàn.', 'info');
  };

  const completeOnboardingSession = (newComp, apiRes) => {
    const nextUser = apiRes?.user
      ? { ...user, ...apiRes.user, company_name: newComp, has_company: true }
      : { ...user, company_name: newComp, has_company: true };
    setUser(nextUser);
    if (typeof getAuthToken === 'function' && getAuthToken()) {
      const remembered = !!localStorage.getItem('ecologix_token');
      saveAuthSession(nextUser, getAuthToken(), remembered);
    }
    setCurrentPage('dashboard');
    showToast('Thiết lập doanh nghiệp hoàn tất! Đã lưu vào SQLite & config.py.');
  };

  const openAiWithPrompt = (promptText) => {
    setPreloadedAiPrompt(promptText);
    setCurrentPage('ai_assistant');
  };

  if (currentPage === 'landing') {
    return (
      <LandingView
        user={user}
        isAuthenticated={isAuthenticated}
        toast={toast}
        showToast={showToast}
        onLogin={() => setCurrentPage('login')}
        onRegister={() => setCurrentPage('onboarding')}
        onOnboardingComplete={completeOnboardingSession}
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
        onFinish={completeOnboardingSession}
        onBack={() => setCurrentPage('landing')}
      />
    );
  }

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      localStorage.setItem('ecologix_dark_mode', next ? '1' : '0');
      return next;
    });
  };

  const FLEET_SUBITEMS = [
    { id: 'vehicles', name: 'Tất cả phương tiện' },
    { id: 'routing', name: 'Tối ưu lộ trình VRP' },
    { id: 'forecasting', name: 'Dự báo nhu cầu AI' },
  ];

  const MAIN_MENU_ITEMS = [
    { id: 'orders', name: 'Đơn hàng & Giao nhận', icon: 'fa-solid fa-cube', hasArrow: true },
    { id: 'inventory', name: 'Quản lý Kho & SKU', icon: 'fa-solid fa-warehouse' },
    { id: 'ai_assistant', name: 'Trợ lý Multi-Agent AI', icon: 'fa-solid fa-robot', badge: 6 },
    { id: 'reports', name: 'Báo cáo & ESG', icon: 'fa-solid fa-chart-column' },
  ];

  const SUPPORT_ITEMS = [
    { id: 'partners', name: 'Khách hàng & NCC', icon: 'fa-solid fa-users' },
    { id: 'notifications', name: 'Thông báo hệ thống', icon: 'fa-regular fa-bell', badge: unreadCount },
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
    <div className={`flex min-h-screen ${darkMode ? 'bg-slate-950 text-slate-100' : 'eco-sky-canvas'}`}>
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

      {/* SIDEBAR MINIMALIST CLEAN SAAS (THEO MẪU THAM CHIẾU) */}
      <aside className={`${mobileSidebarOpen ? 'fixed inset-y-0 left-0 z-40 flex' : 'hidden lg:flex'} ${darkMode ? 'eco-dark-sidebar border-slate-800' : 'border-slate-200/80'} w-[min(82vw,272px)] lg:w-[264px] eco-sidebar-surface border-r flex-col justify-between px-4 py-4 sticky top-0 h-[100dvh] flex-shrink-0 overflow-y-auto custom-scrollbar shadow-xl lg:shadow-none`}>
        <div>
          {/* Logo Header */}
          <div onClick={() => setCurrentPage('landing')} className={`flex items-center gap-2.5 px-2 pb-3 mb-3 cursor-pointer border-b ${darkMode ? 'border-slate-800' : 'border-slate-100'} group`}>
            <BrandLogo sizeClass="w-8 h-8" roundedClass="rounded-lg" className="group-hover:scale-105 transition-transform" />
            <div className="flex items-baseline leading-none">
              <span className={`font-bold text-base tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>EcoLogix</span>
              <span className="font-extrabold text-base text-brand-600 ml-1">AI</span>
            </div>
          </div>

          {/* Search box + Shortcut + Sidebar live dropdown */}
          <div className="relative mb-5">
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
            <input
              ref={sidebarSearchRef}
              type="text"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Search.."
              className={`w-full pl-8 pr-14 py-2 text-xs rounded-xl border focus:outline-none focus:border-brand-500 transition ${darkMode ? 'bg-slate-900 border-slate-700 text-slate-200 placeholder-slate-500' : 'bg-white border-slate-200/90 text-slate-700 placeholder-slate-400'}`}
            />
            <span className={`absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-semibold px-1.5 py-0.5 rounded-md border ${darkMode ? 'bg-slate-800 border-slate-700 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>⌘ K</span>
            {searchHits.length > 0 && (
              <div className={`absolute left-0 right-0 mt-1.5 rounded-2xl shadow-xl border z-50 p-1.5 space-y-0.5 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'}`}>
                {searchHits.map((h, i) => (
                  <button
                    key={i}
                    onClick={() => { setCurrentPage(h.page); setSearchQ(''); setSearchHits([]); setMobileSidebarOpen(false); }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-xl text-[11px] font-semibold flex items-center justify-between transition ${darkMode ? 'text-slate-200 hover:bg-slate-800' : 'text-slate-700 hover:bg-emerald-50'}`}
                  >
                    <span className="truncate">{h.label}</span>
                    <span className="text-[9px] text-brand-600 uppercase ml-2">{h.type}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* MAIN MENU */}
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 mb-2">Main Menu</div>
          <nav className="space-y-1">
            <button
              onClick={() => { setCurrentPage('dashboard'); setMobileSidebarOpen(false); }}
              className={`eco-nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-semibold ${
                currentPage === 'dashboard' ? 'eco-nav-item-active' : darkMode ? 'text-slate-300' : 'text-slate-600'
              }`}
            >
              <i className={`fa-solid fa-table-cells-large w-4 text-center text-sm ${currentPage === 'dashboard' ? '' : 'text-slate-400'}`}></i>
              <span>Tổng quan</span>
            </button>

            {/* Expandable Fleet & Dispatch Group */}
            <div>
              <button
                type="button"
                onClick={() => setFleetMenuOpen(!fleetMenuOpen)}
                className={`eco-nav-item w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-[13px] font-semibold ${
                  ['vehicles', 'routing', 'forecasting'].includes(currentPage)
                    ? (darkMode ? 'text-emerald-400' : 'text-slate-900')
                    : (darkMode ? 'text-slate-300' : 'text-slate-600')
                }`}
              >
                <span className="flex items-center gap-3">
                  <i className={`fa-solid fa-truck w-4 text-center text-sm ${['vehicles', 'routing', 'forecasting'].includes(currentPage) ? 'text-brand-600' : 'text-slate-400'}`}></i>
                  <span>Điều hành Đội xe</span>
                </span>
                <i className={`fa-solid ${fleetMenuOpen ? 'fa-chevron-down' : 'fa-chevron-right'} text-[10px] text-slate-400 transition-transform`}></i>
              </button>

              {fleetMenuOpen && (
                <div className={`mt-1 ml-5 pl-4 border-l space-y-0.5 ${darkMode ? 'border-slate-800' : 'border-slate-200/80'}`}>
                  {FLEET_SUBITEMS.map((sub) => {
                    const subActive = currentPage === sub.id;
                    return (
                      <button
                        key={sub.id}
                        onClick={() => { setCurrentPage(sub.id); setMobileSidebarOpen(false); }}
                        className={`w-full text-left px-3 py-1.5 rounded-lg text-[12px] transition ${
                          subActive
                            ? (darkMode ? 'bg-emerald-500/15 text-emerald-400 font-semibold' : 'bg-emerald-50 text-emerald-700 font-semibold')
                            : (darkMode ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/70' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50')
                        }`}
                      >
                        {sub.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {MAIN_MENU_ITEMS.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => { setCurrentPage(item.id); setMobileSidebarOpen(false); }}
                  className={`eco-nav-item w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-[13px] font-semibold ${
                    isActive ? 'eco-nav-item-active' : darkMode ? 'text-slate-300' : 'text-slate-600'
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <i className={`${item.icon} w-4 text-center text-sm ${isActive ? '' : 'text-slate-400'}`}></i>
                    <span>{item.name}</span>
                  </span>
                  {item.badge ? (
                    <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[10px] font-bold flex items-center justify-center">{item.badge}</span>
                  ) : item.hasArrow ? (
                    <i className="fa-solid fa-chevron-right text-[10px] text-slate-400"></i>
                  ) : null}
                </button>
              );
            })}
          </nav>

          {/* SUPPORT */}
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 mt-5 mb-2">Support</div>
          <nav className="space-y-1">
            {SUPPORT_ITEMS.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => { setCurrentPage(item.id); setMobileSidebarOpen(false); }}
                  className={`eco-nav-item w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-[13px] font-semibold ${
                    isActive ? 'eco-nav-item-active' : darkMode ? 'text-slate-300' : 'text-slate-600'
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <i className={`${item.icon} w-4 text-center text-sm ${isActive ? '' : 'text-slate-400'}`}></i>
                    <span>{item.name}</span>
                  </span>
                  {item.badge > 0 && (
                    <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-slate-900 text-white text-[10px] font-bold flex items-center justify-center">{item.badge}</span>
                  )}
                </button>
              );
            })}
            <button
              onClick={() => { setCurrentPage('landing'); setMobileSidebarOpen(false); }}
              className={`eco-nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-semibold ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}
            >
              <i className="fa-regular fa-life-ring w-4 text-center text-sm text-slate-400"></i>
              <span>Trang chủ & Hỗ trợ</span>
            </button>
          </nav>
        </div>

        {/* BOTTOM UPGRADE CARD & UTILITIES */}
        <div className="space-y-3 pt-5">
          <div className={`rounded-2xl p-4 border ${darkMode ? 'bg-gradient-to-b from-emerald-950/70 to-slate-900 border-emerald-800/60' : 'bg-gradient-to-b from-emerald-100/75 via-emerald-50/45 to-white border-emerald-200/70'}`}>
            <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center shadow-sm mb-2.5">
              <i className="fa-solid fa-star text-xs"></i>
            </div>
            <div className={`font-bold text-sm leading-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>Gói Premium</div>
            <p className={`text-[11px] mt-1 mb-3 leading-snug ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Mở rộng quy mô đội xe & tính năng phân tích không giới hạn
            </p>
            <button
              type="button"
              onClick={() => showToast('Đang ở giao diện Nâng cấp gói (Demo).', 'info')}
              className={`w-full py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 shadow-xs transition ${darkMode ? 'bg-slate-800 border-slate-700 text-slate-100 hover:border-emerald-500' : 'bg-white border-slate-200/90 text-slate-800 hover:border-emerald-400'}`}
            >
              <i className="fa-solid fa-bolt text-emerald-600 text-[11px]"></i>
              <span>Nâng cấp gói</span>
            </button>
          </div>

          <div className={`pt-2 border-t space-y-1 ${darkMode ? 'border-slate-800' : 'border-slate-100'}`}>
            <button
              onClick={() => { setCurrentPage('settings'); setMobileSidebarOpen(false); }}
              className={`eco-nav-item w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-semibold ${
                currentPage === 'settings' ? 'eco-nav-item-active' : darkMode ? 'text-slate-300' : 'text-slate-600'
              }`}
            >
              <i className={`fa-solid fa-gear w-4 text-center text-sm ${currentPage === 'settings' ? '' : 'text-slate-400'}`}></i>
              <span>Cài đặt & Live-Code</span>
            </button>

            <div className={`flex items-center justify-between px-3 py-2 rounded-xl text-[13px] font-semibold ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>
              <span className="flex items-center gap-3">
                <i className="fa-regular fa-moon w-4 text-center text-sm text-slate-400"></i>
                <span>Dark mode</span>
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={darkMode}
                onClick={toggleDarkMode}
                className={`w-9 h-5 rounded-full p-0.5 transition-colors flex items-center ${darkMode ? 'bg-emerald-600 justify-end' : 'bg-slate-200 justify-start'}`}
              >
                <span className="w-4 h-4 rounded-full bg-white shadow-xs"></span>
              </button>
            </div>

            <button
              onClick={handleLogout}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-semibold transition ${darkMode ? 'text-rose-400 hover:bg-slate-800' : 'text-slate-500 hover:text-red-600 hover:bg-red-50/70'}`}
            >
              <i className="fa-solid fa-arrow-right-from-bracket w-4 text-center text-sm"></i>
              <span>Đăng xuất</span>
            </button>
          </div>
        </div>
      </aside>

      {/* MAIN WORKSPACE */}
      <main className="flex-1 min-w-0 flex flex-col">
        <header className={`sticky top-0 z-20 w-full flex flex-wrap justify-between items-center gap-3 backdrop-blur-xl px-4 sm:px-6 lg:px-7 py-3 sm:py-3.5 border-b shadow-[0_4px_20px_-10px_rgba(14,165,233,0.12)] ${darkMode ? 'bg-slate-900/95 border-slate-800 text-slate-100' : 'bg-white/95 border-slate-200/80'}`}>
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <button onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)} className={`lg:hidden p-2 rounded-xl border transition shrink-0 ${darkMode ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-sky-50 border-sky-100 text-text-main hover:shadow-[0_0_12px_rgba(16,185,129,0.2)]'}`}>
              <i className="fa-solid fa-bars"></i>
            </button>
            <h2 className={`text-base sm:text-xl lg:text-2xl font-extrabold tracking-tight m-0 truncate ${darkMode ? 'text-white' : 'text-slate-900'}`}>{PAGE_TITLES[currentPage]}</h2>
            <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1 rounded-full bg-emerald-100/80 text-brand-800 border border-emerald-300 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 pulse-dot"></span>
              <span>SQLite Live Sync</span>
            </span>
          </div>

          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            <button onClick={() => setCurrentPage('notifications')} className={`relative p-2 sm:p-2.5 rounded-xl border transition-all ${darkMode ? 'bg-slate-800 border-slate-700 hover:border-emerald-500' : 'bg-sky-50/80 border-sky-100 hover:bg-white hover:border-brand-300 hover:shadow-[0_0_14px_rgba(16,185,129,0.22)]'}`}>
              <i className={`fa-regular fa-bell text-sm ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}></i>
              {unreadCount > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-r from-brand-600 to-emerald-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center shadow-sm">{unreadCount}</span>}
            </button>

            <div className={`flex items-center gap-2.5 pl-3 border-l ${darkMode ? 'border-slate-800' : 'border-sky-100'}`}>
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-gradient-to-br from-sky-100 to-emerald-100 border border-emerald-200 text-brand-700 flex items-center justify-center text-xs font-bold shadow-sm">
                {(user.name || 'NV').slice(0, 2).toUpperCase()}
              </div>
              <div className="leading-tight hidden sm:block">
                <div className={`font-bold text-xs ${darkMode ? 'text-white' : 'text-slate-900'}`}>{user.name} <span className="text-[10px] bg-emerald-100/80 text-brand-800 border border-emerald-200 px-1.5 py-0.5 rounded-full">{user.role}</span></div>
                <div className={`text-[11px] font-medium truncate max-w-[160px] ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>{user.company_name || 'EcoLogix Logistics'}</div>
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 p-3 sm:p-5 lg:p-7">
          <div className="max-w-[1600px] mx-auto w-full">
            {currentPage === 'dashboard' && <DashboardView onNavigate={setCurrentPage} showToast={showToast} />}
            {currentPage === 'inventory' && <InventoryView user={user} showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
            {currentPage === 'forecasting' && <ForecastingView user={user} showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
            {currentPage === 'orders' && <OrdersView user={user} showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
            {currentPage === 'routing' && <RoutingView user={user} showToast={showToast} onRefreshHeader={refreshHeaderStats} />}
            {currentPage === 'vehicles' && <VehiclesView user={user} showToast={showToast} />}
            {currentPage === 'partners' && <PartnersView user={user} showToast={showToast} />}
            {currentPage === 'ai_assistant' && <AiAssistantView user={user} preloadedPrompt={preloadedAiPrompt} clearPreloaded={() => setPreloadedAiPrompt('')} onNavigate={setCurrentPage} showToast={showToast} />}
            {currentPage === 'reports' && <ReportsView user={user} showToast={showToast} />}
            {currentPage === 'notifications' && <NotificationsView user={user} onRefreshHeader={refreshHeaderStats} showToast={showToast} />}
            {currentPage === 'settings' && <SettingsView user={user} setUser={setUser} showToast={showToast} />}
          </div>
        </div>
      </main>
    </div>
  );
}

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen eco-sky-canvas flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-3xl border border-red-200 p-6 shadow-xl text-center space-y-4">
            <div className="text-3xl">⚠️</div>
            <h3 className="text-lg font-extrabold text-slate-900 m-0">Đã xảy ra sự cố hiển thị</h3>
            <p className="text-xs text-slate-600 m-0">{this.state.error?.message || 'Lỗi kết xuất giao diện React.'}</p>
            <div className="flex gap-2 justify-center pt-1">
              <button type="button" onClick={() => { this.setState({ error: null }); window.history.pushState({}, '', '/'); window.location.reload(); }} className="px-4 py-2 rounded-full border border-slate-300 text-xs font-bold text-slate-700">Về Trang chủ</button>
              <button type="button" onClick={() => window.location.reload()} className="px-5 py-2 rounded-full bg-brand-600 text-white text-xs font-bold">Tải lại trang</button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

Object.assign(window, { App, AppErrorBoundary });

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <AppErrorBoundary>
    <App />
  </AppErrorBoundary>
);
