"""One-off patcher: wire srs.js to the new /api/check contract (M101).

Edits (surgical, by function boundaries):
  1. DB.cstReport global + 'undet' chip state
  2. cstStartCheck → new service flow (POST /api/check → poll → report)
  3. mQaCheck → new-format sample detail (violations table), old path as fallback
  4. mTotalReport → new-format total report, old path as fallback
"""
from pathlib import Path

SRC = Path(r"C:\Users\12488\Desktop\data_clean"
           r"\deploy\nkuDataProject\frontend\js\consist\srs.js")
text = SRC.read_text(encoding="utf-8")


def replace_span(text: str, start_marker: str, new_code: str) -> str:
    """Replace from start_marker to the next top-level '\\nfunction '."""
    idx = text.find(start_marker)
    assert idx >= 0, f"marker not found: {start_marker[:50]}"
    nxt = text.find("\nfunction ", idx + 10)
    assert nxt > idx
    return text[:idx] + new_code + text[nxt:]


# ── 1. globals + chip ────────────────────────────────────────────────────────
old_global = ("DB.qaCst = {};   /* qaIndex → {st:'checking'|'pass'|'fail', n} */")
assert old_global in text, "qaCst global not found"
text = text.replace(old_global, old_global
    + "\nDB.cstReport = null;  /* 新版统一校验报告(/api/check契约) */")

old_chip = ("const cst = !c ? '<span class=\"tag\">未校验</span>'\n"
            "      : (c.st === 'checking' ? '<span class=\"tag info\">校验中</span>'\n"
            "        : (c.st === 'fail' ? '<span class=\"tag err\">发现问题</span>' : '<span class=\"tag ok\">通过</span>'));")
assert old_chip in text, "chip not found"
new_chip = ("const cst = !c ? '<span class=\"tag\">未校验</span>'\n"
            "      : (c.st === 'checking' ? '<span class=\"tag info\">校验中</span>'\n"
            "        : (c.st === 'fail' ? '<span class=\"tag err\">发现问题</span>'\n"
            "          : (c.st === 'undet' ? '<span class=\"tag wait\">无法判定</span>' : '<span class=\"tag ok\">通过</span>')));")
text = text.replace(old_chip, new_chip)

# ── 2. cstStartCheck ────────────────────────────────────────────────────────
NEW_CST_START = """/* 开始校验: 新版统一校验契约(scene1 + qa_pairs → check_id → 轮询 → 报告) */
async function cstStartCheck(){
  if (S.cstMain.running) return;
  const scope = S.cstMain.doc || 'all';
  const all = qaList(scope);
  const list = all.filter(q => S.cstMain.sel[q.idx]);
  const target = list.length > 0 ? list : all;
  if (!target.length) return toast('当前范围无问答对', 'err');
  S.cstMain.running = true;
  target.forEach(q => { DB.qaCst[q.idx] = { st: 'checking', n: 0 }; });
  render();
  toast('已提交校验任务…', 'ok');
  const BASE = (location.protocol==='file:'||location.port==='8080') ? 'http://127.0.0.1:8300' : '';
  try{
    const qa_pairs = target.map(function(q){
      return { sample_id: 'q' + q.idx,
               question: String(q.q || q.question || ''),
               answer: String(q.a || q.answer || ''),
               source: String(q.doc || ''),
               knowledge_refs: [] };
    });
    const r = await fetch(BASE + '/api/check', { method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ scene: 'scene1', qa_pairs: qa_pairs }) });
    const j = await r.json();
    if (!j || !j.ok || !j.data || !j.data.check_id){
      throw new Error('校验服务受理失败' + (j && j.error ? ': ' + j.error.message : ''));
    }
    const checkId = j.data.check_id;
    let report = null;
    for (let i = 0; i < 300; i++){
      await new Promise(r2 => setTimeout(r2, 1000));
      const rs = await fetch(BASE + '/api/check-status/' + checkId);
      const js = await rs.json();
      if (!(js && js.ok && js.data)) continue;
      const st = js.data.status;
      if (st === 'running' && js.data.progress){
        const done = js.data.progress.completed || 0;
        target.slice(0, done).forEach(function(q){
          if (DB.qaCst[q.idx] && DB.qaCst[q.idx].st === 'checking') return;
          DB.qaCst[q.idx] = { st: 'checking', n: 0 }; });
        render();
      }
      if (st === 'done'){
        const rr = await fetch(BASE + '/api/check-reports/' + checkId);
        const jr = await rr.json();
        if (jr && jr.ok && jr.data && jr.data.report) report = jr.data.report;
        break;
      }
      if (st === 'error'){
        throw new Error((js.data.error && js.data.error.message) || '校验引擎异常');
      }
    }
    if (!report) throw new Error('校验引擎超时或未返回报告');
    DB.cstReport = report;
    const bySid = {};
    report.samples.forEach(function(s){ bySid[s.sample_id] = s; });
    target.forEach(function(q){
      const s = bySid['q' + q.idx];
      if (!s){ delete DB.qaCst[q.idx]; return; }
      const n = (s.violations || []).length;
      const st = s.consistency_result === 'inconsistent' ? 'fail'
        : (s.consistency_result === 'consistent' ? 'pass' : 'undet');
      DB.qaCst[q.idx] = { st: st, n: n };
    });
    S.cstMain.running = false;
    S.cstMain.offline = false;
    render();
    toast('校验完成：不一致 ' + report.summary.inconsistent + ' / '
      + report.summary.total, 'ok');
  } catch(e){
    S.cstMain.running = false;
    render();
    toast('校验失败: ' + e.message, 'err');
    cstCheckOffline(target, e.message);
  }
}
"""
text = replace_span(text, "async function cstStartCheck(){", NEW_CST_START)

