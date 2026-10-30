import type {
  ActivateResult, DocInfo, QaPage, VerifyQaItem, VerifyResult,
} from "./types";

const BASE = "";

export async function fetchDocs(): Promise<DocInfo[]> {
  const r = await fetch(`${BASE}/api/docs`);
  const j = await r.json();
  return j.docs;
}

export async function activate(
  question: string,
  opts: { doc?: string | null; k?: number; top_k?: number; min_w?: number } = {}
): Promise<ActivateResult> {
  const r = await fetch(`${BASE}/api/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      doc: opts.doc ?? null,
      k: opts.k ?? 2,
      top_k: opts.top_k ?? 12,
      min_w: opts.min_w ?? 0.3,
    }),
  });
  return r.json();
}

export async function fetchQa(params: {
  q?: string;
  scenario?: string;
  qa_type?: string;
  label?: string;
  injected?: boolean | null;
  page?: number;
  page_size?: number;
}): Promise<QaPage> {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.scenario) sp.set("scenario", params.scenario);
  if (params.qa_type) sp.set("qa_type", params.qa_type);
  if (params.label) sp.set("label", params.label);
  if (params.injected !== null && params.injected !== undefined)
    sp.set("injected", String(params.injected));
  sp.set("page", String(params.page ?? 1));
  sp.set("page_size", String(params.page_size ?? 20));
  const r = await fetch(`${BASE}/api/qa?${sp.toString()}`);
  return r.json();
}

/** IMG节点 → 图片URL */
export function imageUrl(node: { id: string; payload: { path?: string } }): string | null {
  const docNum = node.id.split(":")[1];
  const p = node.payload?.path;
  if (!p) return null;
  return `${BASE}/api/assets/${docNum}/${p}`;
}

/** 章节全文 */
export async function fetchSection(docNum: string, section: string): Promise<{ title: string; text: string }> {
  const r = await fetch(`${BASE}/api/section/${docNum}/${encodeURIComponent(section)}`);
  if (!r.ok) return { title: "", text: "" };
  return r.json();
}

/** 表格HTML */
export async function fetchTable(docNum: string, caption: string): Promise<string> {
  const r = await fetch(`${BASE}/api/table/${docNum}?caption=${encodeURIComponent(caption)}`);
  if (!r.ok) return "";
  const j = await r.json();
  return j.html ?? "";
}

/** 图片的Mermaid导出 */
export async function fetchMermaid(docNum: string, figNum: string): Promise<{ has: boolean; code: string; type: string }> {
  const r = await fetch(`${BASE}/api/mermaid/${docNum}/${figNum}`);
  if (!r.ok) return { has: false, code: "", type: "" };
  const j = await r.json();
  return { has: !!j.has_mermaid, code: j.mermaid ?? "", type: j.diagram_type ?? "" };
}

/** 91条冻结QA轻量列表 */
export async function fetchVerifyQaList(): Promise<VerifyQaItem[]> {
  const r = await fetch(`${BASE}/api/verify/qa_list`);
  if (!r.ok) throw new Error(`加载冻结QA列表失败 (HTTP ${r.status})`);
  return r.json();
}

/** 按instance_id校验冻结QA */
export async function verifyQaById(
  id: string,
  preset: string,
  scene: string
): Promise<VerifyResult> {
  const r = await fetch(`${BASE}/api/verify_qa/${encodeURIComponent(id)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset, scene }),
  });
  if (!r.ok) {
    let detail = `校验请求失败 (HTTP ${r.status})`;
    try {
      const j = await r.json();
      if (j?.detail) detail = String(j.detail);
    } catch {
      detail = `校验请求失败 (HTTP ${r.status})`;
    }
    throw new Error(detail);
  }
  return r.json();
}
