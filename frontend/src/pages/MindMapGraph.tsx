import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ActivateResult, GraphNode } from "../types";
import { MODALITY_CONFIG } from "../types";
import { imageUrl } from "../api";

/** 思维导图式召回图谱: 左→右三列 (中心实体 → 相关实体 → 模态分组) */

const GROUP_ORDER = ["TXT", "TBL", "IMG", "SEQ", "KNW"] as const;
const GROUP_NAME: Record<string, string> = {
  TXT: "文本章节", TBL: "表格", IMG: "图片", SEQ: "时序流程", KNW: "专家知识",
};

interface Link {
  key: string;
  path: string;
  color: string;
  strong: boolean;
}

interface Props {
  result: ActivateResult;
  graphKey: string;
  selectedId: string | null;
  hiddenTypes?: Set<string>;
  onSelect: (n: GraphNode) => void;
  onDblSelect: (n: GraphNode) => void;
}

const MindMapGraph: React.FC<Props> = ({ result, graphKey, selectedId, hiddenTypes, onSelect, onDblSelect }) => {
  const [links, setLinks] = useState<Link[]>([]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [canvasSize, setCanvasSize] = useState({ w: 0, h: 0 });
  const scrollRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const sizerRef = useRef<HTMLDivElement>(null);
  const elRefs = useRef<Map<string, HTMLElement>>(new Map());
  const zoomRef = useRef(1);
  zoomRef.current = zoom;

  const center = result.center!;
  const related = result.related_entities ?? [];
  const groups = result.groups ?? {};

  const setRef = useCallback((id: string) => (el: HTMLElement | null) => {
    if (el) elRefs.current.set(id, el);
    else elRefs.current.delete(id);
  }, []);

  /** 同步画布布局尺寸 → sizer/svg */
  const syncSize = useCallback(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const w = cv.offsetWidth, h = cv.offsetHeight;
    setCanvasSize((s) => (s.w === w && s.h === h ? s : { w, h }));
    const sz = sizerRef.current;
    if (sz) {
      sz.style.width = `${w * zoomRef.current}px`;
      sz.style.height = `${h * zoomRef.current}px`;
    }
  }, []);

  /** 计算连线: 中心→实体, 实体→分组 (坐标除以zoom回到布局空间) */
  const computeLinks = useCallback(() => {
    if (!canvasRef.current) return;
    const wrap = canvasRef.current.getBoundingClientRect();
    const z = zoomRef.current || 1;
    const out: Link[] = [];
    const rectOf = (id: string) => {
      const el = elRefs.current.get(id);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        x1: (r.left - wrap.left + r.width) / z, y1: (r.top - wrap.top + r.height / 2) / z,
        x2: (r.left - wrap.left) / z, y2: (r.top - wrap.top + r.height / 2) / z,
      };
    };
    // 中心→相关实体
    for (const r of related) {
      const rc = rectOf(r.id);
      if (!rc) continue;
      const direct = r.rel === "问题直接命中";
      out.push({
        key: `c-${r.id}`,
        path: bezier(rc.x1, rc.y1, rc.x2, rc.y2),
        color: direct ? "#2563EB" : "#93b4f8",
        strong: direct,
      });
    }
    // 实体(含中心)→模态分组
    for (const mod of GROUP_ORDER) {
      const gid = `grp-${mod}`;
      const list = groups[mod] ?? [];
      if (list.length === 0 || collapsed.has(mod) || hiddenTypes?.has(mod)) continue;
      const viaIds = new Set<string>([center.id]);
      for (const n of list) {
        if (n.via) viaIds.add(n.via);
      }
      for (const vid of viaIds) {
        const rv = rectOf(vid);
        const rg = rectOf(gid);
        if (!rv || !rg) continue;
        out.push({
          key: `g-${mod}-${vid}`,
          path: bezier(rv.x1, rv.y1, rg.x2, rg.y2),
          color: MODALITY_CONFIG[mod].color + "99",
          strong: false,
        });
      }
    }
    setLinks(out);
  }, [related, groups, center.id, collapsed, hiddenTypes]);

  useLayoutEffect(() => {
    syncSize();
    computeLinks();
    const ro = new ResizeObserver(() => {
      syncSize();
      computeLinks();
    });
    if (canvasRef.current) ro.observe(canvasRef.current);
    const t = setTimeout(() => { syncSize(); computeLinks(); }, 400); // 图片加载后再算一次
    return () => { ro.disconnect(); clearTimeout(t); };
  }, [computeLinks, syncSize, graphKey]);

  useEffect(() => { computeLinks(); }, [collapsed, computeLinks]);
  useEffect(() => { syncSize(); }, [zoom, syncSize]);

  /** Ctrl+滚轮: 光标中心缩放 */
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      const oldZ = zoomRef.current;
      const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      const nz = Math.min(1.8, Math.max(0.5, oldZ * factor));
      if (Math.abs(nz - oldZ) < 1e-4) return;
      const rect = el.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      // 内容坐标(布局空间)
      const cx = (el.scrollLeft + mx) / oldZ;
      const cy = (el.scrollTop + my) / oldZ;
      setZoom(nz);
      requestAnimationFrame(() => {
        el.scrollLeft = cx * nz - mx;
        el.scrollTop = cy * nz - my;
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const zoomBy = (factor: number) => {
    const el = scrollRef.current;
    const oldZ = zoomRef.current;
    const nz = Math.min(1.8, Math.max(0.5, oldZ * factor));
    if (Math.abs(nz - oldZ) < 1e-4) return;
    if (el) {
      const cx = (el.scrollLeft + el.clientWidth / 2) / oldZ;
      const cy = (el.scrollTop + el.clientHeight / 2) / oldZ;
      setZoom(nz);
      requestAnimationFrame(() => {
        el.scrollLeft = cx * nz - el.clientWidth / 2;
        el.scrollTop = cy * nz - el.clientHeight / 2;
      });
    } else setZoom(nz);
  };

  const toggleGroup = (mod: string) => {
    setCollapsed((s) => {
      const n = new Set(s);
      if (n.has(mod)) n.delete(mod); else n.add(mod);
      return n;
    });
  };

  const nContent = (result.stats?.n_content) ?? 0;

  return (
    <div className="mm-scroll" key={graphKey} ref={scrollRef}>
      <div className="mm-sizer" ref={sizerRef}>
        <div className="mm-canvas" ref={canvasRef}
             style={{ transform: `scale(${zoom})`, transformOrigin: "0 0" }}>
          {/* 连线层 */}
          <svg className="mm-links" width={canvasSize.w} height={canvasSize.h}>
            {links.map((l) => (
              <path key={l.key} d={l.path} fill="none"
                    stroke={hoverKey === l.key ? "#2563EB" : l.color}
                    strokeWidth={hoverKey === l.key ? 2.6 : l.strong ? 1.8 : 1.2}
                    opacity={hoverKey && hoverKey !== l.key ? 0.3 : 0.85}
                    className="mm-link" />
            ))}
          </svg>

        {/* ===== 列1: 中心实体 ===== */}
        <div className="mm-col mm-center-col">
          <div ref={setRef(center.id)} className="mm-card mm-center-card"
               onClick={() => onSelect(center)}>
            <div className="mm-center-tag">输入实体</div>
            <div className="mm-center-name">
              {center.payload.aliases?.[0] || center.payload.id_str || center.label}
            </div>
            <div className="mm-center-id">{center.payload.id_str ?? center.label}</div>
            <div className="mm-center-meta">
              {center.payload.aliases && center.payload.aliases.length > 1 &&
                `别名×${center.payload.aliases.length - 1}`}
              {center.section ? ` · 章节${center.section}` : ""}
            </div>
          </div>
          {related.length === 0 && (
            <div className="mm-hint">无相关实体(该实体较孤立)</div>
          )}
        </div>

        {/* ===== 列2: 相关实体 ===== */}
        <div className="mm-col mm-ent-col">
          <div className="mm-col-title">相关实体 <span className="mm-count">{related.length}</span></div>
          {related.map((r, i) => (
            <div key={r.id} ref={setRef(r.id)}
                 className={`mm-card mm-ent-card ${selectedId === r.id ? "mm-selected" : ""}`}
                 onMouseEnter={() => setHoverKey(`c-${r.id}`)}
                 onMouseLeave={() => setHoverKey(null)}
                 onClick={() => onSelect(r.node)}>
              <div className="mm-ent-name">{r.aliases?.[0] || r.id_str || r.label}</div>
              <div className="mm-ent-id">{r.id_str ?? r.label}</div>
              <div className="mm-ent-rel">
                <span className={`mm-rel-tag ${r.rel === "问题直接命中" ? "mm-rel-direct" : ""}`}>
                  {relName(r.rel)}
                </span>
                <span className="mm-score">{r.score.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* ===== 列3: 模态分组 ===== */}
        <div className="mm-col mm-group-col">
          <div className="mm-col-title">召回内容 <span className="mm-count">{nContent}</span></div>
          <div className="mm-groups">
            {GROUP_ORDER.map((mod) => {
              const list = groups[mod] ?? [];
              if (list.length === 0 || hiddenTypes?.has(mod)) return null;
              const cfg = MODALITY_CONFIG[mod];
              const isCol = collapsed.has(mod);
              return (
                <div key={mod} className="mm-group" style={{
                  borderColor: cfg.color + "38",
                  background: cfg.color + "08",
                }}>
                  <div className="mm-group-header" ref={setRef(`grp-${mod}`)}
                       onClick={() => toggleGroup(mod)} style={{ color: cfg.color }}>
                    <span className="mm-group-dot" style={{ background: cfg.color }} />
                    {GROUP_NAME[mod]}
                    <span className="mm-count">{list.length}</span>
                    <span className="mm-group-arrow">{isCol ? "＋" : "－"}</span>
                  </div>
                  {!isCol && (
                    <div className="mm-group-body">
                      {list.map((n, i) => (
                        <ContentCard key={n.id} node={n} color={cfg.color}
                                     selected={selectedId === n.id}
                                     onSelect={onSelect} onDblSelect={onDblSelect} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
        </div>
      </div>

      {/* 缩放控制 */}
      <div className="mm-zoombar">
        <button className="mm-zbtn" onClick={() => zoomBy(1.2)} title="放大 (Ctrl+滚轮)">＋</button>
        <span className="mm-zval">{Math.round(zoom * 100)}%</span>
        <button className="mm-zbtn" onClick={() => zoomBy(1 / 1.2)} title="缩小 (Ctrl+滚轮)">－</button>
        <button className="mm-zbtn mm-zreset" onClick={() => setZoom(1)}>重置</button>
      </div>

      <style>{`
        .mm-scroll { width: 100%; height: 100%; overflow: auto; background:
          linear-gradient(180deg, #fafbfd 0%, #f3f6fb 100%); position: relative; }
        .mm-sizer { position: relative; }
        .mm-canvas { position: relative; display: inline-flex; gap: 44px;
          padding: 28px 36px 36px 28px; min-width: min-content; align-items: stretch;
          will-change: transform; }
        .mm-links { position: absolute; left: 0; top: 0; pointer-events: none; z-index: 0;
          overflow: visible; }
        .mm-link { transition: stroke 0.15s, opacity 0.15s; }
        .mm-col { position: relative; z-index: 1; display: flex; flex-direction: column; }
        .mm-center-col { justify-content: center; width: 236px; flex-shrink: 0; }
        .mm-ent-col { justify-content: center; width: 216px; flex-shrink: 0; gap: 10px; }
        .mm-group-col { flex-shrink: 0; }
        .mm-col-title { font-size: 12px; color: #8a94a6; letter-spacing: 2px;
          margin-bottom: 10px; font-weight: 600; }
        .mm-count { background: #e8edf5; color: #5b6876; border-radius: 8px;
          padding: 0 7px; font-size: 11px; margin-left: 6px; }
        .mm-card { background: #fff; border-radius: 12px; cursor: pointer;
          box-shadow: 0 1px 3px rgba(15,23,42,0.07), 0 4px 14px rgba(15,23,42,0.04);
          transition: border-color 0.15s;
          border: 1px solid #eaeef5; }
        .mm-card:hover { border-color: #c3cfe4;
          box-shadow: 0 3px 14px rgba(15,23,42,0.11); }
        .mm-selected { border-color: #2563EB !important;
          box-shadow: 0 0 0 2.5px rgba(37,99,235,0.18) !important; }
        .mm-center-card { padding: 20px 18px; border: none;
          background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%);
          color: #fff; }
        .mm-center-tag { font-size: 10.5px; letter-spacing: 3px; opacity: 0.75;
          margin-bottom: 8px; }
        .mm-center-name { font-size: 19px; font-weight: 700; line-height: 1.35;
          word-break: break-all; }
        .mm-center-id { font-family: ui-monospace, Consolas, monospace; font-size: 11px;
          opacity: 0.82; margin-top: 8px; word-break: break-all; }
        .mm-center-meta { font-size: 11px; opacity: 0.7; margin-top: 10px; }
        .mm-hint { font-size: 12px; color: #9aa5b8; text-align: center; margin-top: 14px; }
        .mm-ent-card { padding: 11px 13px; border-left: 3px solid #2563EB; }
        .mm-ent-name { font-size: 13.5px; font-weight: 650; color: #1e2a3d;
          word-break: break-all; }
        .mm-ent-id { font-family: ui-monospace, Consolas, monospace; font-size: 10px;
          color: #8a94a6; margin-top: 3px; word-break: break-all; }
        .mm-ent-rel { display: flex; align-items: center; margin-top: 6px; gap: 6px; }
        .mm-rel-tag { font-size: 10px; color: #64748b; background: #f1f5f9;
          border-radius: 5px; padding: 1px 6px; }
        .mm-rel-direct { color: #1d4ed8; background: #eff6ff; font-weight: 600; }
        .mm-score { font-size: 10px; color: #b0b9c9; margin-left: auto; }
        .mm-groups { display: flex; flex-direction: column; gap: 12px; width: 344px; }
        .mm-group { border: 1px solid; border-radius: 14px; padding: 10px 12px 12px; }
        .mm-group-header { display: flex; align-items: center; gap: 7px;
          font-size: 12.5px; font-weight: 700; cursor: pointer; user-select: none;
          padding: 2px 2px 8px; }
        .mm-group-dot { width: 8px; height: 8px; border-radius: 3px; }
        .mm-group-arrow { margin-left: auto; color: #9aa5b8; font-size: 13px; }
        .mm-group-body { display: flex; flex-direction: column; gap: 7px; }
        .mm-content-card { display: flex; align-items: center; gap: 10px; padding: 8px 10px; }
        .mm-cc-text { flex: 1; min-width: 0; }
        .mm-cc-title { font-size: 12.5px; color: #23304a; font-weight: 550;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .mm-cc-sub { font-size: 10.5px; color: #93a0b4; margin-top: 2px;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .mm-cc-badge { font-size: 9.5px; border-radius: 5px; padding: 1px 6px;
          flex-shrink: 0; background: #f4f6fa; color: #6b7a92; }
        .mm-cc-via { font-size: 9.5px; color: #2563EBaa; flex-shrink: 0; max-width: 76px;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .mm-cc-img { width: 68px; height: 50px; object-fit: cover; border-radius: 6px;
          flex-shrink: 0; border: 1px solid #e5eaf2; background: #f4f6fa; }
        .mm-warn { color: #dc2626 !important; background: #fef2f2 !important; }
        .mm-zoombar { position: sticky; bottom: 14px; left: 14px; display: inline-flex;
          align-items: center; gap: 6px; margin-top: -46px; z-index: 20;
          background: rgba(255,255,255,0.92); border: 1px solid #e2e8f2; border-radius: 10px;
          padding: 5px 8px; box-shadow: 0 2px 10px rgba(15,23,42,0.1); }
        .mm-zbtn { width: 26px; height: 26px; border: 1px solid #dde5f0; border-radius: 7px;
          background: #fff; color: #475569; font-size: 13px; cursor: pointer; line-height: 1; }
        .mm-zbtn:hover { background: #f1f5f9; }
        .mm-zreset { width: auto; padding: 0 9px; font-size: 11px; }
        .mm-zval { font-size: 11px; color: #64748b; min-width: 36px; text-align: center; }
      `}</style>
    </div>
  );
};

/** 模态内容卡片 */
const ContentCard: React.FC<{
  node: GraphNode & { via?: string; via_label?: string };
  color: string;
  selected: boolean;
  onSelect: (n: GraphNode) => void;
  onDblSelect: (n: GraphNode) => void;
}> = ({ node, color, selected, onSelect, onDblSelect }) => {
  const p = node.payload;
  let title = "", sub = "", badge = "";
  switch (node.type) {
    case "TXT":
      title = `${node.section} ${p.title ?? ""}`;
      sub = p.text_preview ? p.text_preview.slice(0, 60) : "";
      badge = p.text_len ? `${p.text_len}字` : "";
      break;
    case "TBL":
      title = p.caption ?? node.label;
      sub = (p.headers ?? []).slice(0, 4).join(" | ");
      badge = `${p.row_count ?? "?"}行`;
      break;
    case "IMG":
      title = p.caption ?? node.label;
      sub = `${p.img_type ?? ""} · ${node.section}`;
      break;
    case "SEQ": {
      const isFlow = p.seq_type === "exception_flow";
      title = isFlow ? `异常流: ${node.label.replace("异常流:", "")}` : `步骤链 ${p.n_steps ?? "?"}步`;
      sub = (p.steps ?? []).slice(0, 2).join(" → ") + ((p.steps?.length ?? 0) > 2 ? " → …" : "");
      badge = (p.dangling?.length ?? 0) > 0 ? "悬空引用" : "";
      break;
    }
    case "KNW":
      title = node.id.split(":")[1] ?? node.label;
      sub = p.description ?? "";
      break;
    default:
      title = node.label;
  }
  return (
    <div className={`mm-card mm-content-card ${selected ? "mm-selected" : ""}`}
         style={{ borderLeft: `3px solid ${color}` }}
         onClick={() => onSelect(node)}
         onDoubleClick={() => onDblSelect(node)}>
      {node.type === "IMG" && imageUrl(node) && p.exists ? (
        <img className="mm-cc-img" src={imageUrl(node)!} alt={p.caption}
             onLoad={() => {/* 触发重算连线由ResizeObserver覆盖 */}} />
      ) : null}
      <div className="mm-cc-text">
        <div className="mm-cc-title" style={badge === "悬空引用" ? { color: "#dc2626" } : undefined}>
          {title}
        </div>
        {sub && <div className="mm-cc-sub">{sub}</div>}
      </div>
      {node.via_label && <div className="mm-cc-via" title={`经 ${node.via_label} 召回`}>
        ⇐ {node.via_label}
      </div>}
      {badge && <span className={`mm-cc-badge ${badge === "悬空引用" ? "mm-warn" : ""}`}>{badge}</span>}
    </div>
  );
};

function bezier(x1: number, y1: number, x2: number, y2: number): string {
  const dx = Math.max(36, (x2 - x1) * 0.45);
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

function relName(rel: string): string {
  if (rel === "问题直接命中") return "问题命中";
  if (rel === "ent_hierarchy") return "ID父子";
  if (rel === "ent_cooccur") return "同章节";
  if (rel === "ent_same_table") return "同表";
  if (rel === "xdoc_shared_id") return "跨文档";
  if (rel === "xdoc_interface") return "接口关联";
  if (rel.startsWith("ent_appear")) return "出现关联";
  return rel.slice(0, 6);
}

export default MindMapGraph;
