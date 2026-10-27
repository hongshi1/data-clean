import React, { useCallback, useEffect, useState } from "react";
import {
  Table, Tag, Button, Upload, message, Tooltip, Progress, Card, Empty, Spin,
} from "antd";
import {
  UploadOutlined, ApartmentOutlined, SafetyCertificateOutlined,
  DatabaseOutlined, CheckCircleFilled, WarningFilled, CloseCircleFilled,
  RobotOutlined,
} from "@ant-design/icons";

interface DatasetRow {
  doc_num: string;
  doc: string;
  n_nodes: number;
  n_edges: number;
  n_items: number;
  uploaded: boolean;
  checked: boolean;
  check_summary: null | {
    total: number; pass: number; warn: number; fail: number; llm: number;
  };
}

interface Props {
  onOpenWorkbench: (docNum: string) => void;
  onOpenCheck: (docNum: string) => void;
}

const DatasetManager: React.FC<Props> = ({ onOpenWorkbench, onOpenCheck }) => {
  const [rows, setRows] = useState<DatasetRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await window.fetch("/api/datasets");
      const j = await r.json();
      setRows(j.datasets ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const doUpload = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await window.fetch("/api/upload", { method: "POST", body: fd });
      const j = await r.json();
      if (j.ok) {
        message.success(`已导入「${j.doc}」(${j.n_nodes}个章节节点), 正在执行一致性校验…`);
        onOpenCheck(j.doc_num);
      } else {
        message.error(j.detail ?? "上传失败");
      }
    } catch (e) {
      message.error(`上传失败: ${String(e)}`);
    } finally {
      setUploading(false);
    }
    return false;
  };

  const statusBadge = (s: DatasetRow["check_summary"]) => {
    if (!s) return <Tag>未校验</Tag>;
    const parts: React.ReactNode[] = [];
    if (s.fail > 0) parts.push(<Tag key="f" icon={<CloseCircleFilled />} color="red">{s.fail} 确证</Tag>);
    if (s.warn > 0) parts.push(<Tag key="w" icon={<WarningFilled />} color="orange">{s.warn} 可疑</Tag>);
    if (s.fail === 0 && s.warn === 0) parts.push(<Tag key="p" icon={<CheckCircleFilled />} color="green">通过</Tag>);
    parts.push(<Tag key="l" icon={<RobotOutlined />} color="purple">{s.llm} 待LLM</Tag>);
    return <span>{parts}</span>;
  };

  const columns = [
    { title: "编号", dataIndex: "doc_num", width: 64,
      render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
    { title: "数据集名称", dataIndex: "doc", ellipsis: { showTitle: false },
      render: (v: string, r: DatasetRow) => (
        <Tooltip title={v} placement="topLeft">
          <span style={{ fontSize: 13, fontWeight: 550 }}>
            {r.uploaded ? "📎 " : ""}{v.replace(/需求规格说明-终稿|需求规格说明|软件/g, "")}
          </span>
        </Tooltip>
      ) },
    { title: "规模", width: 150,
      render: (_: unknown, r: DatasetRow) => (
        <span style={{ fontSize: 11.5, color: "#64748b" }}>
          {r.n_nodes}节点 · {r.n_edges}边{r.n_items ? ` · ${r.n_items}条目` : ""}
        </span>
      ) },
    { title: "校验状态(52项)", dataIndex: "check_summary", width: 280,
      render: (_: unknown, r: DatasetRow) => r.checked
        ? statusBadge(r.check_summary)
        : <Tag style={{ color: "#94a3b8" }}>未校验</Tag> },
    { title: "操作", width: 250, render: (_: unknown, r: DatasetRow) => (
      <span style={{ display: "flex", gap: 6 }}>
        <Button size="small" type="primary" ghost icon={<SafetyCertificateOutlined />}
                onClick={() => onOpenCheck(r.doc_num)}>
          一致性校验
        </Button>
        <Button size="small" icon={<ApartmentOutlined />}
                onClick={() => onOpenWorkbench(r.doc_num)}>
          上下文关联
        </Button>
      </span>
    )},
  ];

  return (
    <div style={{ padding: 20, height: "100%", overflowY: "auto" }}>
      {/* 顶部: 标题 + 上传 */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: 16, gap: 14 }}>
        <DatabaseOutlined style={{ fontSize: 20, color: "#2563EB" }} />
        <div>
          <div style={{ fontSize: 16, fontWeight: 750 }}>数据集一致性校验</div>
          <div style={{ fontSize: 11.5, color: "#94a3b8" }}>
            上传/选择数据集 → 52项一致性校验(术语8·参数10·逻辑11·GJB合规11·多模态12)
          </div>
        </div>
        <Upload accept=".md,.markdown,.txt" showUploadList={false}
                beforeUpload={doUpload} style={{ marginLeft: "auto" }}>
          <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
            上传数据集(.md)
          </Button>
        </Upload>
      </div>

      <Table
        rowKey="doc_num"
        size="small"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={false}
        expandable={{
          expandedRowRender: (r: DatasetRow) => (
            <div style={{ padding: "4px 6px", fontSize: 12, color: "#64748b" }}>
              完整名称: {r.doc} · 点击「一致性校验」执行52项检测并查看证据 ·
              点击「上下文关联」进入该文档的图谱召回工作台
            </div>
          ),
        }}
      />

      <div style={{ marginTop: 14, fontSize: 11, color: "#b0b9c9" }}>
        内置16份GJB 438C SRS数据集 · 上传数据集自动解析章节并执行文本类校验 ·
        多模态校验项依赖born-digital锚点资产(上传文档自动跳过)
      </div>
    </div>
  );
};

export default DatasetManager;
