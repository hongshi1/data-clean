import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Alert, Button, Card, Empty, Input, Radio, Spin, Table, Tag, Tooltip, Typography,
} from "antd";
import {
  CheckCircleFilled, CloseCircleFilled, QuestionCircleFilled,
  SearchOutlined, ThunderboltOutlined,
} from "@ant-design/icons";
import { fetchVerifyQaList, verifyQaById } from "../api";
import type {
  EvidenceBlock, VerifyClaim, VerifyQaItem, VerifyResult, VerifyVerdict,
} from "../types";

const { Paragraph, Text } = Typography;

type PresetName = "fast" | "standard" | "full";

const PRESET_OPTIONS: { label: string; value: PresetName }[] = [
  { label: "fast · 秒级", value: "fast" },
  { label: "standard · 需模型", value: "standard" },
  { label: "full · 级联", value: "full" },
];

const PRESET_HINTS: Record<PresetName, string> = {
  fast: "fast: L0/L1确定性专家通道, 秒级, 零模型加载",
  standard: "standard: +L2本地NLI残差, 首次调用需加载模型(约35s)",
  full: "full: +L3级联仲裁(refute候选升级LLM复核), 最慢最准",
};

const VERDICT_META: Record<
  VerifyVerdict,
  { color: string; tagColor: string; short: string; label: string; desc: string; icon: ReactNode }
> = {
  support: {
    color: "#059669", tagColor: "green", short: "支持", label: "证据支持",
    desc: "答案声明与冻结证据一致", icon: <CheckCircleFilled />,
  },
  refute: {
    color: "#dc2626", tagColor: "red", short: "反对", label: "证据反对",
    desc: "答案声明与冻结证据矛盾", icon: <CloseCircleFilled />,
  },
  not_in_evidence: {
    color: "#64748b", tagColor: "default", short: "NIE", label: "证据无法判定",
    desc: "当前证据无法判定(开放世界)", icon: <QuestionCircleFilled />,
  },
};

const CHECK_ITEM_NAMES: Record<string, string> = {
  "TERM-01": "术语一致性", "TERM-02": "术语定义", "TERM-03": "枚举集匹配",
  "TERM-04": "状态告警术语", "TERM-05": "指令命令术语", "TERM-06": "单位与精度",
  "TERM-07": "接口标识", "TERM-08": "缩写全称",
  "PARAM-01": "响应时间", "PARAM-02": "周期频率", "PARAM-03": "阈值区间",
  "PARAM-04": "对齐误差", "PARAM-05": "资源占用", "PARAM-06": "取值范围",
  "PARAM-07": "存储容量", "PARAM-08": "同步精度", "PARAM-09": "降级阈值",
  "PARAM-10": "故障时长",
  "LOGIC-01": "优先级", "LOGIC-02": "异常流", "LOGIC-03": "执行顺序",
  "LOGIC-04": "数据流向", "LOGIC-05": "分支工况", "LOGIC-06": "互斥约束",
  "LOGIC-07": "原子性", "LOGIC-08": "主备冗余", "LOGIC-09": "权限控制",
  "LOGIC-10": "恢复重启", "LOGIC-11": "重搜策略",
  "GJB-01": "可测试性", "GJB-02": "容错", "GJB-03": "访问控制", "GJB-04": "审计",
  "GJB-05": "追溯映射", "GJB-06": "报警要素", "GJB-07": "自检", "GJB-08": "掉电保护",
  "GJB-09": "输入校验", "GJB-10": "升级回滚", "GJB-11": "降级模式",
};

const checkItemName = (id: string) => CHECK_ITEM_NAMES[id] ?? id;

const refBase = (ref: string) => ref.split("#")[0];

const EVIDENCE_TABLE_CSS = `
.vp-ev-table table { border-collapse: collapse; }
.vp-ev-table th, .vp-ev-table td { border: 1px solid #dbe3ee; padding: 2px 8px; font-size: 11px; }
.vp-ev-table th { background: #f4f7fb; }
.vp-ev-table p { margin: 0; }
`;

