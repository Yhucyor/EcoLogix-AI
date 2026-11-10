const { useState, useEffect, useRef, useMemo } = React;

// ==================== 17. MOBILE DEMO VIEW ====================
function MobileDemoView({ onBackDesktop }) {
  return (
    <div className="min-h-screen bg-slate-900 p-8 text-white">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8 pb-4 border-b border-slate-800">
          <div><h2 className="text-2xl font-extrabold m-0">📱 Trình Diễn Giao Diện Responsive Mobile</h2><p className="text-xs text-slate-400 mt-1">Tái hiện 3 màn hình di động từ bản thiết kế UI/UX chuẩn</p></div>
          <button onClick={onBackDesktop} className="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl text-xs font-bold">← Quay lại Desktop</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 justify-items-center">
          <div className="w-[300px] h-[580px] bg-white text-text-main rounded-[36px] p-5 border-[7px] border-slate-700 shadow-2xl flex flex-col justify-between">
            <div className="text-center pt-2"><BrandLogo sizeClass="w-10 h-10" roundedClass="rounded-xl" className="mx-auto mb-1" /><strong className="text-sm text-brand-900">EcoLogix AI</strong><p className="text-[10px] text-text-sub">Smart Logistics. Greener Future.</p></div>
            <div className="my-auto text-center"><img src="https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=400" alt="Truck" className="w-full h-32 object-cover rounded-xl mb-4" /><button onClick={onBackDesktop} className="w-full bg-brand-600 text-white py-2.5 rounded-xl text-xs font-bold">Vào ứng dụng</button></div>
            <div className="text-center text-[10px] text-slate-400 pb-2">AI in Economics 2026</div>
          </div>
          <div className="w-[300px] h-[580px] bg-canvas text-text-main rounded-[36px] p-5 border-[7px] border-slate-700 shadow-2xl flex flex-col justify-between">
            <div><div className="flex justify-between items-center mb-4"><span>☰</span><strong className="text-sm">Tổng quan</strong><span>👤</span></div><div className="bg-white p-4 rounded-2xl border border-border-light mb-3"><div className="text-xs text-text-sub font-bold">Giảm CO₂</div><div className="font-mono text-2xl font-extrabold">18.7%</div></div><div className="bg-white p-4 rounded-2xl border border-border-light"><div className="text-xs font-bold mb-2">Hiệu suất kho</div><div className="h-24 bg-emerald-50 rounded-xl flex items-center justify-center text-xs text-brand-700 font-bold">📈 94.4% An toàn</div></div></div>
            <div className="text-center text-[10px] text-slate-400 pb-2">TP.HCM - Bình Dương Hub</div>
          </div>
          <div className="w-[300px] h-[580px] bg-white text-text-main rounded-[36px] p-5 border-[7px] border-slate-700 shadow-2xl flex flex-col justify-between">
            <div><div className="flex justify-between items-center mb-4"><span>☰</span><strong className="text-sm">Trợ lý AI</strong><span>🔔</span></div><div className="space-y-3 text-[11px]"><div className="bg-canvas p-3 rounded-xl border border-border-light">Xin chào! Tôi là EcoLogix AI 🤖</div><div className="bg-emerald-100 p-3 rounded-xl font-semibold text-right">Tối nay đi 5 đơn Bình Dương?</div><div className="bg-canvas p-3 rounded-xl border border-border-light">✅ Chọn Xe Điện EV 1.2T #04 (Tiết kiệm 22%)</div></div></div>
            <button onClick={onBackDesktop} className="w-full bg-brand-600 text-white py-2 rounded-xl text-xs font-bold">Mở chat đầy đủ</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { MobileDemoView });
