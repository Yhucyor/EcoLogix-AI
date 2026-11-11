const { useState, useEffect, useRef, useMemo } = React;

// ==================== REUSABLE LEAFLET MAP (ĐA CHẾ ĐỘ HIỂN THỊ & BÁM ĐƯỜNG THỰC TẾ OSM/OSRM) ====================
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

const ROAD_GEOM_CACHE = {};

function routeCoordKey(depot, stops) {
  const pts = [depot, ...(stops || []), depot].filter((p) => p && Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng)));
  return pts.map((p) => `${Number(p.lat).toFixed(5)},${Number(p.lng).toFixed(5)}`).join(';');
}

function parseHeightPx(heightClass) {
  if (!heightClass || /(?:sm:|md:|lg:|xl:|clamp)/.test(heightClass)) return undefined;
  const m = /h-\[(\d+)px\]/.exec(heightClass);
  return m ? `${m[1]}px` : '320px';
}

function EcoLeafletMap({
  depot = { lat: 10.8505, lng: 106.7718, name: 'Kho Tổng EcoLogix (TP. Thủ Đức)' },
  routes = [], // Mảng [{ color, geometry?: [[lat, lng], ...], stops: [{ lat, lng, label, popup }] }]
  showRestrictedZone = false,
  heightClass = 'h-[320px]',
  defaultTheme = 'osm',
  zoom = 11,
  openDepotPopup = true,
}) {
  const [theme, setTheme] = useState(defaultTheme);
  const [fallbackNotice, setFallbackNotice] = useState(false);
  const [snappedGeoms, setSnappedGeoms] = useState({});
  const [snappingRoads, setSnappingRoads] = useState(false);
  const containerRef = useRef(null);
  const mapObjRef = useRef(null);
  const baseLayersRef = useRef({});
  const overlayGroupRef = useRef(null);
  const lastPopupSigRef = useRef('');
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

  // 2b. Tự động khớp lộ trình theo đường bộ thực tế (OSRM qua backend cache) khi route chưa có geometry sẵn
  useEffect(() => {
    const list = routes || [];
    const needed = [];
    const nextCached = {};
    list.forEach((rt) => {
      const stops = rt.stops || [];
      if (!stops.length) return;
      if (Array.isArray(rt.geometry) && rt.geometry.length >= 2) return;
      const key = routeCoordKey(depot, stops);
      if (ROAD_GEOM_CACHE[key]) {
        nextCached[key] = ROAD_GEOM_CACHE[key];
      } else {
        needed.push({ key, stops });
      }
    });

    if (Object.keys(nextCached).length > 0) {
      setSnappedGeoms((prev) => ({ ...prev, ...nextCached }));
    }
    if (!needed.length) {
      setSnappingRoads(false);
      return;
    }

    let cancelled = false;
    setSnappingRoads(true);
    Promise.all(
      needed.map(async ({ key, stops }) => {
        try {
          const coords = [
            { lat: Number(depot.lat), lng: Number(depot.lng) },
            ...stops.map((s) => ({ lat: Number(s.lat), lng: Number(s.lng) })),
            { lat: Number(depot.lat), lng: Number(depot.lng) },
          ];
          const resp = await fetch('/api/routing/road-geometry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ coordinates: coords }),
          });
          if (!resp.ok) return null;
          const data = await resp.json();
          if (data && data.snapped && Array.isArray(data.points) && data.points.length >= 2) {
            ROAD_GEOM_CACHE[key] = data.points;
            return { key, points: data.points };
          }
        } catch {}
        return null;
      })
    ).then((items) => {
      if (cancelled) return;
      const additions = {};
      items.forEach((it) => {
        if (it) additions[it.key] = it.points;
      });
      if (Object.keys(additions).length > 0) {
        setSnappedGeoms((prev) => ({ ...prev, ...additions }));
      }
      setSnappingRoads(false);
    });

    return () => {
      cancelled = true;
    };
  }, [dataSignature]);

  // 3. Vẽ Depot, Vùng cấm tải và các Tuyến đường khớp đường bộ (Halo + Đường phố + Ghim đánh số)
  useEffect(() => {
    const map = mapObjRef.current;
    const group = overlayGroupRef.current;
    if (!map || !group || typeof L === 'undefined') return;

    group.clearLayers();
    const boundsPts = [[depot.lat, depot.lng]];
    const coordCounts = {};

    const depotIcon = L.divIcon({
      className: 'eco-pin-icon',
      html: '<div style="width:28px;height:28px;border-radius:50%;background:#DC2626;border:3px solid #FFFFFF;box-shadow:0 3px 10px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;color:#FFF;font-size:12px;">🏭</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14],
    });
    const depotMarker = L.marker([depot.lat, depot.lng], { icon: depotIcon, zIndexOffset: 500 })
      .addTo(group)
      .bindPopup(`<div style="font-size:12px;"><b>${depot.name}</b><br/>Điểm xuất phát & Tập kết</div>`, { autoPan: false });
    if (openDepotPopup && lastPopupSigRef.current !== dataSignature) {
      depotMarker.openPopup();
      lastPopupSigRef.current = dataSignature;
    }

    if (showRestrictedZone) {
      L.polygon(
        [[10.795, 106.675], [10.79, 106.705], [10.76, 106.71], [10.745, 106.66], [10.765, 106.65]],
        { color: '#EF4444', weight: 1.8, fillColor: '#EF4444', fillOpacity: 0.12 }
      ).addTo(group).bindPopup('<b>Vùng nội đô hạn chế giờ cấm tải</b>');
    }

    (routes || []).forEach((rt) => {
      const stops = rt.stops || [];
      if (!stops.length) return;
      const color = rt.color || '#059669';
      const key = routeCoordKey(depot, stops);
      const customGeo = Array.isArray(rt.geometry) && rt.geometry.length >= 2 ? rt.geometry : null;
      const asyncGeo = snappedGeoms[key] && snappedGeoms[key].length >= 2 ? snappedGeoms[key] : null;
      const snappedPts = customGeo || asyncGeo;
      const fallbackPts = [[depot.lat, depot.lng], ...stops.map((s) => [s.lat, s.lng]), [depot.lat, depot.lng]];

      if (snappedPts) {
        L.polyline(snappedPts, {
          color: '#FFFFFF',
          weight: 6.5,
          opacity: 0.82,
          lineJoin: 'round',
          lineCap: 'round',
        }).addTo(group);
        L.polyline(snappedPts, {
          color,
          weight: 4.2,
          opacity: 0.94,
          lineJoin: 'round',
          lineCap: 'round',
        }).addTo(group);
        for (let idx = 0; idx < snappedPts.length; idx += Math.max(1, Math.floor(snappedPts.length / 40))) {
          boundsPts.push(snappedPts[idx]);
        }
      } else {
        L.polyline(fallbackPts, {
          color,
          weight: 2.8,
          opacity: 0.55,
          dashArray: '6, 8',
        }).addTo(group);
      }

      const showNumbered = stops.length <= 25;
      stops.forEach((s, idx) => {
        const ck = `${Number(s.lat).toFixed(5)},${Number(s.lng).toFixed(5)}`;
        const dupIdx = coordCounts[ck] || 0;
        coordCounts[ck] = dupIdx + 1;
        let pinLat = Number(s.lat);
        let pinLng = Number(s.lng);
        if (dupIdx > 0) {
          const angle = dupIdx * 2.1;
          const radiusDeg = 0.00022 * Math.ceil(dupIdx / 3);
          pinLat += Math.sin(angle) * radiusDeg;
          pinLng += Math.cos(angle) * radiusDeg;
        }
        boundsPts.push([pinLat, pinLng]);
        const popupHtml = s.popup || `<b>Điểm #${idx + 1}</b><br/>${s.label || ''}`;

        if (showNumbered) {
          const pinIcon = L.divIcon({
            className: 'eco-stop-pin',
            html: `<div style="width:22px;height:22px;border-radius:50%;background:${color};border:2px solid #FFFFFF;box-shadow:0 2px 6px rgba(15,23,42,0.35);display:flex;align-items:center;justify-content:center;color:#FFFFFF;font-size:10px;font-weight:800;">${idx + 1}</div>`,
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -11],
          });
          L.marker([pinLat, pinLng], { icon: pinIcon, zIndexOffset: 200 + idx })
            .addTo(group)
            .bindPopup(popupHtml);
        } else {
          L.circleMarker([pinLat, pinLng], {
            radius: 5.5,
            color: '#FFFFFF',
            weight: 2,
            fillColor: color,
            fillOpacity: 1,
          }).addTo(group).bindPopup(popupHtml);
        }
      });
    });

    if (boundsPts.length > 1) {
      try {
        map.fitBounds(L.latLngBounds(boundsPts), { padding: [32, 32], maxZoom: 14 });
      } catch {}
    }
    setTimeout(() => map.invalidateSize(), 120);
  }, [dataSignature, snappedGeoms]);

  const themeExtraClass = MAP_THEMES[theme]?.containerClass || '';
  const hasRoutes = (routes || []).some((rt) => (rt.stops || []).length > 0);
  const allRoutesSnapped =
    hasRoutes &&
    (routes || []).every((rt) => {
      if (!(rt.stops || []).length) return true;
      if (Array.isArray(rt.geometry) && rt.geometry.length >= 2) return true;
      const key = routeCoordKey(depot, rt.stops);
      return Boolean(snappedGeoms[key] && snappedGeoms[key].length >= 2);
    });

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
        <div className="flex flex-wrap items-center gap-1.5">
          {hasRoutes && (
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                snappingRoads
                  ? 'text-amber-700 bg-amber-50 border-amber-200'
                  : allRoutesSnapped
                    ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                    : 'text-slate-600 bg-slate-50 border-slate-200'
              }`}
            >
              {snappingRoads ? '⏳ Đang khớp đường phố...' : allRoutesSnapped ? '🛣️ Bám sát đường bộ OSM' : '📍 Tuyến trực tiếp'}
            </span>
          )}
          {fallbackNotice && theme === 'osm' && (
            <span className="text-[10px] font-semibold text-sky-700 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded-full">
              Đang dùng OSM Mirror (.de)
            </span>
          )}
        </div>
      </div>
      <div
        ref={containerRef}
        className={`${heightClass} ${themeExtraClass} w-full rounded-xl border border-slate-200 shadow-inner relative`}
        style={{ ...(resolvedHeight ? { height: resolvedHeight } : {}), minHeight: '220px', width: '100%' }}
      ></div>
    </div>
  );
}

Object.assign(window, { MAP_THEMES, parseHeightPx, EcoLeafletMap });
