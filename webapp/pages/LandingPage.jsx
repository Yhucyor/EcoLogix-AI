const { useState, useEffect, useRef, useMemo } = React;

// ==================== 1. LANDING VIEW (CODE.HTML + PRICING + FAQ + CONTACT) ====================
function LandingView({ user, onLogin, onRegister, onOnboardingComplete, onGoApp, onAskAi, toast, showToast }) {
  const [simVehicle, setSimVehicle] = useState('truck');
  const [faqOpen, setFaqOpen] = useState(0);
  const [activeNav, setActiveNav] = useState('hero');
  const [activeShowcaseTab, setActiveShowcaseTab] = useState('dashboard');
  const [showStartModal, setShowStartModal] = useState(false);
  const [contactForm, setContactForm] = useState({ name: '', contact: '', need: 'Dùng thử miễn phí 14 ngày', message: '' });

  const openStartPopup = () => setShowStartModal(true);

  const headerRef = useRef(null);

  const HEADER_NAV = [
    { id: 'hero', label: 'Trang chủ' },
    { id: 'features', label: 'Tính năng' },
    { id: 'dashboard', label: 'Giải pháp' },
    { id: 'pricing', label: 'Báo giá' },
    { id: 'contact', label: 'Liên hệ' },
  ];

  const scrollToSection = (sectionId) => {
    setActiveNav(sectionId);
    const el = document.getElementById(sectionId);
    if (el) {
      const offset = (headerRef.current?.offsetHeight || 80) + 12;
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
  };

  const openFeatureShowcase = (pageId) => {
    setActiveShowcaseTab(pageId);
    scrollToSection('dashboard');
  };

  useEffect(() => {
    const sectionIds = ['hero', 'features', 'dashboard', 'pricing', 'contact'];
    const onScroll = () => {
      const scrollPos = window.scrollY + 130;
      let current = 'hero';
      for (const id of sectionIds) {
        const el = document.getElementById(id);
        if (el) {
          const absTop = el.getBoundingClientRect().top + window.scrollY;
          if (absTop <= scrollPos) current = id;
        }
      }
      setActiveNav(current);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const FEATURE_CARDS = [
    { icon: 'fa-chart-line', title: 'Dự báo nhu cầu', desc: 'Mô hình LightGBM thực tế dự báo nhu cầu 7–90 ngày & Safety Stock.', page: 'forecasting', badge: 'LightGBM ML' },
    { icon: 'fa-route', title: 'Tối ưu lộ trình', desc: 'Giảm 15-22% chi phí nhiên liệu & tự động né giờ cấm tải 16h–18h.', page: 'routing', badge: 'CVRPTW 2-Opt' },
    { icon: 'fa-robot', title: 'Trợ lý AI đa tác vụ', desc: '6 Agents chuyên trách hỗ trợ 100% tiếng Việt truy vấn SQLite.', page: 'ai_assistant', badge: '6 AI Agents' },
    { icon: 'fa-earth-americas', title: 'Báo cáo ESG', desc: 'Chuẩn GHG Protocol Scope 1, xuất file PDF & Excel đa sheet tức thì.', page: 'reports', badge: 'Scope 1 CO₂' },
  ];

  const SHOWCASE_NAV = [
    { name: 'Tổng quan', icon: 'fa-grip', page: 'dashboard' },
    { name: 'Kho & SKU', icon: 'fa-warehouse', page: 'inventory' },
    { name: 'Dự báo nhu cầu', icon: 'fa-chart-pie', page: 'forecasting' },
    { name: 'Tối ưu lộ trình', icon: 'fa-map-location-dot', page: 'routing' },
    { name: 'Trợ lý AI', icon: 'fa-robot', page: 'ai_assistant' },
    { name: 'Báo cáo ESG', icon: 'fa-file-invoice', page: 'reports' },
    { name: 'Cài đặt', icon: 'fa-gear', page: 'settings' },
  ];

  const activeTabMeta = SHOWCASE_NAV.find((m) => m.page === activeShowcaseTab) || SHOWCASE_NAV[0];

  const sendContact = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/contact', { method: 'POST', body: JSON.stringify(contactForm) });
      showToast(res.message);
      setContactForm({ name: '', contact: '', need: 'Dùng thử miễn phí 14 ngày', message: '' });
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="min-h-screen eco-sky-canvas flex flex-col">
      {toast && (
        <div className={`fixed top-5 right-5 z-50 px-5 py-3 rounded-xl shadow-xl text-white text-xs font-bold ${toast.type === 'error' ? 'bg-red-600' : 'bg-brand-600'}`}>
          {toast.msg}
        </div>
      )}

      {/* MainHeader */}
      <header ref={headerRef} className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <a className="flex items-center gap-2.5 group cursor-pointer" onClick={() => scrollToSection('hero')}>
              <BrandLogo sizeClass="w-11 h-11" className="shadow-brand-500/20 group-hover:scale-105 transition-transform" />
              <div className="flex items-baseline">
                <span className="text-2xl font-bold tracking-tight text-slate-900">EcoLogix</span>
                <span className="text-2xl font-extrabold text-brand-600 ml-1">AI</span>
              </div>
            </a>

            <nav className="hidden md:flex items-center gap-8 font-medium text-slate-600 text-sm">
              {HEADER_NAV.map((nav) => (
                <a
                  key={nav.id}
                  href={`#${nav.id}`}
                  onClick={(e) => { e.preventDefault(); scrollToSection(nav.id); }}
                  className={`transition-colors py-1 border-b-2 ${
                    activeNav === nav.id
                      ? 'text-brand-600 font-bold border-brand-600'
                      : 'border-transparent hover:text-brand-600'
                  }`}
                >
                  {nav.label}
                </a>
              ))}
            </nav>

            <div className="flex items-center gap-3">
              <button onClick={onLogin} className="px-5 py-2.5 rounded-full border border-brand-600 text-brand-700 font-semibold text-sm hover:bg-brand-50 transition-all" type="button">
                Đăng nhập
              </button>
              <button onClick={openStartPopup} className="hidden sm:inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-brand-600 text-white font-semibold text-sm shadow-md shadow-brand-600/25 hover:bg-brand-700 transition-all" type="button">
                <span>Bắt đầu ngay</span>
                <i className="fa-solid fa-arrow-right text-xs"></i>
              </button>
            </div>
          </div>
          <nav className="flex md:hidden items-center gap-4 overflow-x-auto pb-2.5 pt-0.5 text-xs font-semibold text-slate-600">
            {HEADER_NAV.map((nav) => (
              <a
                key={nav.id}
                href={`#${nav.id}`}
                onClick={(e) => { e.preventDefault(); scrollToSection(nav.id); }}
                className={`whitespace-nowrap px-2.5 py-1 rounded-full transition-colors ${
                  activeNav === nav.id ? 'bg-brand-50 text-brand-700 font-bold' : 'hover:text-brand-600'
                }`}
              >
                {nav.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* HeroSection */}
        <section className="scroll-mt-24 relative pt-12 pb-20 lg:pt-16 lg:pb-24 overflow-hidden bg-gradient-to-br from-sky-100/60 via-white/90 to-emerald-50/70" id="hero">
          <div className="absolute top-6 left-1/4 w-[520px] h-[360px] bg-sky-200/40 blur-3xl rounded-full -z-10 pointer-events-none"></div>
          <div className="absolute top-14 right-1/4 w-[520px] h-[360px] bg-emerald-200/35 blur-3xl rounded-full -z-10 pointer-events-none"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
              <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-100/80 border border-emerald-300 text-brand-800 text-xs font-semibold tracking-wide shadow-sm">
                  <span className="w-2 h-2 rounded-full bg-brand-500 pulse-dot"></span>
                  <span>Nền tảng Multi-Agent AI Chuỗi cung ứng Xanh</span>
                </div>
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-[1.2] lg:leading-[1.15]">
                  Nền tảng <span className="text-brand-600">Multi-Agent AI</span><br className="hidden sm:inline" />
                  Tối ưu chuỗi cung ứng &<br className="hidden sm:inline" />
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-brand-600 to-emerald-500">Logistics xanh</span> cho SMEs
                </h1>
                <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto lg:mx-0 font-normal leading-relaxed">
                  Dự báo thông minh • Lộ trình tối ưu • Giảm phát thải CO₂ • Cùng doanh nghiệp vừa và nhỏ hướng tới chuyển đổi xanh và phát triển bền vững.
                </p>
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
                  <button onClick={openStartPopup} className="w-full sm:w-auto px-7 py-3.5 rounded-full bg-gradient-to-r from-brand-600 to-emerald-500 text-white font-bold text-sm shadow-lg shadow-brand-500/30 hover:shadow-xl transition-all flex items-center justify-center gap-2 group">
                    <span>Bắt đầu ngay</span>
                    <i className="fa-solid fa-arrow-right group-hover:translate-x-1 transition-transform"></i>
                  </button>
                  <button onClick={() => onGoApp('dashboard')} className="w-full sm:w-auto px-7 py-3.5 rounded-full border border-slate-300 bg-white/80 hover:bg-slate-50 text-slate-700 font-semibold text-sm transition-all shadow-sm flex items-center justify-center gap-2">
                    <i className="fa-regular fa-circle-play text-brand-600 text-base"></i>
                    <span>Xem Demo Dashboard</span>
                  </button>
                </div>
                <div className="pt-4 flex items-center justify-center lg:justify-start gap-6 text-xs text-slate-500 font-medium">
                  <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Dùng thử miễn phí 14 ngày</div>
                  <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Không cần thẻ tín dụng</div>
                  <div className="flex items-center gap-1.5"><i className="fa-solid fa-check text-brand-500 font-bold"></i> Hỗ trợ kỹ thuật 24/7</div>
                </div>
              </div>

              {/* Hero Graphic Card */}
              <div className="lg:col-span-5 relative flex justify-center">
                <div className="w-full max-w-md lg:max-w-none bg-gradient-to-br from-sky-50/85 via-emerald-50/55 to-white rounded-3xl p-6 border border-sky-100 shadow-2xl relative overflow-hidden">
                  <div className="flex items-center justify-between mb-4 border-b border-emerald-100 pb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-400"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                      <div className="w-3 h-3 rounded-full bg-green-400"></div>
                      <span className="text-xs font-semibold text-slate-500 ml-2">Eco Delivery Simulator v2.4</span>
                    </div>
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-brand-100 text-brand-700">Live AI Fleet</span>
                  </div>

                  <div className="relative rounded-2xl bg-gradient-to-b from-white to-emerald-50/50 p-6 border border-slate-100 text-center flex flex-col items-center">
                    <div className="relative w-48 h-32 flex items-center justify-center">
                      <div className="absolute inset-0 bg-emerald-400/20 rounded-full blur-xl"></div>
                      <i className="fa-solid fa-truck-fast text-6xl text-brand-600 relative z-10 drop-shadow-md"></i>
                      <BrandLogo sizeClass="w-10 h-10" roundedClass="rounded-full" className="absolute -top-2 right-7 animate-bounce border-emerald-200 shadow-md" />
                    </div>
                    <h4 className="font-bold text-slate-800 text-sm mt-2">Hệ thống Điều phối Lộ trình Tối ưu</h4>
                    <p className="text-xs text-slate-500 mt-0.5">Tự động giảm tải trọng rỗng và giảm khí thải nhà kính</p>
                    <div className="mt-4 w-full grid grid-cols-2 gap-2 text-left">
                      <div className="bg-white p-2.5 rounded-xl border border-slate-100 shadow-sm">
                        <div className="text-[11px] text-slate-400 font-medium">Tiết kiệm nhiên liệu</div>
                        <div className="text-sm font-bold text-brand-600 mt-0.5">18.5% ~ 22.0%</div>
                      </div>
                      <div className="bg-white p-2.5 rounded-xl border border-slate-100 shadow-sm">
                        <div className="text-[11px] text-slate-400 font-medium">CO₂ Cắt giảm</div>
                        <div className="text-sm font-bold text-teal-600 mt-0.5">-22.7 kg / chuyến</div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 bg-brand-700 text-white text-xs font-medium rounded-xl p-3 flex items-center justify-between shadow-sm">
                    <div className="flex items-center gap-2"><i className="fa-solid fa-seedling text-brand-300"></i><span>EcoLogix.AI: Kiến tạo chuỗi cung ứng xanh</span></div>
                    <button onClick={() => onGoApp('dashboard')} className="text-brand-200 hover:text-white font-bold inline-flex items-center gap-1 text-[11px]">
                      Khám phá ngay <i className="fa-solid fa-chevron-right text-[9px]"></i>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* 4 Key Highlights / Tính năng Cốt lõi */}
            <div className="scroll-mt-24 pt-12 mt-14 border-t border-slate-200/70" id="features">
              <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 mb-6">
                <div>
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-[11px] font-bold uppercase tracking-wider mb-1.5">Tính năng cốt lõi</span>
                  <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900">Chọn tính năng để xem trực tiếp trên trang chủ</h2>
                </div>
                <p className="text-xs text-slate-500">Nhấp vào từng thẻ để chuyển tới đúng phân hệ tương ứng bên dưới</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                {FEATURE_CARDS.map((c, idx) => {
                  const isSelected = activeShowcaseTab === c.page;
                  return (
                    <div
                      key={idx}
                      onClick={() => openFeatureShowcase(c.page)}
                      className={`cursor-pointer bg-white rounded-2xl p-5 border transition-all flex flex-col justify-between gap-3 group ${
                        isSelected
                          ? 'border-brand-500 ring-2 ring-brand-500/20 shadow-elevated'
                          : 'border-slate-200/80 shadow-card hover:shadow-lg hover:border-brand-300'
                      }`}
                    >
                      <div className="flex items-start gap-3.5">
                        <div className={`w-12 h-12 rounded-xl border flex items-center justify-center shrink-0 transition-colors ${isSelected ? 'bg-brand-600 text-white border-brand-600' : 'bg-brand-50 border-brand-100 text-brand-600 group-hover:bg-brand-600 group-hover:text-white'}`}>
                          <i className={`fa-solid ${c.icon} text-lg`}></i>
                        </div>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-brand-600">{c.badge}</span>
                          <h3 className="font-bold text-slate-900 text-sm mt-0.5">{c.title}</h3>
                          <p className="text-xs text-slate-500 mt-1 leading-relaxed">{c.desc}</p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between pt-2.5 border-t border-slate-100 text-[11px] font-bold">
                        <span className="text-brand-600 group-hover:translate-x-0.5 transition-transform">Xem tại Showcase ↓</span>
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); onGoApp(c.page); }}
                          className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-brand-600 text-slate-700 hover:text-white transition"
                        >
                          Mở đầy đủ →
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Interactive Dashboard Showcase Section */}
        <section className="scroll-mt-24 py-16 bg-gradient-to-b from-sky-50/75 via-slate-50/85 to-emerald-50/45 border-t border-sky-100" id="dashboard">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-10">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-100 text-brand-800 text-xs font-bold uppercase tracking-wider mb-2">Trải nghiệm Thực tế</div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900">Bảng điều khiển Trung tâm Điều hành Toàn diện</h2>
              <p className="text-slate-600 text-sm sm:text-base mt-2">Chọn từng phân hệ ở menu bên trái để xem mô phỏng trực tiếp ngay tại đây hoặc mở không gian làm việc SQLite đầy đủ.</p>
            </div>

            <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden">
              <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[640px]">
                <aside className="lg:col-span-3 xl:col-span-2 bg-slate-900 text-slate-300 p-4 flex flex-col justify-between border-r border-slate-800">
                  <div>
                    <div className="flex items-center gap-2 px-2 py-3 mb-6">
                      <BrandLogo sizeClass="w-8 h-8" roundedClass="rounded-lg" />
                      <span className="font-bold text-white text-base">EcoLogix AI</span>
                    </div>
                    <div className="space-y-1">
                      {SHOWCASE_NAV.map((m) => {
                        const isActive = activeShowcaseTab === m.page;
                        return (
                          <button
                            key={m.page}
                            type="button"
                            onClick={() => setActiveShowcaseTab(m.page)}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-xs transition-all ${
                              isActive ? 'bg-brand-600 text-white shadow-sm font-semibold' : 'hover:bg-slate-800 hover:text-white'
                            }`}
                          >
                            <i className={`fa-solid ${m.icon} text-sm w-4`}></i><span>{m.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="pt-4 border-t border-slate-800">
                    <div className="bg-slate-800/80 rounded-xl p-3 flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-brand-700 text-white flex items-center justify-center font-bold text-xs">ABC</div>
                      <div className="truncate"><div className="text-[11px] text-slate-400">Doanh nghiệp</div><div className="text-xs font-semibold text-white truncate">EcoLogix SME</div></div>
                    </div>
                  </div>
                </aside>

                <div className="lg:col-span-9 xl:col-span-10 bg-slate-50 p-6 space-y-5">
                  <div className="flex flex-wrap items-center justify-between gap-3 bg-white px-4 py-3 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="flex items-center gap-2.5">
                      <span className="w-8 h-8 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center"><i className={`fa-solid ${activeTabMeta.icon}`}></i></span>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-brand-600">Xem trước Phân hệ</div>
                        <h3 className="text-sm font-extrabold text-slate-900 m-0">{activeTabMeta.name}</h3>
                      </div>
                    </div>
                    <button onClick={() => onGoApp(activeShowcaseTab)} className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold shadow-sm transition">
                      Mở {activeTabMeta.name} đầy đủ →
                    </button>
                  </div>

                  {activeShowcaseTab === 'dashboard' && (
                    <>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"><div className="flex justify-between text-slate-500 text-xs"><span>Chi phí kỳ hiện tại</span><i className="fa-solid fa-wallet text-brand-600"></i></div><div className="mt-2 flex items-baseline justify-between"><div className="text-2xl font-black text-slate-900">113.1 <span className="text-xs font-semibold text-slate-500">tr</span></div><span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">↓ 18.1%</span></div></div>
                        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"><div className="flex justify-between text-slate-500 text-xs"><span>Phát thải CO₂</span><i className="fa-solid fa-cloud-arrow-down text-brand-600"></i></div><div className="mt-2 flex items-baseline justify-between"><div className="text-2xl font-black text-slate-900">2.12 <span className="text-xs font-semibold text-slate-500">tấn</span></div><span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">↓ 18.7%</span></div></div>
                        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"><div className="flex justify-between text-slate-500 text-xs"><span>Hiệu suất tồn kho</span><i className="fa-solid fa-boxes-stacked text-brand-600"></i></div><div className="mt-2 flex items-baseline justify-between"><div className="text-2xl font-black text-slate-900">94.4%</div><span className="text-xs font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded">↑ An toàn</span></div></div>
                        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"><div className="flex justify-between text-slate-500 text-xs"><span>Điểm xanh ESG</span><i className="fa-solid fa-sack-dollar text-brand-600"></i></div><div className="mt-2 flex items-baseline justify-between"><div className="text-2xl font-black text-brand-600">95.2%</div><span className="text-xs font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded">Net-Zero</span></div></div>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                        <div className="lg:col-span-6 bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
                          <div className="flex justify-between border-b border-slate-100 pb-3">
                            <div><h4 className="font-bold text-slate-900 text-sm">Xu hướng chi phí & phát thải</h4><p className="text-[11px] text-slate-400">Dữ liệu thực tế từ bảng expenses & esg_reports</p></div>
                            <button onClick={() => onGoApp('reports')} className="text-xs font-bold text-brand-600 hover:underline">Mở báo cáo →</button>
                          </div>
                          <div className="py-5">
                            <svg className="w-full h-36 overflow-visible" preserveAspectRatio="none" viewBox="0 0 400 120">
                              <line stroke="#f1f5f9" strokeWidth="1" x1="0" x2="400" y1="30" y2="30"></line>
                              <line stroke="#f1f5f9" strokeWidth="1" x1="0" x2="400" y1="60" y2="60"></line>
                              <line stroke="#f1f5f9" strokeWidth="1" x1="0" x2="400" y1="90" y2="90"></line>
                              <path d="M0,90 Q 60,70 120,75 T 240,45 T 320,55 T 400,25" fill="none" stroke="#059669" strokeLinecap="round" strokeWidth="3"></path>
                              <path d="M0,105 Q 60,95 120,85 T 240,65 T 320,40 T 400,30" fill="none" stroke="#34d399" strokeDasharray="4,4" strokeLinecap="round" strokeWidth="2.5"></path>
                              <circle cx="240" cy="45" fill="#059669" r="4"></circle><circle cx="400" cy="25" fill="#059669" r="5"></circle>
                            </svg>
                            <div className="flex justify-between text-[10px] text-slate-400 font-semibold mt-2"><span>T7</span><span>T8</span><span>T9</span><span>T10</span><span>T11</span></div>
                          </div>
                        </div>

                        <div className="lg:col-span-6 bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
                          <div className="flex justify-between border-b border-slate-100 pb-3 mb-3">
                            <div><h4 className="font-bold text-slate-900 text-sm">Green Route Planner (Leaflet Live Map)</h4><p className="text-[11px] text-slate-400">Chuyển đổi chế độ OSM / Dark / Vệ tinh / Địa hình</p></div>
                            <button onClick={() => onGoApp('routing')} className="px-2.5 py-1 bg-brand-50 text-brand-700 font-bold text-[11px] rounded-full border border-brand-200 hover:bg-brand-100">Mở bản đồ đầy đủ</button>
                          </div>
                          <EcoLeafletMap
                            depot={{ lat: 10.8505, lng: 106.7718, name: 'Kho Tổng EcoLogix (TP. Thủ Đức)' }}
                            routes={[{
                              color: simVehicle === 'ev' ? '#10B981' : '#0284C7',
                              stops: [
                                { lat: 10.9022, lng: 106.7584, label: 'Dĩ An, Bình Dương', popup: '<b>Điểm #1: Bách Hóa Dĩ An</b><br/>Dự kiến: 08:35' },
                                { lat: 10.9333, lng: 106.7167, label: 'Thuận An, Bình Dương', popup: '<b>Điểm #2: Đại Lý Thuận An</b><br/>Dự kiến: 09:15' },
                                { lat: 10.7769, lng: 106.7009, label: 'Quận 1, TP.HCM', popup: '<b>Điểm #3: Bách Hóa Quận 1</b><br/>Ngoài giờ cấm tải' },
                              ],
                            }]}
                            showRestrictedZone={true}
                            heightClass="h-[220px]"
                            defaultTheme="osm"
                            openDepotPopup={false}
                          />
                          <div className="flex items-center justify-between text-xs mt-3 pt-2 border-t border-slate-100">
                            <div className="flex gap-2">
                              <button onClick={() => setSimVehicle('truck')} className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold ${simVehicle === 'truck' ? 'bg-brand-50 border border-brand-200 text-brand-700' : 'bg-slate-100 text-slate-600'}`}>🚚 Xe tải trung</button>
                              <button onClick={() => setSimVehicle('ev')} className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold ${simVehicle === 'ev' ? 'bg-brand-50 border border-brand-200 text-brand-700' : 'bg-slate-100 text-slate-600'}`}>⚡ Xe điện EV</button>
                            </div>
                            <span className="text-[11px] text-brand-700 font-bold">{simVehicle === 'ev' ? '0 kg CO₂ ống xả' : 'Giảm 18.4% nhiên liệu'}</span>
                          </div>
                        </div>
                      </div>

                      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                          <div className="flex items-center gap-2"><i className="fa-solid fa-wand-magic-sparkles text-brand-600"></i><h4 className="font-bold text-slate-900 text-sm m-0">Trợ lý AI - Multi-Agent Assistant (6 Agents Tiếng Việt)</h4></div>
                          <div className="flex flex-wrap gap-2 text-[11px]">
                            <button onClick={() => onAskAi('Kho hàng hiện còn bao nhiêu sản phẩm và có mặt hàng nào sắp hết?')} className="bg-slate-100 hover:bg-emerald-50 text-slate-700 px-2.5 py-1 rounded-full font-medium">📊 Kiểm tra tồn kho ngay?</button>
                            <button onClick={() => onAskAi('Tối nay đi 5 đơn Bình Dương dùng xe nào rẻ nhất?')} className="bg-slate-100 hover:bg-emerald-50 text-slate-700 px-2.5 py-1 rounded-full font-medium">🚚 Tuyến Bình Dương xe nào rẻ nhất?</button>
                          </div>
                        </div>
                        <div className="mt-3 flex items-center gap-2">
                          <button onClick={() => onGoApp('ai_assistant')} className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold transition">Mở Cửa Sổ Hội Thoại 6 Agents Tiếng Việt →</button>
                        </div>
                      </div>
                    </>
                  )}

                  {activeShowcaseTab === 'forecasting' && (
                    <div className="space-y-5">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="bg-white p-4 rounded-2xl border border-slate-200"><div className="text-xs text-slate-500">Nhu cầu dự báo 30 ngày</div><div className="font-mono text-2xl font-black text-slate-900 mt-1">8,450 đơn vị</div><span className="text-[11px] font-bold text-brand-600">LightGBM MAPE 4.2%</span></div>
                        <div className="bg-white p-4 rounded-2xl border border-slate-200"><div className="text-xs text-slate-500">Điểm tái đặt hàng (ROP)</div><div className="font-mono text-2xl font-black text-amber-600 mt-1">420 SKU</div><span className="text-[11px] text-slate-500">Tự động cảnh báo thiếu hàng</span></div>
                        <div className="bg-white p-4 rounded-2xl border border-slate-200"><div className="text-xs text-slate-500">Lô nhập EOQ tối ưu</div><div className="font-mono text-2xl font-black text-brand-600 mt-1">+1,200</div><span className="text-[11px] text-slate-500">Tiết kiệm 16% chi phí lưu kho</span></div>
                      </div>
                      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-center mb-4">
                          <div><h4 className="font-bold text-slate-900 text-sm">Đường cong Dự báo Nhu cầu vs Thực tế (LightGBM 4.7.0)</h4><p className="text-[11px] text-slate-400">Hỗ trợ dự báo 7, 14, 30 hoặc 90 ngày kèm dải tin cậy</p></div>
                          <button onClick={() => onGoApp('forecasting')} className="px-3 py-1.5 rounded-xl bg-brand-600 text-white text-xs font-bold">Chạy mô hình thực tế →</button>
                        </div>
                        <svg className="w-full h-44 overflow-visible" viewBox="0 0 600 140">
                          <path d="M0,110 L100,98 L200,104 L300,82 L400,66 L500,52 L600,32" fill="none" stroke="#0284C7" strokeWidth="3" />
                          <path d="M0,115 L100,102 L200,95 L300,76 L400,62 L500,45 L600,26" fill="none" stroke="#10B981" strokeDasharray="6,4" strokeWidth="3" />
                        </svg>
                        <div className="flex justify-between text-[11px] text-slate-400 font-semibold mt-2"><span>Hôm nay</span><span>Ngày 7</span><span>Ngày 14</span><span>Ngày 21</span><span>Ngày 30</span></div>
                      </div>
                    </div>
                  )}

                  {activeShowcaseTab === 'routing' && (
                    <div className="space-y-4">
                      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
                        <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
                          <div><h4 className="font-bold text-slate-900 text-sm">Tối ưu Lộ trình CVRPTW 2-Opt & Né Giờ Cấm Tải Nội Đô</h4><p className="text-[11px] text-slate-500">Hỗ trợ tới 100 điểm TP.HCM – Bình Dương – Đồng Nai & đa chế độ bản đồ Leaflet</p></div>
                          <div className="flex gap-2">
                            <button onClick={() => setSimVehicle('truck')} className={`px-3 py-1.5 rounded-xl text-xs font-bold ${simVehicle === 'truck' ? 'bg-sky-50 border border-sky-200 text-sky-700' : 'bg-slate-100 text-slate-600'}`}>🚚 Xe tải trung</button>
                            <button onClick={() => setSimVehicle('ev')} className={`px-3 py-1.5 rounded-xl text-xs font-bold ${simVehicle === 'ev' ? 'bg-emerald-50 border border-emerald-200 text-brand-700' : 'bg-slate-100 text-slate-600'}`}>⚡ Xe điện EV</button>
                          </div>
                        </div>
                        <EcoLeafletMap
                          depot={{ lat: 10.8505, lng: 106.7718, name: 'Kho Tổng EcoLogix (TP. Thủ Đức)' }}
                          routes={[{
                            color: simVehicle === 'ev' ? '#10B981' : '#0284C7',
                            stops: [
                              { lat: 10.9022, lng: 106.7584, label: 'Dĩ An, Bình Dương', popup: '<b>Điểm #1: Bách Hóa Dĩ An</b><br/>Dự kiến: 08:35' },
                              { lat: 10.9333, lng: 106.7167, label: 'Thuận An, Bình Dương', popup: '<b>Điểm #2: Đại Lý Thuận An</b><br/>Dự kiến: 09:15' },
                              { lat: 10.7769, lng: 106.7009, label: 'Quận 1, TP.HCM', popup: '<b>Điểm #3: Bách Hóa Quận 1</b><br/>Ngoài giờ cấm tải 16h–18h' },
                            ],
                          }]}
                          showRestrictedZone={true}
                          heightClass="h-[340px]"
                          defaultTheme="osm"
                          openDepotPopup={true}
                        />
                      </div>
                    </div>
                  )}

                  {activeShowcaseTab === 'ai_assistant' && (
                    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
                      <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                        <div><h4 className="font-bold text-slate-900 text-sm">6 Specialized Agents • Truy vấn SQLite Thời gian Thực</h4><p className="text-[11px] text-slate-500">Supervisor, Demand, Inventory, Route, Finance & ESG Agents</p></div>
                        <button onClick={() => onGoApp('ai_assistant')} className="px-3.5 py-2 rounded-xl bg-brand-600 text-white text-xs font-bold">Mở Trợ lý AI →</button>
                      </div>
                      <div className="space-y-3 text-xs">
                        <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 max-w-xl"><strong>🤖 EcoLogix Supervisor:</strong> Xin chào! Bạn muốn hỏi về tồn kho sắp hết hạn, chọn xe tối ưu tuyến Bình Dương hay xuất báo cáo ESG?</div>
                        <div className="bg-emerald-50 p-3.5 rounded-2xl border border-emerald-200 max-w-md ml-auto text-right font-semibold text-brand-900">Tối nay đi 5 đơn Bình Dương dùng xe nào rẻ nhất & ít CO₂ nhất?</div>
                        <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 max-w-xl"><strong>🚚 Route & 🌱 ESG Agent:</strong> Đề xuất <strong>Xe tải điện EV 1.5 Tấn</strong> — Quãng đường tối ưu <strong>42.8 km</strong> (-18%), <strong>0 kg CO₂ ống xả</strong>, tiết kiệm 245,000đ nhiên liệu.</div>
                      </div>
                      <div className="flex flex-wrap gap-2 pt-2">
                        <button onClick={() => onAskAi('Kho hàng hiện còn bao nhiêu sản phẩm và có mặt hàng nào sắp hết?')} className="px-3 py-2 rounded-xl bg-sky-50 hover:bg-sky-100 text-sky-800 text-xs font-bold">Thử hỏi tồn kho →</button>
                        <button onClick={() => onAskAi('Tối nay đi 5 đơn Bình Dương dùng xe nào rẻ nhất?')} className="px-3 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-brand-800 text-xs font-bold">Thử hỏi điều phối tuyến →</button>
                      </div>
                    </div>
                  )}

                  {activeShowcaseTab === 'reports' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      <div className="bg-gradient-to-br from-brand-700 to-emerald-900 text-white p-6 rounded-2xl shadow-md">
                        <span className="text-[10px] font-extrabold uppercase bg-white/20 px-2.5 py-1 rounded-full">GHG Protocol Scope 1</span>
                        <div className="font-mono text-4xl font-black mt-4">95.2% ESG</div>
                        <p className="text-xs text-emerald-100 mt-2">Giảm 18.7% phát thải CO₂ tương đương trồng mới 120 cây xanh mỗi tháng.</p>
                        <button onClick={() => onGoApp('reports')} className="mt-5 px-4 py-2 rounded-xl bg-white text-brand-800 font-bold text-xs">Xuất PDF & Excel Đa Sheet →</button>
                      </div>
                      <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-3 text-xs">
                        <h4 className="font-bold text-slate-900 text-sm">Tài liệu Báo cáo Tự động</h4>
                        <div className="p-3 rounded-xl bg-slate-50 flex justify-between items-center"><span>📄 Báo cáo ESG & Phát thải CO₂ (PDF ReportLab)</span><strong className="text-brand-600">Sẵn sàng</strong></div>
                        <div className="p-3 rounded-xl bg-slate-50 flex justify-between items-center"><span>📊 Sổ cái Tài chính & Tồn kho (Excel 5 Sheet)</span><strong className="text-brand-600">Sẵn sàng</strong></div>
                        <div className="p-3 rounded-xl bg-slate-50 flex justify-between items-center"><span>📈 Phân tích Độ nhạy Giá xăng & Thuế Carbon</span><strong className="text-brand-600">Real-time</strong></div>
                      </div>
                    </div>
                  )}

                  {activeShowcaseTab === 'inventory' && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-4 text-xs">
                      <div className="flex justify-between items-center">
                        <h4 className="font-bold text-slate-900 text-sm">Quản lý Kho Hàng & Cảnh báo Tồn kho An toàn (SQLite)</h4>
                        <button onClick={() => onGoApp('inventory')} className="px-3.5 py-2 rounded-xl bg-brand-600 text-white font-bold">Mở Quản lý Kho →</button>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200"><div className="text-slate-600">Kho Tổng Thủ Đức</div><div className="font-mono text-xl font-black text-brand-800 mt-1">82% Sức chứa</div></div>
                        <div className="p-4 rounded-xl bg-sky-50 border border-sky-200"><div className="text-slate-600">Hub Bình Dương</div><div className="font-mono text-xl font-black text-sky-800 mt-1">67% Sức chứa</div></div>
                        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200"><div className="text-amber-800 font-bold">Cảnh báo tồn thấp</div><div className="font-mono text-xl font-black text-amber-700 mt-1">3 SKU cần nhập</div></div>
                      </div>
                    </div>
                  )}

                  {activeShowcaseTab === 'settings' && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-4 text-xs">
                      <div className="flex justify-between items-center">
                        <div><h4 className="font-bold text-slate-900 text-sm">Cấu hình Tham số Vận hành Live-Code (`config.py`)</h4><p className="text-[11px] text-slate-500">Thay đổi giá nhiên liệu & giờ cấm tải áp dụng tức thì cho thuật toán VRP</p></div>
                        <button onClick={() => onGoApp('settings')} className="px-3.5 py-2 rounded-xl bg-brand-600 text-white font-bold">Mở Cấu hình →</button>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200"><div className="text-slate-500">Giá dầu DO</div><div className="font-mono text-lg font-black text-slate-900 mt-1">23,500 đ/L</div></div>
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200"><div className="text-slate-500">Thuế Carbon</div><div className="font-mono text-lg font-black text-slate-900 mt-1">500 đ/kg CO₂</div></div>
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200"><div className="text-slate-500">Giờ cấm tải nội đô</div><div className="font-mono text-lg font-black text-red-600 mt-1">16:00 – 18:00</div></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Value Proposition Section */}
        <section className="scroll-mt-24 py-16 bg-white" id="benefits">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100"><div className="w-12 h-12 rounded-2xl bg-emerald-100 text-brand-700 flex items-center justify-center text-xl mb-5"><i className="fa-solid fa-chart-pie"></i></div><h3 className="text-xl font-bold text-slate-900 mb-3">Tối ưu chi phí đến 22%</h3><p className="text-slate-600 text-sm mb-4">Cắt giảm quãng đường rỗng, loại bỏ vi phạm giờ cấm tải và tối ưu vòng quay tồn kho SMEs.</p></div>
            <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100"><div className="w-12 h-12 rounded-2xl bg-emerald-100 text-brand-700 flex items-center justify-center text-xl mb-5"><i className="fa-solid fa-seedling"></i></div><h3 className="text-xl font-bold text-slate-900 mb-3">Chuẩn hóa Báo cáo ESG</h3><p className="text-slate-600 text-sm mb-4">Tự động hạch toán phát thải CO₂ chuẩn GHG Protocol Scope 1, xuất báo cáo PDF & Excel đa sheet.</p></div>
            <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100"><div className="w-12 h-12 rounded-2xl bg-emerald-100 text-brand-700 flex items-center justify-center text-xl mb-5"><i className="fa-solid fa-microchip"></i></div><h3 className="text-xl font-bold text-slate-900 mb-3">Triển khai Nhanh trong 24h</h3><p className="text-slate-600 text-sm mb-4">Quy trình Onboarding 3 bước, cấu hình linh hoạt cho biến động giá xăng & thuế Carbon.</p></div>
          </div>
        </section>

        {/* Pricing Section (Module 01 Requirement) */}
        <section className="scroll-mt-24 py-16 bg-gradient-to-b from-white via-sky-50/50 to-emerald-50/35 border-t border-sky-100" id="pricing">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-10">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900">Bảng giá Dịch vụ SaaS Cho Doanh nghiệp SMEs</h2>
              <p className="text-sm text-slate-600 mt-2">Chi phí tối ưu, hoàn vốn chỉ sau 3 – 5 tháng vận hành.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { name: 'Gói Khởi Nghiệp', price: '1.5M', unit: 'đ/tháng', desc: '1–3 xe tải nhẹ • 50 đơn/ngày • Dự báo 7 ngày', rec: false },
                { name: 'Gói Tăng Trưởng Green', price: '3.8M', unit: 'đ/tháng', desc: '4–15 xe • LightGBM 30–90 ngày • Xuất ESG PDF/Excel', rec: true },
                { name: 'Gói Doanh Nghiệp', price: '8.5M', unit: 'đ/tháng', desc: 'Không giới hạn xe & kho • Multi-Agent API riêng • 24/7', rec: false }
              ].map((pkg, idx) => (
                <div key={idx} className={`rounded-3xl p-7 bg-white border ${pkg.rec ? 'border-2 border-brand-600 shadow-elevated relative' : 'border-slate-200 shadow-card'}`}>
                  {pkg.rec && <span className="absolute -top-3 left-6 bg-brand-600 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase">Phổ biến nhất</span>}
                  <div className="text-xs font-bold text-slate-500 uppercase">{pkg.name}</div>
                  <div className="text-3xl font-black text-slate-900 my-3">{pkg.price} <span className="text-sm font-medium text-slate-500">{pkg.unit}</span></div>
                  <p className="text-xs text-slate-600 mb-6">{pkg.desc}</p>
                  <button onClick={openStartPopup} className={`w-full py-2.5 rounded-xl text-xs font-bold transition ${pkg.rec ? 'bg-brand-600 text-white hover:bg-brand-700' : 'bg-slate-100 text-slate-800 hover:bg-slate-200'}`}>Chọn gói này</button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ & Contact Section (Module 01 Requirement) */}
        <section className="scroll-mt-24 py-16 bg-white border-t border-slate-200" id="contact">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-12 gap-10">
            <div className="lg:col-span-6 space-y-4">
              <h3 className="text-2xl font-extrabold text-slate-900">Câu hỏi thường gặp (FAQ)</h3>
              {[
                { q: 'Hệ thống có sử dụng dữ liệu và thuật toán thực tế không?', a: 'Có. EcoLogix AI chạy LightGBM 4.7.0 dự báo nhu cầu, giải thuật CVRPTW 2-Opt né giờ cấm tải nội đô và lưu trữ trên 24 bảng quan hệ SQLite.' },
                { q: 'Làm thế nào để thử nghiệm thay đổi giá xăng khi BGK yêu cầu?', a: 'Vào mục Cài đặt & Live-Code -> điều chỉnh Giá xăng, Thuế Carbon, Giờ cấm tải và bấm Ghi vào config.py để thấy độ nhạy chi phí ngay lập tức.' },
                { q: 'Trợ lý AI có cần Internet hay API ngoài mới chạy được không?', a: 'Hệ thống tích hợp Multi-Agent SQLite nội bộ chạy offline mượt mà, đồng thời cho phép cấu hình Gemini API Key trong phần Cài đặt.' }
              ].map((item, idx) => (
                <div key={idx} className="border border-slate-200 rounded-2xl p-4">
                  <button onClick={() => setFaqOpen(faqOpen === idx ? -1 : idx)} className="w-full flex justify-between items-center text-left font-bold text-sm text-slate-800">
                    <span>{item.q}</span>
                    <span>{faqOpen === idx ? '−' : '+'}</span>
                  </button>
                  {faqOpen === idx && <p className="text-xs text-slate-600 mt-2.5 leading-relaxed">{item.a}</p>}
                </div>
              ))}
            </div>

            <div className="lg:col-span-6 bg-gradient-to-br from-sky-50/70 via-white to-emerald-50/50 p-7 rounded-3xl border border-sky-100">
              <h3 className="text-xl font-extrabold text-slate-900 mb-2">Đặt lịch Tư vấn & Dùng thử 1-1</h3>
              <p className="text-xs text-slate-500 mb-4">Yêu cầu sẽ được gửi trực tiếp vào Trung tâm Thông báo của hệ thống.</p>
              <form onSubmit={sendContact} className="space-y-3">
                <input value={contactForm.name} onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })} placeholder="Họ tên / Tên doanh nghiệp *" className="w-full text-xs px-4 py-2.5 rounded-xl border border-slate-200 bg-white" required />
                <input value={contactForm.contact} onChange={(e) => setContactForm({ ...contactForm, contact: e.target.value })} placeholder="Số điện thoại hoặc Email *" className="w-full text-xs px-4 py-2.5 rounded-xl border border-slate-200 bg-white" required />
                <select value={contactForm.need} onChange={(e) => setContactForm({ ...contactForm, need: e.target.value })} className="w-full text-xs px-4 py-2.5 rounded-xl border border-slate-200 bg-white">
                  <option>Dùng thử miễn phí 14 ngày</option>
                  <option>Demo giải pháp tối ưu tuyến & ESG</option>
                  <option>Tư vấn gói Enterprise API</option>
                </select>
                <textarea value={contactForm.message} onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })} rows="3" placeholder="Ghi chú số lượng xe hoặc khu vực giao nhận..." className="w-full text-xs px-4 py-2.5 rounded-xl border border-slate-200 bg-white"></textarea>
                <button type="submit" className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold shadow-md">Gửi Yêu Cầu Tư Vấn</button>
              </form>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-slate-900 text-slate-400 text-xs py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2.5"><BrandLogo sizeClass="w-7 h-7" roundedClass="rounded-lg" /><span>© 2026 EcoLogix AI — Cuộc thi AI IN ECONOMICS 2026 (HCM-UTE). Khu Công nghệ Cao, TP. Thủ Đức, TP.HCM.</span></div>
          <div className="flex gap-5">
            <button onClick={() => onGoApp('dashboard')} className="hover:text-emerald-400">Dashboard</button>
            <button onClick={() => onGoApp('routing')} className="hover:text-emerald-400">Green Route</button>
            <button onClick={() => onGoApp('reports')} className="hover:text-emerald-400">Báo cáo ESG</button>
          </div>
        </div>
      </footer>

      {showStartModal && (
        <OnboardingView
          isModal={true}
          user={user}
          toast={toast}
          showToast={showToast}
          onBack={() => setShowStartModal(false)}
          onGoLogin={() => { setShowStartModal(false); onLogin(); }}
          onFinish={(newComp) => {
            setShowStartModal(false);
            if (onOnboardingComplete) onOnboardingComplete(newComp);
            else onGoApp('dashboard');
          }}
        />
      )}
    </div>
  );
}

Object.assign(window, { LandingView });
