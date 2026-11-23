import { useState, useCallback } from 'react';

// ============ Types ============
interface Chunk {
  chunk_id: string;
  type: string;
  bbox?: number[];
  det_conf?: number;
  pose_proxy?: {
    head_down?: boolean | null;
    prone_like?: boolean | null;
    torso_angle_from_vertical_deg?: number | null;
  };
  ppe_class?: string;
  wearing_state?: string;
  matched_person?: string | null;
  appearance?: {
    bgr?: number[];
    hex?: string;
    color_name?: string;
  };
}

interface VisualGraph {
  nodes: string[];
  edges: Array<{
    source: string;
    target: string;
    relation: string;
    confidence?: number;
    evidence?: string;
  }>;
  node_details: Chunk[];
}

interface Proposition {
  id: string;
  subject: string;
  predicate: string;
  object?: string;
  polarity?: string;
}

interface CrossModalMapping {
  claim_id: string;
  subject?: string;
  relation?: string;
  object?: string;
  polarity?: string;
  linked_chunks: string[];
  observation_status: string;
  visual_evidence?: {
    person_count: number;
    ppe_detections: number;
    wearing_count: number;
    not_wearing_count: number;
  };
}

interface Verdict {
  overall_verdict: string;
  per_claim_verdicts: Array<{
    item: string;
    verdict: string;
    reason: string;
    evidence_chunks: string[];
  }>;
}

interface PipelineResult {
  image_id: string;
  layers: {
    L1_chunks: {
      quality: Record<string, unknown>;
      chunks: {
        scene: Record<string, unknown>;
        entities: Chunk[];
        parts: Chunk[];
        text: Chunk[];
      };
      timings: Record<string, number>;
    };
    L2_visual_graph: VisualGraph;
    L3_qa_ner?: {
      method: string;
      model_response: string;
      parsed: {
        entities: Array<{ name: string; type: string; spatial_ref?: string }>;
        relations: Array<{ subject: string; predicate: string; object: string; negated?: boolean }>;
        person_scope: string;
        scene_conditions?: string[];
      };
    };
    L4_cross_modal: {
      mappings: CrossModalMapping[];
      linked_chunks: string[];
    };
    L5_nli_verification?: {
      premise: string;
      overall_verdict: string;
      method: string;
      per_claim_results: Array<{
        claim_id: string;
        hypothesis: string;
        label: string;
        verdict: string;
        confidence: number;
        scores: Record<string, number>;
      }>;
    };
    L5_rule_verification?: Verdict;
  };
  final_verdict: string;
  pipeline_version: string;
  verdict_method?: string;
}

// ============ API call ============
async function analyzeImage(imagePath: string, userText: string, gptText: string): Promise<PipelineResult> {
  const res = await fetch('/api/scenario5/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_path: imagePath, user_text: userText, gpt_text: gptText }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Analysis failed');
  }
  return res.json();
}