function VerdictTag({ v }: { v: VerifyVerdict }) {
  const m = VERDICT_META[v];
  return (
    <Tag icon={m.icon} color={m.tagColor} style={{ fontSize: 11, margin: 0 }}>
      {m.short}
    </Tag>
  );
}

function VerdictBadge({ verdict, big = false }: { verdict: VerifyVerdict; big?: boolean }) {
  const m = VERDICT_META[verdict];
  return (
    <Tooltip title={m.desc}>
      <span
        style={{
          display: "inline-flex", alignItems: "center", gap: big ? 10 : 6,
          padding: big ? "10px 18px" : "2px 10px",
          background: `${m.color}14`, border: `1px solid ${m.color}66`,
          borderRadius: big ? 12 : 6, color: m.color,
        }}
      >
        <span style={{ fontSize: big ? 24 : 13 }}>{m.icon}</span>
        <span style={{ fontSize: big ? 17 : 11.5, fontWeight: big ? 750 : 600 }}>
          {m.label}
        </span>
      </span>
    </Tooltip>
  );
}

function ClaimRow({
  claim, active, onClick,
}: { claim: VerifyClaim; active: boolean; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: "8px 12px", marginBottom: 6, borderRadius: 8, cursor: "pointer",
        border: `1px solid ${active ? "#f59e0b" : "#eef2f7"}`,
        background: active ? "#fff7e6" : "#fafbfd",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <VerdictTag v={claim.verdict} />
        <code style={{ fontSize: 10.5, color: "#64748b", background: "#f1f5f9", padding: "1px 5px", borderRadius: 4 }}>
          {claim.claim_id}
        </code>
        <Tooltip title={`方法: ${claim.method}`}>
          <Tag style={{ fontSize: 10, margin: 0, fontFamily: "monospace" }}>{claim.method}</Tag>
        </Tooltip>
        <span style={{ fontSize: 10.5, color: "#94a3b8" }}>
          conf {(claim.confidence * 100).toFixed(0)}%
        </span>
        {claim.evidence_refs.length > 0 ? (
          <Tag color="gold" bordered={false} style={{ fontSize: 10, margin: 0 }}>
            引用{claim.evidence_refs.length}条
          </Tag>
        ) : (
          <Tag bordered={false} style={{ fontSize: 10, margin: 0, color: "#b0b9c9" }}>无引用</Tag>
        )}
      </div>
      <div style={{ fontSize: 12.5, color: "#1e293b", marginTop: 4, lineHeight: 1.6 }}>
        {claim.claim_text}
      </div>
      <Paragraph
        style={{ margin: "4px 0 0", fontSize: 11, color: "#8a94a6" }}
        ellipsis={{ rows: 2, tooltip: claim.rationale }}
      >
        {claim.rationale}
      </Paragraph>
    </div>
  );
}

