const { useState, useEffect, useRef, useMemo } = React;

// ==================== AUTH STORAGE HELPERS ====================
function getAuthToken() {
  try {
    return localStorage.getItem('ecologix_token') || sessionStorage.getItem('ecologix_token') || '';
  } catch {
    return '';
  }
}

function getStoredUser() {
  try {
    const raw = localStorage.getItem('ecologix_user') || sessionStorage.getItem('ecologix_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveAuthSession(user, token, remember = true) {
  try {
    clearAuthSession();
    const store = remember ? localStorage : sessionStorage;
    if (user) store.setItem('ecologix_user', JSON.stringify(user));
    if (token) store.setItem('ecologix_token', token);
  } catch {}
}

function clearAuthSession() {
  try {
    localStorage.removeItem('ecologix_user');
    localStorage.removeItem('ecologix_token');
    sessionStorage.removeItem('ecologix_user');
    sessionStorage.removeItem('ecologix_token');
  } catch {}
}

// ==================== API HELPER ====================
async function apiFetch(url, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const res = await fetch(url, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !url.startsWith('/api/auth/login')) {
    window.dispatchEvent(new CustomEvent('ecologix:unauthorized'));
  }
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Lỗi kết nối (${res.status})`);
  }
  return data;
}

async function downloadAuthorizedFile(url, fallbackFilename) {
  const token = getAuthToken();
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Không thể tải file (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = fallbackFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
}

const fmtVnd = (n) => Number(n || 0).toLocaleString('vi-VN') + ' đ';

// ==================== SHARED UI COMPONENTS ====================
function EmptyState({ title = 'Chưa có dữ liệu', subtitle = 'Hãy thêm bản ghi mới hoặc điều chỉnh bộ lọc.' }) {
  return (
    <div className="bg-white/90 border border-dashed border-sky-200 rounded-3xl p-8 text-center">
      <div className="text-3xl mb-2">📭</div>
      <div className="font-bold text-sm text-slate-900">{title}</div>
      <div className="text-xs text-slate-500 mt-1">{subtitle}</div>
    </div>
  );
}

function LoadingSkeleton({ rows = 3, label = 'Đang tải dữ liệu...' }) {
  return (
    <div className="bg-white/95 rounded-3xl border border-sky-100 p-6 space-y-4 shadow-card">
      <div className="flex items-center gap-2 text-xs font-bold text-brand-700">
        <span className="w-2 h-2 rounded-full bg-brand-500 pulse-dot"></span>
        <span>{label}</span>
      </div>
      <div className="space-y-3 animate-pulse">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-10 bg-sky-50/90 rounded-2xl border border-sky-100/70"></div>
        ))}
      </div>
    </div>
  );
}

function PaginationBar({ total, page, pageSize, onPage }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between pt-3 text-xs text-slate-500">
      <span>Hiển thị trang <strong>{page}</strong> / {totalPages} (Tổng {total} mục)</span>
      <div className="flex gap-1.5">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="px-3.5 py-1.5 rounded-full border border-sky-200 bg-white disabled:opacity-40 hover:bg-sky-50 font-semibold transition">← Trước</button>
        <button disabled={page >= totalPages} onClick={() => onPage(page + 1)} className="px-3.5 py-1.5 rounded-full border border-sky-200 bg-white disabled:opacity-40 hover:bg-sky-50 font-semibold transition">Sau →</button>
      </div>
    </div>
  );
}

function ModalShell({ open, title, onClose, maxWidth = 'max-w-lg', children }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape' && onClose) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div onClick={onClose} className="fixed inset-0 z-[70] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div onClick={(e) => e.stopPropagation()} className={`bg-white rounded-3xl border border-sky-100 shadow-2xl w-full ${maxWidth} overflow-hidden my-auto`}>
        <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-sky-50 via-white to-emerald-50 border-b border-sky-100">
          <h4 className="font-extrabold text-base text-slate-900 m-0">{title}</h4>
          <button type="button" onClick={onClose} className="w-8 h-8 rounded-full bg-white hover:bg-slate-100 border border-slate-200 text-slate-500 text-xs font-bold flex items-center justify-center">✕</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function ConfirmModal({ open, title = 'Xác nhận thao tác', message, confirmText = 'Xác nhận xóa', danger = true, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <ModalShell open={open} title={title} onClose={onCancel} maxWidth="max-w-md">
      <p className="text-xs text-slate-600 leading-relaxed mb-5">{message}</p>
      <div className="flex gap-3 justify-end">
        <button type="button" onClick={onCancel} className="px-5 py-2.5 rounded-full border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50 transition">Hủy bỏ</button>
        <button
          type="button"
          onClick={onConfirm}
          className={`px-5 py-2.5 rounded-full text-white text-xs font-bold shadow-md transition ${
            danger ? 'bg-red-600 hover:bg-red-700' : 'bg-gradient-to-r from-brand-600 to-emerald-500'
          }`}
        >
          {confirmText}
        </button>
      </div>
    </ModalShell>
  );
}

// ==================== BRAND LOGO COMPONENT ====================
function BrandLogo({ sizeClass = 'w-10 h-10', roundedClass = 'rounded-xl', className = '' }) {
  return (
    <div className={`${sizeClass} ${roundedClass} bg-white/95 border border-emerald-100/80 p-1 flex items-center justify-center shadow-sm overflow-hidden flex-shrink-0 ${className}`}>
      <img
        src="/assets/ecologix-logo.png?v=2"
        alt="EcoLogix AI Logo"
        className="w-full h-full object-contain"
      />
    </div>
  );
}

Object.assign(window, {
  getAuthToken,
  getStoredUser,
  saveAuthSession,
  clearAuthSession,
  apiFetch,
  downloadAuthorizedFile,
  fmtVnd,
  EmptyState,
  LoadingSkeleton,
  PaginationBar,
  ModalShell,
  ConfirmModal,
  BrandLogo,
});
