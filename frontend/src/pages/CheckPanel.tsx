import React, { useEffect, useState } from "react";
import {
  Button, Tag, Spin, Empty, Tooltip, Progress, Collapse, Badge,
} from "antd";
import {
  ArrowLeftOutlined, ReloadOutlined, CheckCircleFilled, WarningFilled,
  CloseCircleFilled, RobotOutlined, MinusCircleFilled,
} from "@ant-design/icons";

/** 一致性校验结果页: 52项 grouped */

interface Finding {
  desc: string;
  section: string;
  evidence: string;
}

interface CheckItem {
  id: string;
  category: string;
  name: string;
  desc: string;
  modality: string;
  mode: string;
  status: "pass" | "warn" | "fail" | "llm";
  n_findings: number;
  findings: Finding[];
}

interface CategorySummary {
  name: string; total: number;
  pass: number; warn: number; fail: number; llm: number; findings: number;
}

interface CheckResult {
  ok: boolean;
  doc: string;
  doc_name: string;
  ran_at: string;
  summary: { total: number; pass: number; warn: number; fail: number; llm: number };
  categories: CategorySummary[];
  items: CheckItem[];
}

const STATUS_META: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  pass: { color: "#059669", icon: <CheckCircleFilled />, label: "通过" },
  warn: { color: "#d97706", icon: <WarningFilled />, label: "可疑" },
  fail: { color: "#dc2626", icon: <CloseCircleFilled />, label: "确证问题" },
  llm: { color: "#7c3aed", icon: <RobotOutlined />, label: "待LLM推理" },
};

interface Props {
  docNum: string;
  onBack: () => void;
}