# ── 3. mQaCheck: prepend new-format branch ──────────────────────────────────
NEW_QA_BRANCH = """function mQaCheck(idx){
  /* 新版报告优先: /api/check契约的violations逐条明细 */
  if (DB.cstReport){
    const sid = 'q' + idx;
    const sample = DB.cstReport.samples.find(s => s.sample_id === sid) || null;
    const q0 = (typeof REAL_QA !== 'undefined' && REAL_QA[idx]) ? REAL_QA[idx] : null;
    const question = sample ? sample.question : (q0 ? q0.q : '');
    const answer = sample ? sample.answer : (q0 ? q0.a : '');
    const stMap = { consistent: '<span class="tag ok">一致</span>',
                    inconsistent: '<span class="tag err">不一致</span>',
                    undetermined: '<span class="tag wait">无法判定</span>' };
    if (!sample){
      return openModal(mask('<div class="modal w860 cst-scope"><div class="m-hd"><h3>一致性校验报告 · #' + (idx+1) + '</h3><span class="m-x" onclick="closeModal()">✕</span></div><div class="m-bd" style="background:#eef1f6"><div class="empty" style="padding:16px"><span class="big">—</span><br>本样本不在最近一次校验范围内</div></div></div>'));
    }
    const stat = stMap[sample.consistency_result] || '<span class="tag">未校验</span>';
    const vioRows = (sample.violations || []).map(function(v){
      return '<tr><td style="width:84px"><code style="font-size:var(--fs-sm)">' + esc(v.item_id) + '</code></td>'
        + '<td class="small">' + esc(v.item_name || '') + '</td>'
        + '<td class="small">' + esc(v.description || '') + '</td>'
        + '<td style="width:190px"><code style="font-size:var(--fs-sm)">' + esc(v.affected_answer || '') + '</code></td>'
        + (v.root_cause ? '<td class="small">' + esc((v.root_cause.source || '') + ' · ' + (v.root_cause.operation || '')) + '</td>' : '') + '</tr>';
    }).join('');
    const hasRc = (sample.violations || []).some(v => v.root_cause);
    return openModal(mask('<div class="modal w860 cst-scope"><div class="m-hd"><h3>一致性校验报告 · #' + (idx+1) + '</h3><span class="m-x" onclick="closeModal()">✕</span></div>'
      + '<div class="m-bd" style="background:#eef1f6">'
      + '<div class="stats" style="margin-bottom:12px">'
      + '<div class="stat b"><div class="k">校验结论</div><div class="v" style="font-size:var(--fs-base)">' + stat + '</div></div>'
      + '<div class="stat o"><div class="k">违反条目</div><div class="v">' + (sample.violations || []).length + '</div></div></div>'
      + '<div style="background:#fff;border-radius:8px;padding:14px">'
      + '<div style="font-size:var(--fs-base);font-weight:650;margin-bottom:6px">问题：' + esc(question) + '</div>'
      + '<div style="font-size:var(--fs-sm);color:var(--txt2);margin-bottom:12px">答案：' + esc(answer.slice(0, 120)) + '</div>'
      + '<div style="font-size:var(--fs-base);font-weight:650;margin:8px 0 6px">违反的校验条目</div>'
      + ((sample.violations || []).length
        ? '<div class="tbwrap"><table class="tb" style="font-size:var(--fs-sm)"><thead><tr>'
          + '<th style="width:84px">条目</th><th>名称</th><th>违反原因</th><th style="width:190px">答案相关值</th>'
          + (hasRc ? '<th style="width:140px">根因</th>' : '') + '</tr></thead><tbody>' + vioRows + '</tbody></table></div>'
        : '<div class="empty" style="padding:16px"><span class="big">✓</span><br>本样本未发现不一致</div>')
      + '</div></div></div>'));
  }
  /* 旧离线演示路径(无新版报告时回退) */
"""
idx = text.find("function mQaCheck(idx){\n")
assert idx >= 0, "mQaCheck not found"
text = text[:idx] + NEW_QA_BRANCH + text[idx + len("function mQaCheck(idx){\n"):]