// ============ Styles ============
const styles: Record<string, React.CSSProperties> = {
  container: { padding: 20, fontFamily: "'Microsoft YaHei', sans-serif" },
  section: { background: '#f7f3fc', borderRadius: 8, padding: 16, marginBottom: 16, border: '1px solid #e0d5f0' },
  sectionTitle: { fontSize: 14, fontWeight: 700, color: '#673799', marginBottom: 8 },
  verdict: {
    padding: '12px 20px',
    borderRadius: 8,
    fontSize: 18,
    fontWeight: 700,
    textAlign: 'center' as const,
    marginBottom: 16,
  },
  chip: {
    display: 'inline-block',
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 12,
    marginRight: 6,
    marginBottom: 4,
  },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: 12 },
  th: { background: '#673799', color: '#fff', padding: '6px 10px', textAlign: 'left' as const },
  td: { padding: '6px 10px', borderBottom: '1px solid #e0d5f0' },
  card: { background: '#fff', borderRadius: 8, padding: 12, border: '1px solid #e0d5f0', marginBottom: 8 },
  label: { fontSize: 11, color: '#69 60 74', marginTop: 4 },
  btn: {
    background: '#673799', color: '#fff', border: 'none', borderRadius: 6,
    padding: '10px 24px', fontSize: 14, cursor: 'pointer',
  },
  input: { width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d0c0e8', fontSize: 13 },
  textarea: { width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d0c0e8', fontSize: 13, minHeight: 60 },
};

const verdictColors: Record<string, string> = {
  support: '#009663',
  refute: '#b43c50',
  NIE: '#6960 74',
  suspicious: '#b48232',
};

// ============ Component ============
export default function Scenario5Panel() {
  const [imagePath, setImagePath] = useState('');
  const [userText, setUserText] = useState('判断图片中是否有人员未佩戴安全帽');
  const [gptText, setGptText] = useState('{"task":"安全帽检测","answer":1,"evidence":["有人员未佩戴安全帽"]}');
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await analyzeImage(imagePath, userText, gptText);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [imagePath, userText, gptText]);

  return (
    <div style={styles.container}>
      <h2 style={{ color: '#673799' }}>场景5 · 安全帽佩戴一致性校验</h2>
      <p style={{ color: '#696074', fontSize: 13 }}>
        视觉Chunk提取 → 图内关系建模 → QA语义解析 → 跨模态关联 → 一致性判定
      </p>

      {/* Input Section */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>📋 输入</div>
        <div style={{ marginBottom: 8 }}>
          <label style={styles.label}>图片路径：</label>
          <input
            style={styles.input}
            value={imagePath}
            onChange={(e) => setImagePath(e.target.value)}
            placeholder="例如: scenario5/data/ppe_hardhat/extracted/xxx.jpg"
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <label style={styles.label}>QA指令（user）：</label>
          <textarea style={styles.textarea} value={userText} onChange={(e) => setUserText(e.target.value)} />
        </div>
        <div style={{ marginBottom: 8 }}>
          <label style={styles.label}>QA回答（gpt）：</label>
          <textarea style={styles.textarea} value={gptText} onChange={(e) => setGptText(e.target.value)} />
        </div>
        <button style={styles.btn} onClick={handleAnalyze} disabled={loading || !imagePath}>
          {loading ? '⏳ 分析中...' : '🔍 运行一致性校验'}
        </button>
        {error && <p style={{ color: 'red', fontSize: 13 }}>❌ {error}</p>}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Verdict */}
          <div
            style={{
              ...styles.verdict,
              background: verdictColors[result.final_verdict] || '#696074',
              color: '#fff',
            }}
          >
            最终判定: {result.final_verdict.toUpperCase()}
          </div>

          {/* L1: Chunks */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>📦 Layer 1 · 视觉Chunk提取</div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ ...styles.chip, background: '#e8dcf5', color: '#673799' }}>
                图片质量: usable={String((result.layers.L1_chunks.quality as Record<string, unknown>)?.usable)}
              </span>
              {result.layers.L1_chunks.chunks.entities
                .filter((c) => c.type === 'person')
                .map((c) => (
                  <span key={c.chunk_id} style={{ ...styles.chip, background: '#d0e8f5', color: '#2a6099' }}>
                    {c.chunk_id} (conf={c.det_conf})
                    {c.appearance?.color_name && ` · ${c.appearance.color_name}`}
                    {c.pose_proxy?.prone_like && ' · 趴伏'}
                    {c.pose_proxy?.head_down && ' · 低头'}
                  </span>
                ))}
              {result.layers.L1_chunks.chunks.entities
                .filter((c) => c.type === 'ppe')
                .map((c) => (
                  <span
                    key={c.chunk_id}
                    style={{
                      ...styles.chip,
                      background: c.wearing_state === 'wearing' ? '#d0f5dc' : '#f5d0d0',
                      color: c.wearing_state === 'wearing' ? '#009663' : '#b43c50',
                    }}
                  >
                    {c.chunk_id}: {c.ppe_class}
                    {c.appearance?.color_name && ` (${c.appearance.color_name})`}
                  </span>
                ))}
            </div>
          </div>

          {/* L2: Visual Graph */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>🔗 Layer 2 · 图内关系 ({result.layers.L2_visual_graph.edges.length} edges)</div>
            {result.layers.L2_visual_graph.edges.slice(0, 10).map((e, i) => (
              <div key={i} style={{ fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: '#673799', fontWeight: 600 }}>{e.source}</span>
                <span style={{ color: '#b48232' }}> ──[{e.relation}]──→ </span>
                <span style={{ color: '#673799', fontWeight: 600 }}>{e.target}</span>
                {e.evidence && <span style={{ color: '#696074', fontSize: 11 }}> ({e.evidence})</span>}
              </div>
            ))}
            {result.layers.L2_visual_graph.edges.length > 10 && (
              <div style={{ fontSize: 11, color: '#696074' }}>
                ... 还有 {result.layers.L2_visual_graph.edges.length - 10} 条边
              </div>
            )}
          </div>

          {/* L3: QA NER (Qwen) */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>📝 Layer 3 · QA语义解析（Qwen NER）</div>
            {result.layers.L3_qa_ner ? (
              <>
                <div style={{ fontSize: 12, color: '#696074', marginBottom: 8 }}>
                  方法: {result.layers.L3_qa_ner.method}
                </div>
                {result.layers.L3_qa_ner.parsed?.entities?.map((e, i) => (
                  <span key={i} style={{ ...styles.chip, background: '#d0e8f5', color: '#2a6099' }}>
                    {e.name} ({e.type}){e.spatial_ref && ` · ${e.spatial_ref}`}
                  </span>
                ))}
                {result.layers.L3_qa_ner.parsed?.relations?.map((r, i) => (
                  <div key={i} style={{ fontSize: 12, marginTop: 4 }}>
                    <b>{r.subject}</b> ──[{r.predicate}{r.negated ? ' (否定)' : ''}]──→ <b>{r.object}</b>
                  </div>
                ))}
                {(!result.layers.L3_qa_ner.parsed?.relations || result.layers.L3_qa_ner.parsed.relations.length === 0) && (
                  <div style={{ fontSize: 12, color: '#b48232' }}>⚠ NER未抽取到关系，使用evidence fallback</div>
                )}
              </>
            ) : (
              <div style={{ fontSize: 12, color: '#696074' }}>v1格式（关键词解析）</div>
            )}
          </div>

          {/* L4: Cross-Modal */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>🔀 Layer 4 · 跨模态关联 ({result.layers.L4_cross_modal.mappings.length} mappings)</div>
            {result.layers.L4_cross_modal.mappings.map((m, i) => (
              <div key={i} style={styles.card}>
                <b>{m.claim_id}</b>: {m.relation} → 状态: <b>{m.observation_status}</b>
                <div style={{ fontSize: 11, color: '#696074', marginTop: 4 }}>
                  关联Chunk: {m.linked_chunks.join(', ')}
                  {m.visual_evidence && (
                    <span>
                      {' '}| 人员={m.visual_evidence.person_count}, PPE={m.visual_evidence.ppe_detections},
                      戴帽={m.visual_evidence.wearing_count}, 未戴={m.visual_evidence.not_wearing_count}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* L5: NLI Verification */}
          {result.layers.L5_nli_verification && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>🧠 Layer 5a · NLI模型裁决（Erlangshen-330M）</div>
              <div style={{ ...styles.card, background: '#f0f8f0' }}>
                <b>视觉事实（Premise）：</b> {result.layers.L5_nli_verification.premise}
              </div>
              {result.layers.L5_nli_verification.per_claim_results.map((r, i) => (
                <div key={i} style={styles.card}>
                  <span
                    style={{
                      ...styles.chip,
                      background: verdictColors[r.verdict] || '#696074',
                      color: '#fff',
                    }}
                  >
                    {r.verdict.toUpperCase()} ({r.label})
                  </span>
                  <b>声称：</b>{r.hypothesis}
                  <div style={{ fontSize: 11, color: '#696074', marginTop: 4 }}>
                    置信度: {r.confidence} | E={r.scores?.entailment || 0} N={r.scores?.neutral || 0} C={r.scores?.contradiction || 0}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* L5: Rule Verification */}
          {result.layers.L5_rule_verification && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>⚖️ Layer 5b · 规则校验</div>
              {result.layers.L5_rule_verification.per_claim_verdicts.map((v, i) => (
                <div key={i} style={styles.card}>
                  <span
                    style={{
                      ...styles.chip,
                      background: verdictColors[v.verdict] || '#696074',
                      color: '#fff',
                    }}
                  >
                    {v.verdict.toUpperCase()}
                  </span>
                  <b>{v.item}</b>: {v.reason}
                  <div style={{ fontSize: 11, color: '#696074', marginTop: 4 }}>
                    证据Chunk: {v.evidence_chunks.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