const CheckPanel: React.FC<Props> = ({ docNum, onBack }) => {
  const [result, setResult] = useState<CheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await window.fetch(`/api/check/${docNum}`, { method: "POST" });
      const j = await r.json();
      if (j.ok) setResult(j);
      else setError(j.message ?? "校验失败");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { setResult(null); run(); }, [docNum]); // eslint-disable-line

  if (loading && !result) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12 }}>
        <Spin size="large" />
        <span style={{ color: "#64748b" }}>正在执行52项一致性校验…</span>
      </div>
    );
  }
  if (error || !result) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Empty description={error ?? "无结果"} />
      </div>
    );
  }

  const s = result.summary;
  const pct = (n: number) => Math.round((n / s.total) * 100);

  const byCat: Record<string, CheckItem[]> = {};
  for (const it of result.items) {
    (byCat[it.category] = byCat[it.category] || []).push(it);
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* 顶栏 */}
      <div style={{ padding: "14px 20px", borderBottom: "1px solid #e5eaf1",
                    display: "flex", alignItems: "center", gap: 12, background: "#fff" }}>
        <Button size="small" icon={<ArrowLeftOutlined />} onClick={onBack}>返回</Button>
        <div>
          <span style={{ fontSize: 14.5, fontWeight: 700 }}>
            一致性校验 · {result.doc_name.slice(0, 22)}
          </span>
          <span style={{ fontSize: 11, color: "#94a3b8", marginLeft: 10 }}>
            {result.ran_at.replace("T", " ")}
          </span>
        </div>
        <Button size="small" icon={<ReloadOutlined />} onClick={run}
                loading={loading} style={{ marginLeft: "auto" }}>重新校验</Button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {/* 汇总卡 */}
        <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
          {(["pass", "warn", "fail", "llm"] as const).map((k) => {
            const meta = STATUS_META[k];
            const n = s[k];
            return (
              <div key={k} style={{
                flex: 1, minWidth: 150, background: "#fff", borderRadius: 12,
                border: "1px solid #eaeef5", padding: "12px 16px",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <span style={{ color: meta.color, fontSize: 20 }}>{meta.icon}</span>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 750, color: meta.color }}>{n}</div>
                  <div style={{ fontSize: 11, color: "#94a3b8" }}>
                    {meta.label} · {pct(n)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 分类进度条 */}
        <div style={{ background: "#fff", border: "1px solid #eaeef5", borderRadius: 12,
                      padding: "12px 16px", marginBottom: 16 }}>
          {result.categories.map((c) => (
            <div key={c.name} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span style={{ width: 80, fontSize: 12, fontWeight: 600, flexShrink: 0 }}>{c.name}</span>
              <Progress
                style={{ flex: 1, margin: 0 }}
                size="small"
                percent={Math.round(((c.pass) / c.total) * 100)}
                success={{ percent: Math.round(((c.pass) / c.total) * 100), strokeColor: "#10b981" }}
                strokeColor="#d97706"
                trailColor="#ede9fe"
                format={() => `${c.pass}/${c.total}通过`}
              />
              {c.findings > 0 && (
                <Badge count={c.findings} size="small" color="#d97706"
                       title={`${c.findings}条发现`} />
              )}
            </div>
          ))}
        </div>

        {/* 52项明细(按类分组折叠面板) */}
        <Collapse
          defaultActiveKey={result.categories.map((c) => c.name)}
          items={result.categories.map((c) => ({
            key: c.name,
            label: (
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <b>{c.name}</b>
                <Tag style={{ fontSize: 11 }}>{c.total}项</Tag>
                {c.fail > 0 && <Tag color="red">{c.fail}确证</Tag>}
                {c.warn > 0 && <Tag color="orange">{c.warn}可疑</Tag>}
                {c.findings > 0 && <span style={{ fontSize: 11, color: "#94a3b8" }}>共{c.findings}条发现</span>}
              </span>
            ),
            children: (
              <div>
                {(byCat[c.name] ?? []).map((it) => (
                  <ItemRow key={it.id} item={it} />
                ))}
              </div>
            ),
          }))}
        />

        <div style={{ marginTop: 14, fontSize: 11, color: "#b0b9c9", lineHeight: 1.8 }}>
          校验数据源: 上下文关联图谱(方向A) + born-digital锚点 + drift普查 + Mermaid保真度资产<br />
          「待LLM推理」项需接入万擎kimi-k2执行业务理解判断(当前为规划态)
        </div>
      </div>
    </div>
  );
};

const ItemRow: React.FC<{ item: CheckItem }> = ({ item }) => {
  const meta = STATUS_META[item.status];
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "9px 10px", borderBottom: "1px solid #f1f5f9",
    }}>
      <span style={{ color: meta.color, fontSize: 15, marginTop: 1, flexShrink: 0 }}>
        {meta.icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <code style={{ fontSize: 10.5, color: "#64748b", background: "#f1f5f9",
                         padding: "1px 5px", borderRadius: 4 }}>{item.id}</code>
          <span style={{ fontSize: 12.5, fontWeight: 600 }}>{item.name}</span>
          <Tooltip title={`检测模态: ${item.modality}`}>
            <Tag style={{ fontSize: 10, margin: 0 }} color="default">{item.modality}</Tag>
          </Tooltip>
          {item.mode === "llm" && (
            <Tooltip title="该项需大模型业务理解推理">
              <Tag style={{ fontSize: 10, margin: 0 }} color="purple" icon={<RobotOutlined />}>LLM</Tag>
            </Tooltip>
          )}
          {item.n_findings > 0 && (
            <Tag style={{ fontSize: 10, margin: 0 }} color={item.status === "fail" ? "red" : "orange"}>
              {item.n_findings}条发现
            </Tag>
          )}
        </div>
        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{item.desc}</div>
        {item.findings.length > 0 && (
          <div style={{ marginTop: 6, background: "#f8fafc", borderRadius: 8,
                        border: "1px solid #eef2f7", padding: "6px 10px" }}>
            {item.findings.map((f, i) => (
              <div key={i} style={{ fontSize: 11.5, padding: "3px 0",
                                    borderBottom: i < item.findings.length - 1 ? "1px dashed #eef2f7" : undefined }}>
                <div style={{ color: "#334155" }}>
                  <MinusCircleFilled style={{ color: "#cbd5e1", fontSize: 9, marginRight: 6 }} />
                  {f.desc}
                  {f.section && <Tag style={{ fontSize: 9.5, marginLeft: 6 }}>{f.section.slice(0, 16)}</Tag>}
                </div>
                <div style={{ color: "#8a94a6", marginLeft: 16, fontSize: 11 }}>{f.evidence}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CheckPanel;