function EvidenceCard({
  block, highlighted, exactRefs,
}: { block: EvidenceBlock; highlighted: boolean; exactRefs?: string[] }) {
  const isTable = block.source_type === "table";
  return (
    <div
      style={{
        border: `1px solid ${highlighted ? "#fadb14" : "#eaeef5"}`,
        background: highlighted ? "#fffbe6" : "#fff",
        borderRadius: 8, padding: "8px 12px", marginBottom: 8,
        boxShadow: highlighted ? "0 0 0 1px rgba(250, 219, 20, 0.55)" : undefined,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
        <code
          style={{
            fontSize: 10.5, padding: "1px 6px", borderRadius: 4,
            color: highlighted ? "#b45309" : "#64748b",
            background: highlighted ? "#fef3c7" : "#f1f5f9",
          }}
        >
          {block.evidence_id}
        </code>
        <Tag style={{ fontSize: 10, margin: 0 }}>{block.source_type}</Tag>
        {block.completeness && (
          <Tooltip title={block.completeness_proof || block.completeness}>
            <Tag style={{ fontSize: 10, margin: 0 }} color={block.completeness === "closed" ? "blue" : "default"}>
              {block.completeness === "closed" ? "封闭集" : "开放集"}
            </Tag>
          </Tooltip>
        )}
        <span style={{ fontSize: 10.5, color: "#94a3b8" }}>
          {block.source_ref?.doc_id} · {block.source_ref?.section}
          {block.source_ref?.page != null ? ` · p${block.source_ref.page}` : ""}
        </span>
        {exactRefs?.map((r) => (
          <Tag key={r} color="gold" style={{ fontSize: 10, margin: 0, fontFamily: "monospace" }}>{r}</Tag>
        ))}
      </div>
      {isTable ? (
        <div
          className="vp-ev-table"
          style={{ overflowX: "auto" }}
          dangerouslySetInnerHTML={{ __html: block.text }}
        />
      ) : (
        <div style={{ whiteSpace: "pre-wrap", fontSize: 12, color: "#334155", lineHeight: 1.7 }}>
          {block.text}
        </div>
      )}
    </div>
  );
}

function ResultView({ result }: { result: VerifyResult }) {
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const activeClaim = useMemo(
    () => result.claim_results.find((c) => c.claim_id === activeClaimId) ?? null,
    [result, activeClaimId]
  );
  const highlightBases = useMemo(() => {
    const claims = activeClaim ? [activeClaim] : result.claim_results;
    return new Set(claims.flatMap((c) => c.evidence_refs).map(refBase));
  }, [activeClaim, result]);
  const exactRefsByBase = useMemo(() => {
    const m = new Map<string, string[]>();
    for (const ref of activeClaim?.evidence_refs ?? []) {
      const base = refBase(ref);
      m.set(base, [...(m.get(base) ?? []), ref]);
    }
    return m;
  }, [activeClaim]);
  const checkItems = useMemo(
    () => [...new Set(result.claim_results.flatMap((c) => c.check_item_candidates))],
    [result]
  );

  const toggle = (id: string) => setActiveClaimId((cur) => (cur === id ? null : id));
  const silver = result.silver_verdict as VerifyVerdict | undefined;

  return (
    <div>
      <div style={{ background: "#fff", border: "1px solid #eaeef5", borderRadius: 12, padding: "14px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <VerdictBadge verdict={result.verdict} big />
          {silver && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 11, color: "#94a3b8" }}>silver参考</span>
              <VerdictTag v={silver} />
              <Tag
                color={silver === result.verdict ? "cyan" : "orange"}
                style={{ fontSize: 10, margin: 0 }}
              >
                {silver === result.verdict ? "与silver一致" : "与silver不一致"}
              </Tag>
            </span>
          )}
          <span style={{ fontSize: 11.5, color: "#64748b" }}>
            {result.latency_ms != null ? `耗时 ${result.latency_ms.toFixed(1)} ms · ` : ""}
            {result.claim_results.length}条claim · {result.evidence.length}块证据 · status {result.status}
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>命中检测项:</span>
            {checkItems.length === 0 ? (
              <span style={{ fontSize: 11, color: "#b0b9c9" }}>无</span>
            ) : (
              checkItems.map((id) => (
                <Tooltip key={id} title={id}>
                  <Tag color="geekblue" style={{ fontSize: 11, margin: 0 }}>{checkItemName(id)}</Tag>
                </Tooltip>
              ))
            )}
          </span>
        </div>
        {result.rationale && (
          <Paragraph
            style={{ margin: "8px 0 0", fontSize: 11.5, color: "#64748b" }}
            ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}
          >
            {result.rationale}
          </Paragraph>
        )}
      </div>

      <Card
        size="small"
        style={{ marginTop: 12 }}
        title={
          <span>
            Claim分解
            <Tag style={{ marginLeft: 8, fontSize: 10 }}>{result.claim_results.length}条</Tag>
          </span>
        }
        extra={<span style={{ fontSize: 11, color: "#94a3b8" }}>点击claim联动高亮证据</span>}
      >
        {result.claim_results.map((c) => (
          <ClaimRow
            key={c.claim_id}
            claim={c}
            active={activeClaimId === c.claim_id}
            onClick={() => toggle(c.claim_id)}
          />
        ))}
      </Card>

      <Card
        size="small"
        style={{ marginTop: 12 }}
        title={
          <span>
            冻结证据
            <Tag style={{ marginLeft: 8, fontSize: 10 }}>{result.evidence.length}块</Tag>
          </span>
        }
        extra={
          <span style={{ fontSize: 11, color: "#94a3b8" }}>
            {activeClaim ? "高亮=当前claim引用" : "高亮=被claim引用"}
          </span>
        }
      >
        {result.evidence.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无冻结证据" />
        ) : (
          result.evidence.map((ev) => (
            <EvidenceCard
              key={ev.evidence_id}
              block={ev}
              highlighted={highlightBases.has(ev.evidence_id)}
              exactRefs={exactRefsByBase.get(ev.evidence_id)}
            />
          ))
        )}
      </Card>

      <div style={{ marginTop: 10, fontSize: 11, color: "#b0b9c9", lineHeight: 1.8 }}>
        NIE = 当前证据无法判定(开放世界假设), 非正确也非错误 ·
        silver标签为GLM-5.3复核的评测参考(非gold) ·
        证据来自冻结快照(context_freeze_id), 校验过程不做重新检索
      </div>
    </div>
  );
}

