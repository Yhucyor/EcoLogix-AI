const { useState, useEffect, useRef, useMemo } = React;

// ==================== REUSABLE LEAFLET MAP (ĐA CHẾ ĐỘ HIỂN THỊ & AUTO-FALLBACK) ====================
const MAP_THEMES = {
  osm: {
    label: '🗺️ Chuẩn OSM',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    fallbackUrl: 'https://tile.openstreetmap.de/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  },
  voyager: {
    label: '🛣️ Đường phố',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19,
  },
  dark: {
    label: '🌑 Dark Mode',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19,
  },
  satellite: {
    label: '🛰️ Vệ tinh',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{x}/{y}',
    attribution: 'Tiles &copy; Esri World Imagery',
    maxZoom: 18,
  },
  toner: {
    label: '🖤 Stamen / Tương phản',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO (Stamen Toner style)',
    maxZoom: 19,
    containerClass: 'eco-map-toner',
  },
  terrain: {
    label: '⛰️ Địa hình',
    url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap (CC-BY-SA)',
    maxZoom: 17,
  },
  light: {
    label: '✨ Tối giản',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19,
  },
};

function parseHeightPx(heightClass) {
  const m = /h-\[(\d+)px\]/.exec(heightClass || '');
  return m ? `${m[1]}px` : '320px';
}

function EcoLeafletMap({
  depot = { lat: 10.8505, lng: 106.7718, name: 'Kho Tổng EcoLogix (TP. Thủ Đức)' },
  routes = [], // Mảng [{ color, stops: [{ lat, lng, label, popup }] }]
  showRestrictedZone = false,
  heightClass = 'h-[320px]',
  defaultTheme = 'osm',
  zoom = 11,
  openDepotPopup = true,
}) {
  const [theme, setTheme] = useState(defaultTheme);
  const [fallbackNotice, setFallbackNotice] = useState(false);
  const containerRef = useRef(null);
  const mapObjRef = useRef(null);
  const baseLayersRef = useRef({});
  const overlayGroupRef = useRef(null);
  const resolvedHeight = useMemo(() => parseHeightPx(heightClass), [heightClass]);
  const dataSignature = useMemo(
    () => JSON.stringify({ depot, routes, showRestrictedZone }),
    [depot, routes, showRestrictedZone]
  );

  // 1. Khởi tạo bản đồ Leaflet chuẩn Quick-Start + Auto-Fallback + ResizeObserver + Layer switcher
  useEffect(() => {
    if (!containerRef.current || typeof L === 'undefined') return;
    const map = L.map(containerRef.current, { zoomControl: true }).setView([depot.lat, depot.lng], zoom);
    mapObjRef.current = map;

    const layersByKey = {};
    const layersByLabel = {};
    Object.entries(MAP_THEMES).forEach(([k, cfg]) => {
      const layer = L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: cfg.maxZoom });
      if (cfg.fallbackUrl) {
        let switchedFallback = false;
        layer.on('tileerror', () => {
          if (!switchedFallback) {
            switchedFallback = true;
            layer.setUrl(cfg.fallbackUrl);
            setFallbackNotice(true);
          }
        });
      }
      layersByKey[k] = layer;
      layersByLabel[cfg.label] = layer;
    });
    baseLayersRef.current = layersByKey;

    const initialLayer = layersByKey[theme] || layersByKey.osm;
    initialLayer.addTo(map);

    L.control.layers(layersByLabel, null, { position: 'topright' }).addTo(map);
    map.on('baselayerchange', (e) => {
      const found = Object.entries(MAP_THEMES).find(([, cfg]) => cfg.label === e.name);
      if (found) setTheme(found[0]);
    });

    overlayGroupRef.current = L.layerGroup().addTo(map);

    const t1 = setTimeout(() => map.invalidateSize(), 150);
    const t2 = setTimeout(() => map.invalidateSize(), 550);
    let ro = null;
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => map.invalidateSize());
      ro.observe(containerRef.current);
    }

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      if (ro) ro.disconnect();
      map.remove();
      mapObjRef.current = null;
      baseLayersRef.current = {};
    };
  }, []);

  // 2. Đồng bộ chế độ hiển thị giữa nút pill bên ngoài và L.control.layers
  useEffect(() => {
    const map = mapObjRef.current;
    const layers = baseLayersRef.current;
    if (!map || !layers[theme]) return;
    Object.entries(layers).forEach(([k, layer]) => {
      if (k === theme) {
        if (!map.hasLayer(layer)) layer.addTo(map);
      } else {
        if (map.hasLayer(layer)) map.removeLayer(layer);
      }
    });
  }, [theme]);

  // 3. Vẽ Depot, Vùng cấm tải và các Tuyến đường (chỉ vẽ lại khi dữ liệu thay đổi thực sự)
  useEffect(() => {
    const map = mapObjRef.current;
    const group = overlayGroupRef.current;
    if (!map || !group || typeof L === 'undefined') return;

    group.clearLayers();
    const boundsPts = [[depot.lat, depot.lng]];

    const depotIcon = L.divIcon({
      className: 'eco-pin-icon',
      html: '<div style="width:28px;height:28px;border-radius:50%;background:#DC2626;border:3px solid #FFFFFF;box-shadow:0 3px 10px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;color:#FFF;font-size:12px;">🏭</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14],
    });
    const depotMarker = L.marker([depot.lat, depot.lng], { icon: depotIcon })
      .addTo(group)
      .bindPopup(`<div style="font-size:12px;"><b>${depot.name}</b><br/>Điểm xuất phát & Tập kết</div>`);
    if (openDepotPopup) depotMarker.openPopup();

    if (showRestrictedZone) {
      L.polygon(
        [[10.795, 106.675], [10.79, 106.705], [10.76, 106.71], [10.745, 106.66], [10.765, 106.65]],
        { color: '#EF4444', weight: 1.8, fillColor: '#EF4444', fillOpacity: 0.14 }
      ).addTo(group).bindPopup('<b>Vùng nội đô hạn chế giờ cấm tải</b>');
    }

    (routes || []).forEach((rt) => {
      const stops = rt.stops || [];
      if (!stops.length) return;
      const color = rt.color || '#059669';
      const polyPts = [[depot.lat, depot.lng], ...stops.map((s) => [s.lat, s.lng]), [depot.lat, depot.lng]];
      L.polyline(polyPts, { color, weight: 4, opacity: 0.9 }).addTo(group);

      stops.forEach((s, idx) => {
        boundsPts.push([s.lat, s.lng]);
        L.circleMarker([s.lat, s.lng], {
          radius: 6,
          color: '#FFFFFF',
          weight: 2,
          fillColor: color,
          fillOpacity: 1,
        }).addTo(group).bindPopup(s.popup || `<b>Điểm #${idx + 1}</b><br/>${s.label || ''}`);
      });
    });

    if (boundsPts.length > 1) {
      try {
        map.fitBounds(L.latLngBounds(boundsPts), { padding: [32, 32], maxZoom: 13 });
      } catch {}
    }
    setTimeout(() => map.invalidateSize(), 120);
  }, [dataSignature]);

  const themeExtraClass = MAP_THEMES[theme]?.containerClass || '';

  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <div className="flex flex-wrap items-center gap-1.5">
          {Object.entries(MAP_THEMES).map(([k, cfg]) => (
            <button
              key={k}
              type="button"
              onClick={() => setTheme(k)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition border ${
                theme === k
                  ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                  : 'bg-canvas text-slate-600 border-border-light hover:bg-sky-50 hover:text-brand-700'
              }`}
            >
              {cfg.label}
            </button>
          ))}
        </div>
        {fallbackNotice && theme === 'osm' && (
          <span className="text-[10px] font-semibold text-sky-700 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded-full">
            Đang dùng OSM Mirror (.de)
          </span>
        )}
      </div>
      <div
        ref={containerRef}
        className={`${heightClass} ${themeExtraClass} w-full rounded-xl border border-slate-200 shadow-inner relative`}
        style={{ height: resolvedHeight, minHeight: '220px', width: '100%' }}
      ></div>
    </div>
  );
}

Object.assign(window, { MAP_THEMES, parseHeightPx, EcoLeafletMap });
