/** API 类型定义 — 与后端 server/main.py 契约对齐 */

export type NodeType = "E" | "TXT" | "TBL" | "IMG" | "SEQ" | "KNW";

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  doc: string;
  section: string;
  payload: NodePayload;
  hop: number;
  score: number;
  is_seed: boolean;
}

export interface NodePayload {
  // E
  id_str?: string;
  aliases?: string[];
  n_occ?: number;
  // TXT
  title?: string;
  level?: number;
  text_preview?: string;
  text_len?: number;
  // TBL
  caption?: string;
  table_type?: string;
  row_count?: number;
  headers?: string[];
  // IMG
  img_type?: string;
  path?: string;
  exists?: boolean;
  mermaid_key?: string | null;
  // SEQ
  seq_type?: "anchor_chain" | "exception_flow";
  steps?: string[];
  n_steps?: number;
  defined?: string[];
  referenced?: string[];
  dangling?: string[];
  // KNW
  rule_type?: string;
  description?: string;
  severity?: string;
  source?: string;
}

export interface GraphEdge {
  s: string;
  t: string;
  type: string;
  w: number;
  ev: string;
}

export interface AggItem {
  entity_id: string;
  doc: string;
  sections: string[];
  n_occurrences: number;
  media: { modality: string; caption: string }[];
  chain_completeness: {
    has_title: boolean;
    has_func_table: boolean;
    has_qualification: boolean;
    has_trace: boolean;
    score: number;
  };
}

export interface SeedInfo {
  id: string;
  label: string;
  score: number;
  why: string;
}

export interface RelatedEntity {
  id: string;
  label: string;
  aliases?: string[];
  id_str?: string;
  score: number;
  rel: string;
  ev: string;
  node: GraphNode;
}

export interface ActivateResult {
  ok: boolean;
  question?: string;
  message?: string;
  doc?: string;
  doc_name?: string;
  /** 思维导图结构 */
  center?: GraphNode & { score?: number; why?: string };
  related_entities?: RelatedEntity[];
  groups?: Record<string, (GraphNode & { via?: string; via_label?: string })[]>;
  edges?: GraphEdge[];
  items?: AggItem[];
  stats?: {
    n_related: number;
    n_content: number;
    by_modality: Record<string, number>;
  };
}

export interface DocInfo {
  doc_num: string;
  doc: string;
  n_nodes: number;
  n_edges: number;
  n_items: number;
}

export interface QaEntry {
  id: string;
  pair_id?: string;
  scenario?: string;
  doc?: string;
  section?: string;
  type?: string;
  question: string;
  answer: string;
  evidence?: string | Record<string, string>;
  difficulty?: string;
  source?: string;
  image_path?: string;
  image_caption?: string;
  table_caption?: string;
  is_injected?: boolean;
  inject_detail?: string;
  rule_id?: string;
  label?: string;
}

export interface QaPage {
  total: number;
  page: number;
  page_size: number;
  items: QaEntry[];
}

/** 节点模态显示配置 */
export const MODALITY_CONFIG: Record<
  NodeType | "SEED",
  { name: string; color: string; sector: number }
> = {
  SEED: { name: "实体(种子)", color: "#2563EB", sector: 0 },
  E: { name: "实体", color: "#2563EB", sector: 0 },
  TXT: { name: "文本", color: "#64748B", sector: -135 },
  TBL: { name: "表格", color: "#0891B2", sector: -45 },
  IMG: { name: "图片", color: "#059669", sector: 45 },
  SEQ: { name: "时序", color: "#D97706", sector: 135 },
  KNW: { name: "知识", color: "#7C3AED", sector: 135 },
};
