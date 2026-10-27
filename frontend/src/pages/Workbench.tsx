import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button, Input, Select, Slider, Spin, Tag, Empty, Modal, Tooltip, Alert,
} from "antd";
import {
  SearchOutlined, DatabaseOutlined, FileTextOutlined, TableOutlined,
  PictureOutlined, NodeIndexOutlined, BulbOutlined, CheckCircleFilled,
  CloseCircleFilled,
} from "@ant-design/icons";
import MindMapGraph from "./MindMapGraph";
import { activate, fetchDocs, fetchMermaid, fetchSection, fetchTable, imageUrl } from "../api";
import type { ActivateResult, DocInfo, GraphNode } from "../types";
import { MODALITY_CONFIG } from "../types";
import MermaidBox from "./MermaidBox";

const { Search } = Input;

interface Props {
  pendingQuestion: string | null;
  onPendingConsumed: () => void;
  initialDoc?: string | null;
}

const Workbench: React.FC<Props> = ({ pendingQuestion, onPendingConsumed, initialDoc }) => {
  const [question, setQuestion] = useState("");
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [docSel, setDocSel] = useState<string | undefined>(undefined);
  const [k, setK] = useState(2);
  const [topK, setTopK] = useState(12);
  const [minW, setMinW] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ActivateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
  const [previewImg, setPreviewImg] = useState<GraphNode | null>(null);
  const [graphKey, setGraphKey] = useState(0);
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => {
    fetchDocs().then(setDocs).catch(() => setError("后端不可达,请确认 server/main.py 已启动"));
  }, []);

  /** 从数据集页跳入: 锁定该文档 */
  useEffect(() => {
    if (initialDoc) {
      setDocSel(initialDoc);
      setError(null);
    }
  }, [initialDoc]);

  const doActivate = useCallback(
    async (q: string, opts?: { doc?: string | null; k?: number; top_k?: number; min_w?: number }) => {
      if (!q.trim()) return;
      setLoading(true);
      setError(null);
      setSelected(null);
      try {
        const r = await activate(q, {
          doc: opts?.doc ?? docSel ?? null,
          k: opts?.k ?? k,
          top_k: opts?.top_k ?? topK,
          min_w: opts?.min_w ?? minW,
        });
        setResult(r);
        setGraphKey((x) => x + 1);
        if (!r.ok) setError(r.message ?? "未找到种子实体");
        setHistory((h) => [q, ...h.filter((x) => x !== q)].slice(0, 8));
      } catch (e) {
        setError(`请求失败: ${String(e)}`);
      } finally {
        setLoading(false);
      }
    },
    [docSel, k, topK, minW]
  );

  /** QA页跳转联动 */
  useEffect(() => {
    if (pendingQuestion) {
      setQuestion(pendingQuestion);
      doActivate(pendingQuestion);
      onPendingConsumed();
    }
  }, [pendingQuestion, doActivate, onPendingConsumed]);

  const toggleType = (t: string) => {
    setHiddenTypes((s) => {
      const n = new Set(s);
      if (n.has(t)) n.delete(t);
      else n.add(t);
      return n;
    });
  };

  const stats = result?.ok ? result.stats : null;

  return (
    <div style={{ display: "flex", height: "100%", gap: 0 }}>
      {/* ============ 左侧控制面板 ============ */}
      <div style={{ width: 280, background: "#fff", borderRight: "1px solid #e5eaf1",
                    padding: 16, display: "flex", flexDirection: "column", gap: 14, overflowY: "auto" }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, color: "#0f172a" }}>
            上下文召回
          </div>
          <Search
            placeholder="输入问题,如: 开发工程生成的需求标识符是什么?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onSearch={(v) => doActivate(v)}
            enterButton={<SearchOutlined />}
            loading={loading}
            allowClear
          />
          {history.length > 0 && (
            <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 4 }}>
              {history.map((h) => (
                <Tag key={h} style={{ cursor: "pointer", fontSize: 11 }}
                     onClick={() => { setQuestion(h); doActivate(h); }}>
                  {h.length > 14 ? h.slice(0, 14) + "…" : h}
                </Tag>
              ))}
            </div>
          )}
        </div>

        <div>
          <div style={labelStyle}>文档范围</div>
          <Select
            style={{ width: "100%" }}
            placeholder="自动(按问题匹配)"
            allowClear
            value={docSel}
            onChange={(v) => setDocSel(v)}
            options={docs.map((d) => ({
              value: d.doc_num,
              label: `${d.doc_num} ${d.doc.slice(2, 14)} (${d.n_nodes}节点)`,
            }))}
          />
        </div>

        <div>
          <div style={labelStyle}>扩展深度</div>
          <Select
            style={{ width: "100%" }}
            value={k}
            onChange={(v) => { setK(v); if (result?.ok) doActivate(question, { k: v }); }}
            options={[
              { value: 1, label: "1跳(直接关联)" },
              { value: 2, label: "2跳(扩展召回)" },
            ]}
          />
        </div>

        <div>
          <div style={labelStyle}>每模态数量上限 <span style={{ color: "#2563EB" }}>{topK}</span></div>
          <Slider min={6} max={20} value={topK}
                  onChange={(v) => setTopK(v)}
                  onChangeComplete={(v) => { if (result?.ok) doActivate(question, { top_k: v }); }} />
        </div>

        <div>
          <div style={labelStyle}>边权重阈值 <span style={{ color: "#2563EB" }}>{minW.toFixed(1)}</span></div>
          <Slider min={0.3} max={0.8} step={0.05} value={minW}
                  onChange={(v) => setMinW(v)}
                  onChangeComplete={(v) => { if (result?.ok) doActivate(question, { min_w: v }); }} />
        </div>

        <div>
          <div style={labelStyle}>节点类型(点击显隐)</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {(["E", "TXT", "TBL", "IMG", "SEQ", "KNW"] as const).map((t) => {
              const cfg = MODALITY_CONFIG[t];
              const hidden = hiddenTypes.has(t);
              return (
                <Tag key={t} style={tagStyle(hidden, cfg.color)} onClick={() => toggleType(t)}>
                  {t === "E" ? <NodeIndexOutlined /> :
                   t === "TXT" ? <FileTextOutlined /> :
                   t === "TBL" ? <TableOutlined /> :
                   t === "IMG" ? <PictureOutlined /> :
                   t === "SEQ" ? <DatabaseOutlined /> : <BulbOutlined />}
                  <span style={{ marginLeft: 4 }}>{cfg.name}</span>
                </Tag>
              );
            })}
          </div>
        </div>

        {stats && result?.ok && (
          <div style={{ background: "#f8fafc", borderRadius: 10, padding: 12, fontSize: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>
              召回统计 · doc{result.doc}
            </div>
            <div style={{ color: "#64748b", lineHeight: 1.9 }}>
              相关实体 {stats.n_related} · 召回内容 {stats.n_content}
              <br />
              {Object.entries(stats.by_modality)
                .filter(([, c]) => c > 0)
                .map(([m, c]) => `${MODALITY_CONFIG[m as keyof typeof MODALITY_CONFIG]?.name ?? m}: ${c}`)
                .join(" · ")}
            </div>
          </div>
        )}

        <div style={{ marginTop: "auto", fontSize: 11, color: "#94a3b8", lineHeight: 1.7 }}>
          中心实体 → 相关实体 → 模态分组<br />
          悬停实体卡 → 高亮召回连线<br />
          双击图片卡片 → 大图预览
        </div>
      </div>

      {/* ============ 中央思维导图 ============ */}
      <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
        <div style={{ position: "absolute", inset: 0 }}>
          {result?.ok && result.center ? (
            <MindMapGraph
              result={result}
              graphKey={`g${graphKey}`}
              selectedId={selected?.id ?? null}
              hiddenTypes={hiddenTypes}
              onSelect={setSelected}
              onDblSelect={(n) => { if (n.type === "IMG") setPreviewImg(n); }}
            />
          ) : (
            <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Empty description={error ?? "输入问题开始上下文召回"} />
            </div>
          )}
        </div>
        {loading && (
          <div style={{
            position: "absolute", inset: 0, zIndex: 10,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(255,255,255,0.55)", backdropFilter: "blur(1px)",
          }}>
            <Spin size="large" tip="召回中…" />
          </div>
        )}
        {result?.ok && (
          <div style={{ position: "absolute", top: 12, left: 14, fontSize: 12, color: "#64748b",
                        background: "rgba(255,255,255,0.9)", padding: "6px 12px", borderRadius: 8,
                        boxShadow: "0 1px 4px rgba(15,23,42,0.08)" }}>
            {result.doc_name?.slice(0, 22)}
          </div>
        )}
      </div>

      {/* ============ 右侧详情面板 ============ */}
      <div style={{ width: 360, background: "#fff", borderLeft: "1px solid #e5eaf1",
                    padding: 16, overflowY: "auto" }}>
        {selected ? (
          <NodeDetail node={selected} />
        ) : result?.ok ? (
          <>
            <div style={labelStyle}>中心实体</div>
            <div style={{ ...cardStyle, marginBottom: 10, borderLeft: "3px solid #2563EB" }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: "#1e2a3d" }}>
                {result.center?.payload.aliases?.[0] || result.center?.payload.id_str || result.center?.label}
              </div>
              <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 10.5,
                            color: "#8a94a6", marginTop: 4, wordBreak: "break-all" }}>
                {result.center?.payload.id_str ?? result.center?.label}
              </div>
              <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 6 }}>
                {result.center?.why}
              </div>
            </div>
            <div style={{ ...labelStyle, marginTop: 14 }}>
              相关实体 ({result.related_entities?.length ?? 0})
            </div>
            {(result.related_entities ?? []).slice(0, 6).map((r) => (
              <div key={r.id} style={{ ...cardStyle, marginBottom: 8, display: "flex",
                                        alignItems: "center", gap: 8, cursor: "pointer" }}
                   onClick={() => setSelected(r.node)}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: "#1e2a3d",
                                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {r.aliases?.[0] || r.id_str || r.label}
                  </div>
                  <div style={{ fontSize: 10.5, color: "#94a3b8", marginTop: 2 }}>
                    {r.rel} · {r.score.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
            <div style={{ ...labelStyle, marginTop: 16 }}>聚合条目(方向A输出)</div>
            {(result.items ?? []).map((it) => (
              <div key={it.entity_id} style={{ ...cardStyle, marginBottom: 10 }}>
                <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 11.5, fontWeight: 600 }}>
                  {it.entity_id}
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", margin: "6px 0" }}>
                  {it.sections.slice(0, 6).map((s) => (
                    <Tag key={s} style={{ fontSize: 10, margin: 0 }}>{s}</Tag>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: "#64748b" }}>
                  出现 {it.n_occurrences} 次 · 媒体 {it.media.length} 个
                </div>
                <ChainBar score={it.chain_completeness} />
              </div>
            ))}
            {(result.items ?? []).length === 0 && (
              <div style={{ fontSize: 12, color: "#94a3b8" }}>该问题未命中聚合条目</div>
            )}
          </>
        ) : (
          <Empty description="点击节点查看详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </div>

      {/* 图片大图预览 */}
      <Modal
        open={!!previewImg}
        title={previewImg?.payload.caption ?? "图片预览"}
        footer={null}
        onCancel={() => setPreviewImg(null)}
        width={720}
      >
        {previewImg && imageUrl(previewImg) && (
          <img src={imageUrl(previewImg)!} alt={previewImg.payload.caption}
               style={{ width: "100%", borderRadius: 8 }} />
        )}
      </Modal>
    </div>
  );
};

/** 节点详情渲染 */
const NodeDetail: React.FC<{ node: GraphNode }> = ({ node }) => {
  const p = node.payload;
  const cfg = MODALITY_CONFIG[node.type];
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span style={{ width: 10, height: 10, borderRadius: 3, background: cfg.color }} />
        <span style={{ fontSize: 13, fontWeight: 700 }}>{cfg.name}</span>
        <Tag style={{ marginLeft: "auto", fontSize: 10 }}>
          hop {node.hop} · score {node.score}
        </Tag>
      </div>

      {node.type === "E" && (
        <>
          <DetailRow label="需求ID" value={<code style={codeStyle}>{p.id_str}</code>} />
          {(p.aliases ?? []).length > 0 && (
            <DetailRow label="名称别名" value={p.aliases!.map((a) => (
              <Tag key={a} color="blue" style={{ margin: 2 }}>{a}</Tag>
            ))} />
          )}
          {node.section && <DetailRow label="章节" value={node.section} />}
        </>
      )}
      {node.type === "TXT" && <TxtDetail node={node} />}
      {node.type === "TBL" && <TblDetail node={node} />}
      {node.type === "IMG" && <ImgDetail node={node} />}
      {node.type === "SEQ" && (
        <>
          <DetailRow label="类型" value={
            p.seq_type === "exception_flow" ? <Tag color="orange">异常流</Tag> : <Tag color="gold">流程步骤链</Tag>
          } />
          {(p.steps ?? []).length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={labelStyle}>步骤序列</div>
              <ol style={{ paddingLeft: 18, fontSize: 12, lineHeight: 2 }}>
                {(p.steps ?? []).slice(0, 20).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
          {(p.dangling ?? []).length > 0 && (
            <Alert type="error" style={{ marginTop: 8, fontSize: 12 }}
                   message={`悬空引用: ${(p.dangling ?? []).join(", ")}`} />
          )}
          {(p.defined ?? []).length > 0 && (
            <DetailRow label="定义的异常" value={(p.defined ?? []).join(", ")} />
          )}
        </>
      )}
      {node.type === "KNW" && (
        <>
          <DetailRow label="规则" value={<code style={codeStyle}>{node.id.split(":")[1]}</code>} />
          <DetailRow label="描述" value={p.description ?? "-"} />
          <DetailRow label="严重度" value={
            p.severity === "HIGH" ? <Tag color="red">HIGH</Tag> : <Tag color="orange">{p.severity}</Tag>
          } />
          <DetailRow label="来源" value={p.source} />
        </>
      )}
    </div>
  );
};

const DetailRow: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={{ display: "flex", marginBottom: 8, fontSize: 12.5, gap: 8 }}>
    <div style={{ width: 62, color: "#94a3b8", flexShrink: 0 }}>{label}</div>
    <div style={{ color: "#334155", flex: 1, wordBreak: "break-all" }}>{value}</div>
  </div>
);

/** TXT详情: 章节全文 */
const TxtDetail: React.FC<{ node: GraphNode }> = ({ node }) => {
  const [text, setText] = useState<string | null>(null);
  const docNum = node.id.split(":")[1];
  useEffect(() => {
    setText(null);
    fetchSection(docNum, node.section).then((r) => setText(r.text || "(该章节无正文)"));
  }, [docNum, node.section]);
  return (
    <>
      <DetailRow label="章节号" value={<code style={codeStyle}>{node.section}</code>} />
      <DetailRow label="标题" value={node.payload.title ?? "-"} />
      <div style={{ ...labelStyle, marginTop: 10 }}>章节正文</div>
      {text === null ? (
        <div style={{ color: "#94a3b8", fontSize: 12, padding: 12 }}>加载中…</div>
      ) : (
        <div style={{ background: "#f8fafc", border: "1px solid #eef2f7", borderRadius: 10,
                      padding: 12, fontSize: 12.5, lineHeight: 1.9, color: "#334155",
                      maxHeight: 420, overflowY: "auto", whiteSpace: "pre-wrap" }}>
          {text}
        </div>
      )}
    </>
  );
};

/** TBL详情: 完整表格渲染 */
const TblDetail: React.FC<{ node: GraphNode }> = ({ node }) => {
  const [html, setHtml] = useState<string | null>(null);
  const docNum = node.id.split(":")[1];
  useEffect(() => {
    setHtml(null);
    fetchTable(docNum, node.payload.caption ?? "").then((h) => setHtml(h));
  }, [docNum, node.payload.caption]);
  return (
    <>
      <DetailRow label="表标题" value={node.payload.caption ?? "-"} />
      <DetailRow label="表型" value={<Tag color="cyan">{node.payload.table_type}</Tag>} />
      <DetailRow label="行数" value={String(node.payload.row_count ?? "?")} />
      <DetailRow label="章节" value={node.section} />
      <div style={{ ...labelStyle, marginTop: 10 }}>表格内容</div>
      {html === null ? (
        <div style={{ color: "#94a3b8", fontSize: 12, padding: 12 }}>加载中…</div>
      ) : html === "" ? (
        <div style={{ color: "#94a3b8", fontSize: 12, padding: 12 }}>未找到表格数据</div>
      ) : (
        <div className="tbl-html"
             style={{ maxHeight: 420, overflow: "auto", border: "1px solid #eef2f7",
                      borderRadius: 10, background: "#fff" }}
             dangerouslySetInnerHTML={{ __html: html }} />
      )}
      <style>{`
        .tbl-html table { border-collapse: collapse; width: 100%; font-size: 11.5px; }
        .tbl-html th, .tbl-html td { border: 1px solid #e2e8f0; padding: 4px 7px;
          color: #334155; vertical-align: top; }
        .tbl-html th { background: #f1f5f9; font-weight: 600; white-space: nowrap; }
        .tbl-html td p { margin: 0; }
      `}</style>
    </>
  );
};

/** IMG详情: 原图 + Mermaid渲染 并排 */
const ImgDetail: React.FC<{ node: GraphNode }> = ({ node }) => {
  const p = node.payload;
  const docNum = node.id.split(":")[1];
  const figNum = node.id.split(":")[2];
  const [mm, setMm] = useState<{ has: boolean; code: string; type: string } | null>(null);
  useEffect(() => {
    setMm(null);
    fetchMermaid(docNum, figNum).then(setMm);
  }, [docNum, figNum]);
  const hasImg = imageUrl(node) && p.exists;
  return (
    <>
      <DetailRow label="图标题" value={p.caption ?? "-"} />
      <DetailRow label="图型" value={<Tag color="green">{p.img_type}</Tag>} />
      <DetailRow label="章节" value={node.section} />
      {hasImg && (
        <div style={{ marginTop: 10 }}>
          <div style={labelStyle}>原始图片</div>
          <img src={imageUrl(node)!} alt={p.caption}
               style={{ width: "100%", borderRadius: 10, border: "1px solid #e2e8f0",
                        display: "block" }} />
        </div>
      )}
      {mm && mm.has && (
        <div style={{ marginTop: 14 }}>
          <div style={labelStyle}>Mermaid结构图</div>
          <MermaidBox code={mm.code} />
        </div>
      )}
      {mm && !mm.has && !hasImg && (
        <div style={{ color: "#94a3b8", fontSize: 12, padding: 12 }}>该图无图片文件与Mermaid导出</div>
      )}
    </>
  );
};

const ChainBar: React.FC<{ score: { has_title: boolean; has_func_table: boolean; has_qualification: boolean; has_trace: boolean; score: number } }> = ({ score }) => {
  const items: [string, boolean][] = [
    ["标题", score.has_title], ["功能表", score.has_func_table],
    ["合格性", score.has_qualification], ["追溯", score.has_trace],
  ];
  return (
    <div style={{ marginTop: 8 }}>
      <Tooltip title="chain_completeness: 实体在四类位置的覆盖度">
        <div style={{ display: "flex", gap: 4 }}>
          {items.map(([name, ok]) => (
            <div key={name} style={{
              flex: 1, textAlign: "center", fontSize: 10, padding: "3px 0", borderRadius: 6,
              background: ok ? "#ecfdf5" : "#fef2f2", color: ok ? "#059669" : "#dc2626",
            }}>
              {ok ? <CheckCircleFilled style={{ marginRight: 2 }} /> : <CloseCircleFilled style={{ marginRight: 2 }} />}
              {name}
            </div>
          ))}
        </div>
      </Tooltip>
    </div>
  );
};

const labelStyle: React.CSSProperties = {
  fontSize: 11.5, color: "#94a3b8", marginBottom: 6, letterSpacing: 1,
};
const cardStyle: React.CSSProperties = {
  background: "#f8fafc", border: "1px solid #eef2f7", borderRadius: 10, padding: 10,
};
const codeStyle: React.CSSProperties = {
  background: "#f1f5f9", padding: "2px 6px", borderRadius: 4, fontSize: 11.5,
};
const tagStyle = (hidden: boolean, color: string): React.CSSProperties => ({
  cursor: "pointer", borderRadius: 6, padding: "2px 8px",
  color: hidden ? "#cbd5e1" : color,
  border: `1px solid ${hidden ? "#f1f5f9" : color + "66"}`,
  background: hidden ? "#fafafa" : color + "0d",
});

export default Workbench;