# ── 4. mTotalReport: prepend new-format branch ──────────────────────────────
NEW_TOTAL_BRANCH = """function mTotalReport(){
  /* 新版报告优先: summary + 不一致条目聚合 + 逐样本钻取 */
  if (DB.cstReport){
    const rep = DB.cstReport;
    const sm = rep.summary;
    const itemAgg = {};
    rep.samples.forEach(function(s){
      (s.violations || []).forEach(function(v){
        const key = v.item_id + '|' + (v.item_name || '');
        const e = itemAgg[key] = itemAgg[key]
          || { item_id: v.item_id, item_name: v.item_name || '', count: 0 };
        e.count++;
      });
    });
    const failing = Object.keys(itemAgg).map(k => itemAgg[k])
      .sort((a, b) => b.count - a.count);
    const stMap = { consistent: '<span class="tag ok">一致</span>',
                    inconsistent: '<span class="tag err">不一致</span>',
                    undetermined: '<span class="tag wait">无法判定</span>' };
    const itemRows = failing.map(function(e, i){
      return '<tr><td>' + (i+1) + '</td>'
        + '<td style="width:90px"><code style="font-size:var(--fs-sm)">' + esc(e.item_id) + '</code></td>'
        + '<td>' + esc(e.item_name) + '</td>'
        + '<td><b style="color:var(--red)">' + e.count + '</b></td></tr>';
    }).join('');
    const sampleRows = rep.samples.map(function(s){
      const vio = (s.violations || []).map(v => esc(v.item_id)).join('、');
      return '<tr style="cursor:pointer" onclick="mQaCheckBySid(\\'' + s.sample_id + '\\')">'
        + '<td class="small nowrap">' + esc(s.sample_id) + '</td>'
        + '<td class="ell small" style="max-width:280px">' + esc(s.question.slice(0, 60)) + '</td>'
        + '<td>' + (stMap[s.consistency_result] || esc(s.consistency_result)) + '</td>'
        + '<td class="small">' + (vio || '—') + '</td></tr>';
    }).join('');
    const html = '<div class="modal w1000 cst-scope" style="max-width:96vw"><div class="m-hd">'
      + '<h3>一致性校验总报告</h3><span class="m-x" onclick="closeModal()">✕</span></div>'
      + '<div class="m-bd" style="background:#eef1f6;max-height:78vh;overflow-y:auto">'
      + '<div class="stats" style="margin-bottom:14px">'
      + '<div class="stat b"><div class="k">样本总数</div><div class="v">' + sm.total + '</div></div>'
      + '<div class="stat g"><div class="k">一致</div><div class="v">' + sm.consistent + '</div></div>'
      + '<div class="stat r"><div class="k">不一致</div><div class="v">' + sm.inconsistent + '</div></div>'
      + '<div class="stat y"><div class="k">无法判定</div><div class="v">' + sm.undetermined + '</div></div></div>'
      + '<div class="card"><div class="card-hd"><h3>不一致条目聚合（' + failing.length + '项）</h3></div>'
      + '<div class="card-bd">'
      + (failing.length
        ? '<div class="tbwrap"><table class="tb"><thead><tr><th style="width:34px">序号</th>'
          + '<th style="width:90px">条目</th><th>名称</th><th style="width:70px">样本数</th>'
          + '</tr></thead><tbody>' + itemRows + '</tbody></table></div>'
        : '<div class="empty" style="padding:14px"><span class="big">✓</span><br>全部样本一致</div>')
      + '</div></div>'
      + '<div class="card" style="margin-top:12px"><div class="card-hd"><h3>逐样本结果（点击行查看明细）</h3></div>'
      + '<div class="card-bd"><div class="tbwrap"><table class="tb"><thead><tr>'
      + '<th style="width:130px">样本ID</th><th style="max-width:280px">问题</th>'
      + '<th style="width:90px">结论</th><th>违反条目</th></tr></thead><tbody>'
      + sampleRows + '</tbody></table></div></div></div>'
      + '</div></div>');
    return openModal(mask(html));
  }
  /* 旧离线演示路径(无新版报告时回退) */
"""
idx = text.find("function mTotalReport(){\n")
assert idx >= 0, "mTotalReport not found"
text = text[:idx] + NEW_TOTAL_BRANCH + text[idx + len("function mTotalReport(){\n"):]

# ── 5. mQaCheckBySid helper (drill-down by sample_id) ────────────────────────
HELPER = """function mQaCheckBySid(sid){
  const idx = parseInt(String(sid).slice(1), 10);
  if (isNaN(idx)) return toast('无效样本: ' + sid, 'err');
  mQaCheck(idx);
}
function mQaCheck(idx){"""
text = text.replace("function mQaCheck(idx){", HELPER, 1)

SRC.write_text(text, encoding="utf-8")
print("patched: globals+chip+cstStartCheck+mQaCheck+mTotalReport+helper")