export default function VerifyPanel() {
  const [qaList, setQaList] = useState<VerifyQaItem[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [preset, setPreset] = useState<PresetName>("fast");
  const [verifying, setVerifying] = useState(false);
  const [runSeq, setRunSeq] = useState(0);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchVerifyQaList()
      .then((items) => { if (alive) setQaList(items); })
      .catch((e: unknown) => {
        if (alive) setListError(String(e instanceof Error ? e.message : e));
      })
      .finally(() => { if (alive) setListLoading(false); });
    return () => { alive = false; };
  }, []);

  const selected = useMemo(
    () => qaList.find((q) => q.instance_id === selectedId) ?? null,
    [qaList, selectedId]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return qaList;
    return qaList.filter((it) =>
      it.instance_id.toLowerCase().includes(q) ||
      it.question.toLowerCase().includes(q) ||
      (it.silver_verdict ?? "").toLowerCase().includes(q));
  }, [qaList, search]);

  const selectQa = (id: string) => {
    setSelectedId(id);
    setResult(null);
    setResultError(null);
  };

  const runVerify = async () => {
    if (!selected) return;
    setVerifying(true);
    setResultError(null);
    setResult(null);
    try {
      const r = await verifyQaById(selected.instance_id, preset, "srs_scene1");
      setResult(r);
      setRunSeq((n) => n + 1);
    } catch (e: unknown) {
      setResultError(String(e instanceof Error ? e.message : e));
    } finally {
      setVerifying(false);
    }
  };

  const columns = [
    {
      title: "ID", dataIndex: "instance_id", width: 96,
      render: (v: string) => (
        <code style={{
          fontSize: 11, color: v === selectedId ? "#2563eb" : "#64748b",
          fontWeight: v === selectedId ? 700 : 400,
        }}>
          {v}
        </code>
      ),
    },
    { title: "问题", dataIndex: "question", ellipsis: true },
    {
      title: "silver", dataIndex: "silver_verdict", width: 76,
      render: (v?: string) =>
        v ? <VerdictTag v={v as VerifyVerdict} /> : <Tag style={{ fontSize: 10, margin: 0 }}>—</Tag>,
    },
  ];

  return (
    <div style={{ height: "100%", display: "flex", gap: 12, padding: 12, overflow: "hidden" }}>
      <style>{EVIDENCE_TABLE_CSS}</style>

      <Card
        size="small"
        title={
          <span>
            冻结QA语料
            <Tag style={{ marginLeft: 8, fontSize: 10 }}>{qaList.length}条</Tag>
            <Tag style={{ fontSize: 10 }} color="blue">srs_scene1</Tag>
          </span>
        }
        style={{ width: 430, flexShrink: 0, display: "flex", flexDirection: "column" }}
        styles={{ body: { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", paddingTop: 8 } }}
      >
        <Input
          allowClear
          prefix={<SearchOutlined style={{ color: "#94a3b8" }} />}
          placeholder="搜索ID / 问题 / silver标签"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ marginBottom: 8 }}
        />
        <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
          {listError ? (
            <Alert type="error" showIcon message="加载失败" description={listError} />
          ) : (
            <Table
              size="small"
              rowKey="instance_id"
              columns={columns}
              dataSource={filtered}
              loading={listLoading}
              pagination={{ pageSize: 12, size: "small", showTotal: (t) => `${t}条` }}
              onRow={(r) => ({
                onClick: () => selectQa(r.instance_id),
                style: {
                  cursor: "pointer",
                  background: r.instance_id === selectedId ? "#eff6ff" : undefined,
                },
              })}
            />
          )}
        </div>
      </Card>

      <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>
        {!selected ? (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Empty description="从左侧选择一条冻结QA, 选择preset后点击「开始校验」" />
          </div>
        ) : (
          <>
            <Card
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <span style={{ fontSize: 13.5 }}>
                  <code style={{
                    fontSize: 11, background: "#eff6ff", color: "#2563eb",
                    padding: "1px 6px", borderRadius: 4, marginRight: 8,
                  }}>
                    {selected.instance_id}
                  </code>
                  {selected.question.slice(0, 32)}…
                </span>
              }
              extra={
                selected.silver_verdict
                  ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 11, color: "#94a3b8" }}>silver</span>
                      <VerdictTag v={selected.silver_verdict as VerifyVerdict} />
                    </span>
                  )
                  : null
              }
            >
              <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <Text strong style={{ fontSize: 11.5, color: "#2563eb", flexShrink: 0 }}>Q</Text>
                <div style={{ fontSize: 12.5, lineHeight: 1.7 }}>{selected.question}</div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-start", marginTop: 6 }}>
                <Text strong style={{ fontSize: 11.5, color: "#059669", flexShrink: 0 }}>A</Text>
                <Paragraph
                  style={{ margin: 0, fontSize: 12, color: "#475569" }}
                  ellipsis={{ rows: 4, expandable: true, symbol: "展开全文" }}
                >
                  {selected.answer}
                </Paragraph>
              </div>
            </Card>

            <Card size="small" title="一致性校验" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <Radio.Group
                  optionType="button"
                  size="small"
                  options={PRESET_OPTIONS}
                  value={preset}
                  onChange={(e) => setPreset(e.target.value as PresetName)}
                />
                <Button
                  type="primary"
                  size="small"
                  icon={<ThunderboltOutlined />}
                  loading={verifying}
                  disabled={!selected}
                  onClick={runVerify}
                >
                  开始校验
                </Button>
                <span style={{ fontSize: 11, color: "#94a3b8" }}>{PRESET_HINTS[preset]}</span>
              </div>
              {verifying && (
                <div style={{ padding: "36px 0", textAlign: "center" }}>
                  <Spin />
                  <div style={{ marginTop: 10, fontSize: 12, color: "#64748b" }}>
                    正在执行 {preset} 档级联校验…
                  </div>
                </div>
              )}
              {resultError && (
                <Alert
                  type="error"
                  showIcon
                  style={{ marginTop: 12 }}
                  message="校验失败"
                  description={resultError}
                />
              )}
            </Card>

            {result && !verifying && (
              <ResultView key={`${result.instance_id}:${runSeq}`} result={result} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
