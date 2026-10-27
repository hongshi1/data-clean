import React, { useCallback, useEffect, useState } from "react";
import { Table, Tag, Input, Select, Button, Space, Tooltip } from "antd";
import { ExperimentOutlined, SearchOutlined } from "@ant-design/icons";
import { fetchQa } from "../api";
import type { QaEntry } from "../types";

const SCENARIO_COLORS: Record<string, string> = {
  "1": "blue", "2": "geekblue", "3": "cyan", "4": "green",
  "5": "lime", "6": "gold", "7": "orange", "8": "purple",
};

const QA_TYPES = [
  "T2_table_factual", "T3_counting", "T4_tracing", "T5_text_understanding",
  "T7_consistency", "T8_cross_reference",
];

interface Props {
  onOpenInWorkbench: (question: string) => void;
}

const QaManager: React.FC<Props> = ({ onOpenInWorkbench }) => {
  const [data, setData] = useState<QaEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [scenario, setScenario] = useState<string | undefined>("4");
  const [qaType, setQaType] = useState<string | undefined>(undefined);
  const [label, setLabel] = useState<string | undefined>(undefined);
  const [injected, setInjected] = useState<boolean | undefined>(undefined);
  const [q, setQ] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetchQa({
        q: q || undefined, scenario, qa_type: qaType, label,
        injected: injected ?? null, page, page_size: pageSize,
      });
      setData(r.items);
      setTotal(r.total);
    } finally {
      setLoading(false);
    }
  }, [q, scenario, qaType, label, injected, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  const columns = [
    { title: "ID", dataIndex: "id", width: 110,
      render: (v: string) => <code style={{ fontSize: 11 }}>{v}</code> },
    { title: "场景", dataIndex: "scenario", width: 64,
      render: (v: string) => v ? <Tag color={SCENARIO_COLORS[v] ?? "default"}>sc{v}</Tag> : "-" },
    { title: "类型", dataIndex: "type", width: 140,
      render: (v: string) => v ? <Tag style={{ fontSize: 11 }}>{v}</Tag> : "-" },
    { title: "问题", dataIndex: "question", ellipsis: { showTitle: false },
      render: (v: string) => (
        <Tooltip title={v} placement="topLeft"><span style={{ fontSize: 12.5 }}>{v}</span></Tooltip>
      ) },
    { title: "答案", dataIndex: "answer", ellipsis: { showTitle: false },
      render: (v: string) => (
        <Tooltip title={v} placement="topLeft">
          <span style={{ fontSize: 12.5, color: "#0e7490" }}>{v}</span>
        </Tooltip>
      ) },
    { title: "标注", dataIndex: "label", width: 92,
      render: (v?: string) => v === "inconsistent" ? <Tag color="red">不一致</Tag>
        : v === "consistent" ? <Tag color="green">一致</Tag> : <Tag>未标注</Tag> },
    { title: "注入", dataIndex: "is_injected", width: 66,
      render: (v?: boolean) => v ? <Tag color="volcano">注入</Tag> : <Tag>原生</Tag> },
    { title: "难度", dataIndex: "difficulty", width: 72,
      render: (v?: string) => v ?? "-" },
    { title: "操作", width: 120, render: (_: unknown, rec: QaEntry) => (
      <Button size="small" icon={<ExperimentOutlined />}
              onClick={() => onOpenInWorkbench(rec.question)}>
        在工作台打开
      </Button>
    )},
  ];

  return (
    <div style={{ padding: 16, height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <Input
          style={{ width: 260 }} placeholder="搜索问题/答案" allowClear
          prefix={<SearchOutlined />} value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1); }}
        />
        <Select style={{ width: 130 }} placeholder="场景" allowClear value={scenario}
                onChange={(v) => { setScenario(v); setPage(1); }}
                options={[...Array(8)].map((_, i) => ({
                  value: String(i + 1), label: `场景${i + 1}`,
                }))} />
        <Select style={{ width: 180 }} placeholder="QA类型" allowClear value={qaType}
                onChange={(v) => { setQaType(v); setPage(1); }}
                options={QA_TYPES.map((t) => ({ value: t, label: t }))} />
        <Select style={{ width: 120 }} placeholder="标注" allowClear value={label}
                onChange={(v) => { setLabel(v); setPage(1); }}
                options={[
                  { value: "consistent", label: "一致" },
                  { value: "inconsistent", label: "不一致" },
                ]} />
        <Select style={{ width: 120 }} placeholder="来源" allowClear value={injected}
                onChange={(v) => { setInjected(v); setPage(1); }}
                options={[
                  { value: true, label: "注入" },
                  { value: false, label: "原生" },
                ]} />
        <span style={{ color: "#94a3b8", fontSize: 12, marginLeft: "auto" }}>
          共 {total} 条QA对
        </span>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        <Table
          rowKey="id"
          size="small"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            current: page, pageSize, total,
            showSizeChanger: true, showQuickJumper: true,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
          expandable={{
            expandedRowRender: (rec: QaEntry) => <QaExpand rec={rec} onOpen={onOpenInWorkbench} />,
            rowExpandable: () => true,
          }}
          scroll={{ y: "calc(100vh - 250px)" }}
        />
      </div>
    </div>
  );
};

const QaExpand: React.FC<{ rec: QaEntry; onOpen: (q: string) => void }> = ({ rec, onOpen }) => {
  const ev = typeof rec.evidence === "string" ? rec.evidence
    : rec.evidence ? Object.entries(rec.evidence as Record<string, string>)
        .map(([k, v]) => `${k}: ${v}`).join(" | ") : "";
  return (
    <div style={{ padding: "4px 8px", fontSize: 12.5, lineHeight: 1.9 }}>
      <div><b style={{ color: "#64748b" }}>问题:</b> {rec.question}</div>
      <div><b style={{ color: "#64748b" }}>答案:</b> {rec.answer}</div>
      {ev && <div><b style={{ color: "#64748b" }}>证据:</b> {ev}</div>}
      <Space wrap style={{ marginTop: 4 }}>
        {rec.doc && <Tag>doc{rec.doc.slice(0, 12)}</Tag>}
        {rec.section && <Tag>章节 {rec.section}</Tag>}
        {rec.image_caption && <Tag color="green">{rec.image_caption}</Tag>}
        {rec.table_caption && <Tag color="cyan">{rec.table_caption}</Tag>}
        {rec.rule_id && <Tag color="purple">{rec.rule_id}</Tag>}
        {rec.inject_detail && <Tag color="red">注入: {rec.inject_detail.slice(0, 40)}</Tag>}
      </Space>
      <div style={{ marginTop: 6 }}>
        <Button size="small" type="primary" ghost icon={<ExperimentOutlined />}
                onClick={() => onOpen(rec.question)}>
          在工作台打开(召回此问题)
        </Button>
      </div>
    </div>
  );
};

export default QaManager;
