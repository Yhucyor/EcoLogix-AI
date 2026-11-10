const { useState, useEffect, useRef, useMemo } = React;

// ==================== API HELPER ====================
async function apiFetch(url, options = {}) {
  const cfg = {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  };
  const res = await fetch(url, cfg);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Lỗi kết nối (${res.status})`);
  }
  return data;
}

const fmtVnd = (n) => Number(n || 0).toLocaleString('vi-VN') + ' đ';

function EmptyState({ title = 'Chưa có dữ liệu', subtitle = 'Hãy thêm bản ghi mới hoặc điều chỉnh bộ lọc.' }) {
  return (
    <div className="bg-white border border-dashed border-slate-300 rounded-2xl p-8 text-center">
      <div className="text-3xl mb-2">📭</div>
      <div className="font-bold text-sm text-text-main">{title}</div>
      <div className="text-xs text-text-sub mt-1">{subtitle}</div>
    </div>
  );
}

function PaginationBar({ total, page, pageSize, onPage }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between pt-3 text-xs text-text-sub">
      <span>Hiển thị trang <strong>{page}</strong> / {totalPages} (Tổng {total} mục)</span>
      <div className="flex gap-1.5">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="px-3 py-1 rounded-lg border border-border-light bg-white disabled:opacity-40 hover:bg-canvas font-semibold">← Trước</button>
        <button disabled={page >= totalPages} onClick={() => onPage(page + 1)} className="px-3 py-1 rounded-lg border border-border-light bg-white disabled:opacity-40 hover:bg-canvas font-semibold">Sau →</button>
      </div>
    </div>
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

Object.assign(window, { apiFetch, fmtVnd, EmptyState, PaginationBar, BrandLogo });
