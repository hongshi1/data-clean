#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原型增强构建: 把一致性校验模块(上下文关联+52项校验)注入《微调数据集构建平台》

输入: docs/doc11/原型模板/微调数据集构建平台.html + _demo_data.json
输出: docs/doc11/原型模板/微调数据集构建平台-一致性校验增强版.html

7个注入点, 每个锚点替换计数必须=1, 否则构建失败。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(BASE, "docs/doc11/原型模板")
SRC = os.path.join(TPL_DIR, "微调数据集构建平台.html")
OUT = os.path.join(TPL_DIR, "微调数据集构建平台-一致性校验增强版.html")
DEMO = json.load(open(os.path.join(TPL_DIR, "_demo_data.json"), encoding="utf-8"))


def inject(html, anchor, replacement, name, count=1):
    n = html.count(anchor)
    if n != count:
        raise SystemExit(f"[FAIL] 锚点「{name}」命中 {n} 次(期望{count}): {anchor[:60]}...")
    html = html.replace(anchor, replacement)
    print(f"  [OK] {name} ({count}处)")
    return html


html = open(SRC, encoding="utf-8").read()
print(f"读入原型: {len(html)}字符")

# ======================================================================
# 模块代码块: 上下文关联 + 52项校验 (遵循原型vanilla JS约定)
# ======================================================================
gd = DEMO["graph_demo"]
checks = DEMO["checks"]
MODULE_CODE = """/* ============================================================
   一致性校验模块增强: SRS数据集校验 + 上下文关联图谱 (真实数据驱动)
   数据源: 16份GJB 438C SRS · 5619节点图谱 · 52项校验引擎
   ============================================================ */
const SRS_DEMO = __DEMO_JSON__;
/* 52项校验项注册表(术语8·参数10·逻辑11·GJB11·多模态12) */
const CHECK52_ALL = SRS_DEMO.checks['02'].items.map(i => ({ id:i.id, category:i.category, name:i.name, mode:i.mode, modality:i.modality }));
const CST_CATS = ['术语层','参数层','逻辑层','GJB合规层','多模态层'];
S.cstMain = { doc:'' };
S.cstGraph = { node:null };
DB.srsChecks = {};
/* 已有真实结果的数据集(引擎实跑) */
DB.srsChecks['01'] = SRS_DEMO.checks['01'];
DB.srsChecks['02'] = SRS_DEMO.checks['02'];

/* ---- 校验总览: 左数据分类树(展开数据源) + 右按数据源组织的问答对列表(逐对校验/上下文/状态) ---- */
S.cstMain = { running:false, cat:'', catHidden:false, expand:true, doc:'' };
DB.srsLog = [];
DB.qaCst = {};   /* qaIndex → {st:'checking'|'pass'|'fail', n} */
function cstMainOpen(c){ S.cstMain.cat = c; render(); }
function toggleCstMainCat(){ S.cstMain.catHidden = !S.cstMain.catHidden; render(); }
function cstMainToggle(){ S.cstMain.expand = !S.cstMain.expand; render(); }
function cstMainOpenDoc(num){ S.cstMain.doc = num; render(); }
function qaDoc(p){ /* qa数据源前缀匹配doc_num */ const n = SRS_DEMO.datasets.find(d => p.doc.indexOf(d.name.slice(0, 6)) === 0 || d.name.indexOf(p.doc.slice(0, 6)) === 0); return n ? n.num : '02'; }
function qaList(scope){ return SRS_DEMO.qa_pairs.map((p, i) => Object.assign({ idx: i, num: qaDoc(p) }, p))
  .filter(q => scope === 'all' || q.num === scope); }
function viewCstMain(){
  const st = S.cstMain;
  const cats = topCats();
  if (!cats.some(c => c.id === st.cat)) st.cat = cats.length ? cats[0].id : '';
  const isSrs = isSrsCatId(st.cat);

  const right = isSrs ? cstSrsMainPanel() : cstOrigPanel(st.cat);

  /* 左树: 数据分类 → 软件需求规格展开16份数据源(每份显示问答对数) */
  const qaCount = {}; SRS_DEMO.qa_pairs.forEach(p => { const n = qaDoc(p); qaCount[n] = (qaCount[n] || 0) + 1; });
  const srsKids = (st.expand && isSrs) ? SRS_DEMO.datasets.map(d =>
    '<div class="tree-i tree-lvl2' + (st.doc === d.num ? ' on' : '') + '" onclick="cstMainOpenDoc(\\'' + d.num + '\\')" title="' + esc(d.name) + '">'
    + '<span class="ell">📄 ' + esc(d.name.slice(0, 11)) + '</span>'
    + '<span class="n">' + (qaCount[d.num] || 0) + '</span></div>').join('') : '';
  const left = st.catHidden ? ''
    : '<div style="width:230px;flex:0 0 230px"><div class="card" style="height:100%;display:flex;flex-direction:column">'
      + '<div class="card-hd" style="display:flex;justify-content:space-between;align-items:center"><h3>数据分类</h3>'
        + '<span class="lnk" onclick="toggleCstMainCat()" title="折叠">«</span></div>'
      + '<div class="card-bd" style="padding:8px;overflow-y:auto;flex:1">'
      + cats.map(c => {
          const isS = isSrsCatId(c.id);
          return '<div class="tree-i' + (st.cat === c.id && !isS ? ' on' : '') + '" onclick="cstMainOpen(\\'' + c.id + '\\')">'
          + '<span class="ell">📁 ' + esc(c.n) + '</span>'
          + (isS ? '<span class="tree-toggle" onclick="event.stopPropagation();cstMainToggle()">' + (st.expand ? '−' : '+') + '</span>'
                 : '<span class="n">' + DB.datasets.filter(d => effCat(d.cat) === c.id).length + '</span>') + '</div>'
          + (isS ? srsKids : '');
        }).join('')
      + '</div></div></div>';

  return '<div style="display:flex;gap:16px;align-items:stretch;height:calc(100vh - 120px)">'
    + left
    + '<div style="flex:1;min-width:0;display:flex;flex-direction:column">'
    + (st.catHidden ? '<div style="margin-bottom:10px"><span class="lnk" style="color:var(--primary);cursor:pointer" onclick="toggleCstMainCat()">» 展开数据分类</span></div>' : '')
    + right + '</div></div>';
}

/* SRS右侧: 顶部仅[开始校验] + 问答对列表(可勾选, 逐对: 查看特征提取与上下文关联 | 进行不一致性校验) */
S.cstMain.sel = {};
function qaSel(idx, on){ if (on) S.cstMain.sel[idx] = 1; else delete S.cstMain.sel[idx]; }
function qaSelAll(on){ qaList(S.cstMain.doc || 'all').forEach(q => { if (on) S.cstMain.sel[q.idx] = 1; else delete S.cstMain.sel[q.idx]; }); render(); }
function cstSrsMainPanel(){
  const st = S.cstMain;
  const scope = st.doc || 'all';
  const list = qaList(scope);
  const scopeName2 = scope === 'all' ? '全部数据源（16份）'
    : ((SRS_DEMO.datasets.find(d => d.num === scope) || { name: scope }).name.slice(0, 16));
  let nChecked = 0, nFail = 0, nFind = 0;
  list.forEach(q => { const c = DB.qaCst[q.idx];
    if (c && c.st !== 'checking'){ nChecked++; nFind += c.n; if (c.st === 'fail') nFail++; } });
  const nSel = list.filter(q => S.cstMain.sel[q.idx]).length;

  const rows = list.map((q, i) => {
    const c = DB.qaCst[q.idx];
    const cst = !c ? '<span class="tag">未校验</span>'
      : (c.st === 'checking' ? '<span class="tag info">校验中</span>'
        : (c.st === 'fail' ? '<span class="tag err">发现问题</span>' : '<span class="tag ok">通过</span>'));
    return '<tr style="cursor:pointer" onclick="mQaCheck(\\'' + q.idx + '\\')"><td style="text-align:center"><input type="checkbox"' + (S.cstMain.sel[q.idx] ? ' checked' : '')
      + ' onclick="event.stopPropagation()" onchange="qaSel(\\\'' + q.idx + '\\\', this.checked)"></td>'
      + '<td>' + (i+1) + '</td>'
      + '<td class="ell small" style="max-width:260px" title="' + esc(q.q) + '">' + esc(q.q) + '</td>'
      + '<td class="ell small" style="max-width:200px" title="' + esc(q.a) + '">' + esc(q.a) + '</td>'
      + '<td class="small nowrap"><code style="font-size:10px">' + q.num + '</code> ' + esc(q.doc.slice(0, 8)) + '</td>'
      + '<td>' + (c && c.st !== 'checking' ? c.n + ' 条' : '<span class="muted">—</span>') + '</td>'
      + '<td>' + cst + '</td></tr>';
  }).join('');

  return '<div class="card" style="height:100%;display:flex;flex-direction:column">'
    + '<div class="card-hd"><h3>校验总览 · ' + esc(scopeName2) + '（' + list.length + ' 条问答对' + (nSel ? '，已选 ' + nSel + ' 条' : '') + '）</h3>'
      + '<div class="btn-grp" style="margin-left:auto">'
      + '<button class="btn" onclick="mTotalReport()">总报告</button>'
      + '<button class="btn pri" onclick="cstStartCheck()"' + (S.cstMain.running ? ' disabled' : '') + '>'
      + (S.cstMain.running ? '校验中…' : '开始校验') + '</button></div></div>'
    + '<div class="card-bd" style="flex:1;overflow:auto">'
    + '<div class="stats" style="margin-bottom:12px">'
      + '<div class="stat b"><div class="k">问答对</div><div class="v">' + list.length + '</div></div>'
      + '<div class="stat g"><div class="k">已校验</div><div class="v">' + nChecked + '</div></div>'
      + '<div class="stat r"><div class="k">发现问题</div><div class="v">' + nFail + '</div></div>'
      + '<div class="stat o"><div class="k">发现总数</div><div class="v">' + nFind + '</div></div></div>'
    + '<div class="tip">左侧选择数据源（一个数据源对应一组问答对）；勾选条目后「开始校验」仅对选中项执行，未勾选则校验当前全部；右上「总报告」查看分门别类（语法·语义·逻辑）统计。</div>'
    + '<div class="tbwrap"><table class="tb"><thead><tr>'
    + '<th style="width:36px"><input type="checkbox" onchange="qaSelAll(this.checked)" title="全选/清空"></th>'
    + '<th style="width:40px">序号</th><th>问题</th><th>答案</th>'
    + '<th style="width:130px">数据源</th>'
    + '<th style="width:66px">发现</th><th style="width:86px">状态</th></tr></thead><tbody>'
    + (rows || '<tr><td colspan="7"><div class="empty">该数据源暂无问答对</div></td></tr>')
    + '</tbody></table></div></div></div>';
}

/* 开始校验: 勾选了条目则仅校验选中项, 否则校验当前范围全部 */
function cstStartCheck(){
  if (S.cstMain.running) return;
  const scope = S.cstMain.doc || 'all';
  const all = qaList(scope);
  const list = all.filter(q => S.cstMain.sel[q.idx]);
  const useSel = list.length > 0;
  const target = useSel ? list : all;
  if (!target.length) return toast('当前范围无问答对', 'err');
  S.cstMain.running = true;
  target.forEach(q => { DB.qaCst[q.idx] = { st: 'checking', n: 0 }; });
  render();
  toast('已对' + (useSel ? '选中的 ' + target.length + ' 条' : '「' + (scope === 'all' ? '全部数据源' : 'doc' + scope) + '」' + target.length + ' 条') + '问答对发起52项校验…', 'ok');
  const nums = scope === 'all' ? SRS_DEMO.datasets.map(d => d.num) : [scope];
  nums.forEach(n => { if (!DB.srsChecks[n]) DB.srsChecks[n] = simCheck(n); });
  setTimeout(() => {
    let nFind = 0, nFail = 0;
    target.forEach(q => {
      const c = DB.srsChecks[q.num];
      const f = c ? c.categories.reduce((a, b) => a + b.findings, 0) : 0;
      const fail = c && c.summary.fail > 0;
      const per = Math.max(1, Math.round(f / Math.max(all.filter(x => x.num === q.num).length, 1)));
      DB.qaCst[q.idx] = { st: fail ? 'fail' : 'pass', n: per };
      nFind += per; if (fail) nFail++;
    });
    S.cstMain.running = false;
    render();
    toast('校验完成：' + nFail + ' 条问答对发现确证问题，共 ' + nFind + ' 条发现', nFail ? 'err' : 'ok');
  }, 2000);
}

/* 召回条交互: 参数配置/图例过滤/实时引擎查询(恢复块) */
S.mmCfg = { k: 2, topK: 6, minW: 0.3, hidden: {}, q: '' };
function mmToggleMod(mod){ mmSaveScroll(); S.mmCfg.hidden[mod] = !S.mmCfg.hidden[mod]; render(); }
function mmApplyCfg(){ mmSaveScroll(); render(); }
async function mmQuery(){
  const inp = document.getElementById('mmQ');
  const q = inp ? inp.value.trim() : '';
  S.mmCfg.q = q;
  if (!q) return toast('请输入查询内容', 'err');
  S.cstGraph.queried = true;
  S.cstGraph.node = '';
  render();
  toast('正在召回「' + q.slice(0, 16) + '」…', 'ok');
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 2500);
    const r = await fetch('http://127.0.0.1:8300/api/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
        'Authorization': 'Basic ' + btoa('demo:srs-2026-graph') },
      body: JSON.stringify({ question: q, k: S.mmCfg.k, top_k: S.mmCfg.topK, min_w: S.mmCfg.minW }),
      signal: ctrl.signal });
    const j = await r.json();
    if (j && j.ok){ applyLiveGraph(j); return; }
  } catch (e) { /* 引擎未启动, 离线回退 */ }
  mmOfflineQuery(q);
}
function applyLiveGraph(j){
  const slim = n => ({ id: n.id, type: n.type, label: (n.label || '').slice(0, 24),
    section: n.section || '',
    preview: ((n.payload && n.payload.text_preview) || '').slice(0, 40),
    caption: ((n.payload && n.payload.caption) || '').slice(0, 20),
    headers: (n.payload && n.payload.headers || []).slice(0, 4),
    img_type: (n.payload && n.payload.img_type) || '',
    seq: (n.payload && n.payload.seq_type) === 'anchor_chain' ? ((n.payload && n.payload.n_steps || '?') + '步') : '异常流',
    rule: (n.id || '').split(':')[1] || '' });
  const groups = {};
  let nContent = 0;
  Object.keys(j.groups || {}).forEach(m => {
    groups[m] = (j.groups[m] || []).slice(0, 12).map(n => Object.assign(slim(n), {
      score: Math.round((n.score || 0) * 100) / 100,
      via: (n.via_label || '').slice(0, 10) }));
    nContent += groups[m].length;
  });
  const g2 = { question: j.question, doc: j.doc,
    center: Object.assign(slim(j.center), {
      alias: ((j.center.payload && j.center.payload.aliases) || [''])[0],
      score: j.center.score || 1 }),
    related: (j.related_entities || []).slice(0, 6).map(x => ({
      name: (x.aliases || [x.id_str || ''])[0], id_str: x.id_str || '',
      rel: x.rel || '', score: Math.round((x.score || 0) * 100) / 100 })),
    groups: groups,
    stats: { n_related: (j.related_entities || []).length, n_content: nContent,
      by_modality: j.stats ? (j.stats.by_modality || {}) : {} } };
  SRS_DEMO.graphs[j.doc] = g2;
  S.cstGraph.doc = j.doc;
  render();
  toast('实时引擎召回完成：' + g2.center.alias + '，相关' + g2.related.length + '，召回' + nContent + '条', 'ok');
}
function mmOfflineQuery(q){
  const hit = Object.keys(SRS_DEMO.graphs).find(num => {
    const g = SRS_DEMO.graphs[num];
    const al = (g.center.alias || g.center.label || '');
    return al && (q.indexOf(al) >= 0 || al.indexOf(q) >= 0);
  });
  if (hit && hit !== S.cstGraph.doc){
    S.cstGraph.doc = hit; render();
    toast('离线匹配：切换到 doc' + hit + ' 的图谱（启动实时引擎可获得任意查询的完整召回）', 'ok');
  } else if (hit){
    toast('已展示该实体的图谱', 'ok');
  } else {
    toast('离线演示未匹配到该实体；启动实时引擎(python server/main.py)后可任意查询', 'err');
  }
}

/* 问答对的上下文校验: 跳图谱页并对该问题实时召回 */
function mmQueryFor(idx){
  const q = SRS_DEMO.qa_pairs[idx];
  if (!q) return;
  S.mmCfg.q = q.q;
  S.cstGraph.doc = qaDoc(q);
  S.menu = 'consist'; S.sub = 'graph'; S.modal = null; render();
  setTimeout(() => { if (document.getElementById('mmQ')) mmQuery(); }, 250);
}

/* 问答对的不一致性校验: 状态 + 分门别类(语法/语义/逻辑)发现 */
function mQaCheck(idx){
  const q = Object.assign({ idx: idx, num: qaDoc(SRS_DEMO.qa_pairs[idx]) }, SRS_DEMO.qa_pairs[idx]);
  if (!q.q) return;
  const c = DB.qaCst[idx];
  if (!DB.srsChecks[q.num]) DB.srsChecks[q.num] = simCheck(q.num);
  const dc = DB.srsChecks[q.num];
  const stat = !c ? '<span class="tag">未校验</span>'
    : (c.st === 'checking' ? '<span class="tag info">校验中</span>'
      : (c.st === 'fail' ? '<span class="tag err">发现问题</span>' : '<span class="tag ok">通过</span>'));
  /* 三分类统计(语法/语义/逻辑) */
  const grp = cst3Stats(dc);
  const grpRows = grp.map(g => '<tr><td>' + g.name + '</td>'
    + '<td>' + g.total + '</td><td style="color:var(--green)">' + g.pass + '</td>'
    + '<td style="color:var(--orange)">' + g.warn + '</td>'
    + '<td style="color:var(--red)">' + g.fail + '</td>'
    + '<td>' + g.findings + '</td></tr>').join('');
  openModal(mask('<div class="modal w860"><div class="m-hd"><h3>不一致性校验 · 问答对 #' + (idx + 1) + '</h3>'
    + '<span class="m-x" onclick="closeModal()">✕</span></div>'
    + '<div class="m-bd" style="background:#eef1f6">'
    + '<div class="stats" style="margin-bottom:12px">'
      + '<div class="stat b"><div class="k">校验状态</div><div class="v" style="font-size:14px">' + stat + '</div></div>'
      + '<div class="stat g"><div class="k">配对数据源</div><div class="v">' + q.num + '</div></div>'
      + '<div class="stat o"><div class="k">发现</div><div class="v">' + (c && c.st !== 'checking' ? c.n + ' 条' : '—') + '</div></div></div>'
    + '<div style="background:#fff;border-radius:8px;padding:14px">'
    + '<div style="font-size:13px;font-weight:650;margin-bottom:6px">问题：' + esc(q.q) + '</div>'
    + '<div style="font-size:12px;color:var(--txt2);margin-bottom:12px">答案：' + esc((q.a || '').slice(0, 90)) + '</div>'
    + '<div style="font-size:12.5px;font-weight:650;margin:8px 0 6px">关联数据源校验结果（语法 · 语义 · 逻辑）</div>'
    + '<table class="tb"><thead><tr><th>分类</th><th style="width:70px">项数</th>'
    + '<th style="width:64px">通过</th><th style="width:64px">可疑</th>'
    + '<th style="width:64px">确证</th><th style="width:70px">发现数</th></tr></thead><tbody>'
    + grpRows + '</tbody></table>'
    + '<div style="margin-top:12px;text-align:right">'
    + '<span class="lnk" onclick="closeModal();mTotalReport()">查看总报告（分门别类统计） →</span></div>'
    + '</div></div></div>'));
}

/* 三分类统计: 语法/语义/逻辑 */
function cst3Stats(dc){
  if (!dc) return [];
  const items = dc.items || [];
  const out = [];
  Object.keys(CST3).forEach(top => {
    const ids = [];
    CST3[top].forEach(sub => { ids.push.apply(ids, sub[1]); });
    const its = items.filter(it => ids.indexOf(it.id) >= 0);
    out.push({
      name: top, total: its.length,
      pass: its.filter(i => i.status === 'pass').length,
      warn: its.filter(i => i.status === 'warn').length,
      fail: its.filter(i => i.status === 'fail').length,
      findings: its.reduce((a, b) => a + (b.n || 0), 0) });
  });
  return out;
}

/* 总报告: 分门别类统计(语法/语义/逻辑, 含细分原因与发现) — 融合原独立页面 */
function mTotalReport(){
  const scope = S.cstMain.doc || 'all';
  const nums = scope === 'all' ? SRS_DEMO.datasets.map(d => d.num) : [scope];
  nums.forEach(n => { if (!DB.srsChecks[n]) DB.srsChecks[n] = simCheck(n); });
  /* 聚合当前范围的校验结果 */
  const agg = { pass: 0, warn: 0, fail: 0, findings: 0 };
  const itemsAll = [];
  nums.forEach(n => {
    const dc = DB.srsChecks[n];
    agg.pass += dc.summary.pass; agg.warn += dc.summary.warn;
    agg.fail += dc.summary.fail; agg.findings += dc.categories.reduce((a, b) => a + b.findings, 0);
    dc.items.forEach(it => itemsAll.push(it));
  });
  const scopeName3 = scope === 'all' ? '全部数据源（16份）'
    : ((SRS_DEMO.datasets.find(d => d.num === scope) || { name: scope }).name.slice(0, 16));
  const byId = {};
  itemsAll.forEach(it => { byId[it.id] = it; });
  const catCards = Object.keys(CST3).map(top => {
    const color = CST3_META[top];
    const subs = CST3[top].map(sub => {
      const [subName, ids] = sub;
      const items = ids.map(id => byId[id]).filter(Boolean);
      if (!items.length) return '';
      const nFind = items.reduce((a, b) => a + (b.n || 0), 0);
      const nFail = items.filter(i => i.status === 'fail').length;
      const nWarn = items.filter(i => i.status === 'warn').length;
      const rows = items.map((it, i) => '<tr><td>' + (i+1) + '</td>'
        + '<td><code style="font-size:10.5px">' + it.id + '</code></td>'
        + '<td>' + esc(it.name) + '</td>'
        + (it.n ? '<td><b style="color:' + (it.status === 'fail' ? 'var(--red)' : 'var(--orange)') + '">' + it.n + '</b></td>'
                : '<td class="muted">0</td>') + '</tr>').join('');
      return '<div style="margin-bottom:10px">'
        + '<div style="font-size:12px;font-weight:650;color:' + color + ';margin:6px 0 4px;display:flex;align-items:center;gap:6px">'
        + '<span style="width:7px;height:7px;border-radius:2px;background:' + color + '"></span>'
        + subName + ' <span class="tag" style="font-size:10px">' + items.length + '项'
        + (nFind ? ' · ' + nFind + '条发现' : '') + (nFail ? ' · ' + nFail + '确证' : '') + (nWarn ? ' · ' + nWarn + '可疑' : '')
        + '</span></div>'
        + '<div class="tbwrap"><table class="tb" style="font-size:11.5px"><thead><tr>'
        + '<th style="width:34px">序号</th><th style="width:80px">校验项</th><th>名称</th>'
        + '<th style="width:64px">发现</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>';
    }).join('');
    return '<div class="card"><div class="card-hd"><h3 style="color:' + color + '">' + top + '</h3></div>'
      + '<div class="card-bd">' + (subs || '<div class="small muted">无条目</div>') + '</div></div>';
  }).join('');
  const totalHtml = '<div class="stats" style="margin-bottom:14px">'
    + '<div class="stat b"><div class="k">校验项</div><div class="v">52</div></div>'
    + '<div class="stat g"><div class="k">通过</div><div class="v">' + agg.pass + '</div></div>'
    + '<div class="stat o"><div class="k">可疑</div><div class="v">' + agg.warn + '</div></div>'
    + '<div class="stat r"><div class="k">确证问题</div><div class="v">' + agg.fail + '</div></div>'
    + '<div class="stat y"><div class="k">发现总数</div><div class="v">' + agg.findings + '</div></div></div>';
  openModal(mask('<div class="modal w1000" style="max-width:96vw"><div class="m-hd">'
    + '<h3>一致性校验总报告 · ' + esc(scopeName3) + '</h3>'
    + '<span class="m-x" onclick="closeModal()">✕</span></div>'
    + '<div class="m-bd" style="background:#eef1f6;max-height:78vh;overflow-y:auto">'
    + totalHtml + catCards
    + '</div></div>'));
}

/* 其他分类右侧: 原浅层校验面板 */
function cstOrigPanel(catId){
  const list = DB.cstLog[catId] || [];
  return '<div class="card" style="height:100%;display:flex;flex-direction:column">'
    + '<div class="card-hd"><h3>一致性校验</h3>'
      + '<button class="btn pri" style="margin-left:auto" onclick="catCstRun(\\'' + catId + '\\')">校验</button></div>'
    + '<div class="card-bd np"><div class="tbwrap"><table class="tb"><thead><tr>'
    + '<th style="width:46px">序号</th><th style="width:110px">数据集数量</th>'
    + '<th style="width:110px">异常样本数</th><th style="width:110px">正常样本数</th>'
    + '<th style="width:110px">校验状态</th><th style="width:160px">创建时间</th>'
    + '<th style="width:120px">操作</th></tr></thead><tbody>'
    + (list.length ? list.map((r, i) => '<tr><td>' + (i+1) + '</td>'
      + '<td>' + r.total + '</td>'
      + '<td style="color:var(--red)">' + r.bad + '</td>'
      + '<td style="color:var(--green)"><b>' + r.ok + '</b></td>'
      + '<td>' + cstTag(r.st) + '</td>'
      + '<td class="small nowrap">' + r.time + '</td>'
      + '<td class="ops nowrap"><span class="lnk" onclick="mCstDetail(\\'' + catId + '\\')">查看校验报告</span></td></tr>').join('')
      : '<tr><td colspan="7"><div class="empty"><span class="big">✅</span>该分类下暂无校验记录</div></td></tr>')
    + '</tbody></table></div></div></div>';
}

/* 问答对 ↔ 数据源 配对关系 */
function mPairing(){
  const pairs = SRS_DEMO.qa_pairs || [];
  const rows = pairs.map((p, i) => '<tr><td>' + (i+1) + '</td>'
    + '<td class="small ell" style="max-width:260px" title="' + esc(p.q) + '">' + esc(p.q) + '</td>'
    + '<td class="small">' + esc(p.doc) + '</td>'
    + '<td class="small ell" style="max-width:170px" title="' + esc(p.ev) + '">' + esc(p.ev) + '</td>'
    + '<td class="small">' + esc(p.typ || '') + '</td></tr>').join('');
  openModal(mask('<div class="modal w1000"><div class="m-hd"><h3>问答对 · 数据源配对关系</h3>'
    + '<span class="m-x" onclick="closeModal()">✕</span></div>'
    + '<div class="m-bd" style="background:#eef1f6">'
    + '<div class="stats" style="margin-bottom:12px">'
      + '<div class="stat b"><div class="k">问答对</div><div class="v">' + pairs.length + '</div></div>'
      + '<div class="stat g"><div class="k">配对数据源</div><div class="v">16</div></div>'
      + '<div class="stat o"><div class="k">证据可追溯</div><div class="v">100%</div></div></div>'
    + '<div style="background:#fff;border-radius:8px;padding:12px">'
    + '<table class="tb"><thead><tr><th style="width:40px">序号</th><th>问题</th>'
    + '<th style="width:150px">数据源文档</th><th style="width:180px">证据</th>'
    + '<th style="width:130px">类型</th></tr></thead><tbody>' + rows + '</tbody></table></div>'
    + '<div class="small" style="margin-top:10px;color:var(--txt3)">配对机制：问答对经问题生成+答案生成后由数据集管理打包，doc_ref 指向源SRS文档章节；校验时按配对关系定位证据。</div>'
    + '</div></div>'));
}

/* 批次报告: 16数据集列表(逐份可进52项明细) */
function mSrsBatchReport(){
  const ds = SRS_DEMO.datasets;
  let nFind = 0, nFail = 0, nPass = 0;
  ds.forEach(d => { const c = DB.srsChecks[d.num];
    if (c){ nFind += c.categories.reduce((a, b) => a + b.findings, 0); nFail += c.summary.fail; nPass += c.summary.pass; } });
  const rows = ds.map((d, i) => {
    const c = DB.srsChecks[d.num];
    const st = !c ? '<span class="tag">未校验</span>'
      : (c.summary.fail ? '<span class="tag err">' + c.summary.fail + '确证</span>'
        : (c.summary.warn ? '<span class="tag wait">' + c.summary.warn + '可疑</span>' : '<span class="tag ok">通过</span>'));
    return '<tr><td>' + (i+1) + '</td><td><code style="font-size:11px">' + d.num + '</code></td>'
      + '<td class="ell" style="max-width:220px">' + esc(d.name) + '</td>'
      + '<td class="small">' + d.nodes + '</td><td>' + st + '</td>'
      + '<td class="small">' + (c ? c.categories.reduce((a, b) => a + b.findings, 0) : 0) + '</td>'
      + '<td class="ops nowrap"><span class="lnk" onclick="mSrsReport(\\'' + d.num + '\\')">52项明细</span></td></tr>';
  }).join('');
  openModal(mask('<div class="modal w900"><div class="m-hd"><h3>一致性校验报告 · 软件需求规格数据（16份数据集）</h3>'
    + '<span class="m-x" onclick="closeModal()">✕</span></div>'
    + '<div class="m-bd" style="background:#eef1f6">'
    + '<div class="stats" style="margin-bottom:12px">'
      + '<div class="stat b"><div class="k">数据集</div><div class="v">16</div></div>'
      + '<div class="stat g"><div class="k">通过项合计</div><div class="v">' + nPass + '</div></div>'
      + '<div class="stat r"><div class="k">确证问题</div><div class="v">' + nFail + '</div></div>'
      + '<div class="stat o"><div class="k">发现总数</div><div class="v">' + nFind + '</div></div></div>'
    + '<div style="background:#fff;border-radius:8px;padding:12px;max-height:56vh;overflow-y:auto">'
    + '<table class="tb"><thead><tr><th style="width:42px">序号</th><th style="width:52px">编号</th>'
    + '<th>数据集名称</th><th style="width:90px">图谱规模</th><th style="width:110px">校验结果</th>'
    + '<th style="width:80px">发现数</th><th style="width:90px">操作</th></tr></thead><tbody>'
    + rows + '</tbody></table></div>'
    + '</div></div>'));
}

/* 执行单数据集校验 */
function cstSrsRun(num){
  if (!DB.srsChecks[num]) DB.srsChecks[num] = simCheck(num);
  toast('数据集 ' + num + ' 一致性校验完成，' + (DB.srsChecks[num].summary.fail ? '发现确证问题 ' + DB.srsChecks[num].summary.fail + ' 项' : '未发现确证问题'), 'ok');
  render();
  mSrsReport(num);
}
function cstSrsRunAll(){
  SRS_DEMO.datasets.forEach(d => { if (!DB.srsChecks[d.num]) DB.srsChecks[d.num] = simCheck(d.num); });
  render(); toast('全部数据集校验完成', 'ok');
}
/* 无真实结果的数据集: 基于01/02口径生成确定性变体 */
function simCheck(num){
  const base = SRS_DEMO.checks[num <= '08' ? '01' : '02'];
  const seed = parseInt(num, 10) || 1;
  const items = base.items.map((it, i) => {
    let n = it.n;
    if (n > 0){ n = Math.max(1, Math.round(n * (0.5 + ((seed * 7 + i * 3) % 10) / 12))); }
    const status = it.mode === 'llm' ? 'llm' : (n === 0 ? 'pass' : (it.status === 'fail' ? 'fail' : 'warn'));
    return Object.assign({}, it, { n: n, status: status });
  });
  const summary = { total: 52, pass: 0, warn: 0, fail: 0, llm: 0 };
  items.forEach(it => summary[it.status]++);
  const categories = CST_CATS.map(c => {
    const ci = items.filter(i2 => i2.category === c);
    return { name: c, total: ci.length, pass: ci.filter(i2 => i2.status === 'pass').length,
      warn: ci.filter(i2 => i2.status === 'warn').length, fail: ci.filter(i2 => i2.status === 'fail').length,
      llm: ci.filter(i2 => i2.status === 'llm').length, findings: ci.reduce((a, b) => a + b.n, 0) };
  });
  return { ran_at: '2026-08-30T18:00:00', summary: summary, categories: categories, items: items };
}

/* ---- 校验报告modal: 汇总 + 分类 + 52项明细(证据展开) ---- */
function mSrsReport(num){
  const c = DB.srsChecks[num];
  if (!c) return toast('该数据集尚未校验', 'err');
  const d = SRS_DEMO.datasets.find(x => x.num === num) || { name: num };
  const s = c.summary;
  const catRows = c.categories.map((ct, i) => '<tr><td>' + (i+1) + '</td><td>' + ct.name + '</td>'
    + '<td>' + ct.total + '</td><td style="color:var(--green)">' + ct.pass + '</td>'
    + '<td style="color:var(--orange)">' + ct.warn + '</td>'
    + '<td style="color:var(--red)">' + ct.fail + '</td>'

    + '<td>' + ct.findings + '</td></tr>').join('');
  const itemRows = c.items.map((it, i) => {
    const stTag = it.status === 'pass' ? '<span class="tag ok">通过</span>'
      : it.status === 'warn' ? '<span class="tag wait">可疑</span>'
      : it.status === 'fail' ? '<span class="tag err">确证问题</span>'
      : '<span class="tag">待核</span>';
    const modeTag = it.mode === 'llm' ? '<span class="tag" style="background:var(--purple-bg);color:var(--purple);font-size:10px">LLM</span>' : '<span class="tag" style="font-size:10px">auto</span>';
    const fd = (it.findings || []).map((f, j) => '<div style="padding:3px 0;border-top:' + (j ? '1px dashed var(--line2)' : 'none') + '">'
      + '<div style="font-size:12px">' + esc(f.desc) + (f.section ? ' <span class="tag" style="font-size:9.5px">' + esc(String(f.section).slice(0, 14)) + '</span>' : '') + '</div>'
      + '<div style="font-size:11px;color:var(--txt3);margin-left:14px">' + esc(f.evidence) + '</div></div>').join('');
    return '<tr><td>' + (i+1) + '</td><td><code style="font-size:10.5px">' + it.id + '</code></td>'
      + '<td>' + esc(it.name) + '</td><td class="small">' + esc(it.modality || '') + '</td>'
      + '<td>' + modeTag + '</td><td>' + stTag + '</td>'
      + '<td>' + (it.n ? '<b style="color:' + (it.status === 'fail' ? 'var(--red)' : 'var(--orange)') + '">' + it.n + '</b>' : '<span class="muted">0</span>') + '</td></tr>'
      + (fd ? '<tr class="cst-fd"><td colspan="7" style="background:var(--bg);padding:8px 14px">' + fd + '</td></tr>' : '');
  }).join('');

  const html = '<div class="doc"><h1>SRS数据集一致性校验报告</h1>'
    + '<div class="meta">数据集：' + esc(d.name) + '（' + num + '）　|　校验时间：' + c.ran_at.replace('T', ' ') + '</div>'
    + '<h2>一、校验概况</h2><table><tbody>'
    + '<tr><th style="width:140px">校验项总数</th><td>' + s.total + '</td><th style="width:140px">通过</th><td style="color:var(--green)">' + s.pass + '</td></tr>'
    + '<tr><th>确证问题</th><td style="color:var(--red)">' + s.fail + '</td><th>可疑项</th><td style="color:var(--orange)">' + s.warn + '</td></tr>'
    + '<tr><th>校验项总数</th><td>' + s.total + '</td><th>校验结论</th><td>' + (s.fail ? '发现确证问题 ' + s.fail + ' 项，需修正后重新校验' : '确定性项全部通过，可进入质量评估') + '</td></tr></tbody></table>'
    + '<h2>二、分类统计</h2><table><thead><tr><th>序号</th><th>校验层</th><th>项数</th><th>通过</th><th>可疑</th><th>确证</th><th>发现数</th></tr></thead><tbody>' + catRows + '</tbody></table>'
    + '<h2>三、52项明细（含证据）</h2><table><thead><tr><th style="width:40px">序号</th><th style="width:80px">校验项</th><th>名称</th><th style="width:130px">模态</th><th style="width:56px">方式</th><th style="width:86px">状态</th><th style="width:56px">发现</th></tr></thead><tbody>' + itemRows + '</tbody></table>'
    + '<h2>四、处理说明</h2><ol>'
    + '<li>确证问题（fail）类发现关联的样本标记剔除，不进入质量评估。</li>'
    + '<li>可疑（warn）类发现需人工复核，复核后规范保留或剔除。</li>'
    + '<li>其余项待补充核验，不阻塞当前判定。</li></ol>'
    + '<p style="text-align:right;margin-top:20px">微调数据集构建平台 · 一致性校验模块　' + today() + '</p></div>';
  window.__rpt = html;
  openModal(mask('<div class="modal w1000"><div class="m-hd"><h3>一致性校验报告 · ' + esc(d.name) + '</h3>'
    + '<span class="m-x" onclick="closeModal()">✕</span></div>'
    + '<div class="m-bd" style="background:#eef1f6">'
    + '<div class="stats" style="margin-bottom:14px">'
      + '<div class="stat g"><div class="k">通过</div><div class="v">' + s.pass + '</div></div>'
      + '<div class="stat o"><div class="k">可疑</div><div class="v">' + s.warn + '</div></div>'
      + '<div class="stat r"><div class="k">确证问题</div><div class="v">' + s.fail + '</div></div>'
      + '</div>'
    + '<div style="background:#fff;border-radius:8px;padding:14px;max-height:60vh;overflow-y:auto">' + html + '</div>'
    + '<div style="margin-top:12px;text-align:right"><button class="btn" onclick="exportRpt()">导出报告</button></div>'
    + '</div></div>'));
}

/* ---- 上下文关联图谱: 左数据分类树(软件需求规格可展开16数据集) + 右图谱 ---- */
const MM_MODS = [['TXT','文本章节','#64748b'],['TBL','表格','#0891b2'],['IMG','图片','#059669'],['SEQ','时序流程','#d97706'],['KNW','专家知识','#7c3aed']];
S.cstGraph = { doc:'', cat:'', expand:true, node:'', queried:false };
function cstGraphOpenDoc(num){ S.cstGraph.doc = num; S.cstGraph.queried = false; S.cstGraph.node = ''; render(); }
function cstGraphToggle(){ S.cstGraph.expand = !S.cstGraph.expand; render(); }
function curGraph(){ return SRS_DEMO.graphs[S.cstGraph.doc] || null; }
function viewCstGraph(){
  const st = S.cstGraph;
  if (!st.doc) st.doc = '02';
  st.node = st.node || '';
  const g = st.queried ? curGraph() : null;
  /* 左侧: 数据分类树 + 数据集归属 */
  const cats = topCats();
  const srsKids = st.expand ? SRS_DEMO.datasets.map(d =>
    '<div class="tree-i tree-lvl2' + (st.doc === d.num ? ' on' : '') + '" onclick="cstGraphOpenDoc(\\'' + d.num + '\\')" title="' + esc(d.name) + '">'
    + '<span class="ell">📄 ' + esc(d.name.slice(0, 12)) + '</span>'
    + '<span class="n">' + d.nodes + '</span></div>').join('') : '';
  const left = '<div style="width:230px;flex:0 0 230px"><div class="card" style="height:100%;display:flex;flex-direction:column">'
    + '<div class="card-hd"><h3>数据分类</h3></div>'
    + '<div class="card-bd" style="padding:8px;overflow-y:auto;flex:1">'
    + cats.map(c => {
        const isSrs = catName(c.id).indexOf('软件需求规格') >= 0;
        return '<div class="tree-i" onclick="cstGraphToggle()" style="cursor:' + (isSrs ? 'pointer' : 'default') + '">'
          + '<span class="ell">📁 ' + esc(c.n) + '</span>'
          + (isSrs ? '<span class="tree-toggle">' + (st.expand ? '−' : '+') + '</span>'
                   : '<span class="n">—</span>') + '</div>'
          + (isSrs ? srsKids : '');
      }).join('')
    + '</div></div></div>';

  /* 中央: 召回条 + (未查询=空态 | 已查询=图谱) */
  const center = buildGraphCanvas(g);

  /* 右侧: 上=特征提取可视化信息, 下=节点数据·细粒度 */
  const ds = SRS_DEMO.datasets.find(d => d.num === st.doc) || SRS_DEMO.datasets[0];
  const mods = (ds && ds.mods) || {};
  const modBar = [['E','实体','#2563EB'],['TXT','文本章节','#64748b'],['TBL','表格','#0891b2'],
    ['IMG','图片','#059669'],['SEQ','时序','#d97706'],['KNW','知识','#7c3aed']].map(m => {
    const cnt = mods[m[0]] || 0;
    const maxv = Math.max(1, ...Object.values(mods));
    const pct = Math.round(cnt / maxv * 100);
    return '<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px">'
      + '<span class="small" style="width:44px;color:' + m[2] + ';font-weight:600">' + m[1] + '</span>'
      + '<span style="flex:1;height:7px;background:var(--line2);border-radius:4px;overflow:hidden">'
      + '<span style="display:block;height:100%;width:' + pct + '%;background:' + m[2] + ';border-radius:4px"></span></span>'
      + '<span class="small" style="width:34px;text-align:right;color:var(--txt2)">' + cnt + '</span></div>';
  }).join('');
  const featCard = '<div class="card" style="flex:0 0 auto">'
    + '<div class="card-hd"><h3>特征提取 · 图谱信息</h3></div>'
    + '<div class="card-bd" style="padding:12px 14px">'
    + '<div class="small" style="color:var(--txt3);margin-bottom:2px">当前数据源</div>'
    + '<div style="font-size:12.5px;font-weight:650;margin-bottom:8px">' + esc((ds ? ds.name : '').slice(0, 16)) + '（doc' + (ds ? ds.num : '') + '）</div>'
    + '<div style="display:flex;gap:10px;margin-bottom:10px">'
      + '<span class="small" style="background:var(--blue-bg);color:var(--primary);border-radius:6px;padding:3px 9px">' + (ds ? ds.nodes : 0) + ' 节点</span>'
      + '<span class="small" style="background:var(--blue-bg);color:var(--primary);border-radius:6px;padding:3px 9px">' + (ds ? ds.edges : 0) + ' 边</span>'
      + '<span class="small" style="background:var(--green-bg);color:var(--green);border-radius:6px;padding:3px 9px">' + (ds ? ds.items : 0) + ' 聚合条目</span></div>'
    + '<div class="small" style="color:var(--txt3);margin-bottom:5px;font-weight:600">节点类型分布</div>'
    + modBar
    + '<div class="small" style="color:var(--txt3);margin-top:9px;padding-top:8px;border-top:1px solid var(--line2);line-height:1.8">'
    + '全局：16 份源文档 · 5619 节点 · 23850 边<br>'
    + '锚点/结构图：373 图 · Mermaid 覆盖 89%<br>'
    + '聚合条目：978（四位置覆盖度评价）</div>'
    + '</div></div>';

  const sidebar = '<div style="width:312px;flex:0 0 312px;display:flex;flex-direction:column;gap:12px;height:100%;min-height:0">'
    + featCard
    + '<div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column">'
      + '<div class="card-hd"><h3 id="mmSbTitle">' + (st.node ? '节点数据 · 细粒度' : '节点详情') + '</h3>'
      + (st.node ? '<span class="lnk" onclick="mmCloseNode()">关闭</span>' : '') + '</div>'
      + '<div class="card-bd" id="mmSbBody" style="flex:1;overflow-y:auto;padding:14px">' + nodeSidebar() + '</div></div>'
    + '</div>';

  /* 滚动位置还原(参数/图例变更触发render后) */
  setTimeout(() => {
    const w = document.querySelector('.mmwrap');
    if (w && S.cstGraph.scroll){ w.scrollLeft = S.cstGraph.scroll.l; w.scrollTop = S.cstGraph.scroll.t; }
  }, 70);

  return '<div style="display:flex;gap:14px;align-items:stretch;height:calc(100vh - 120px)">'
    + left
    + '<div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:0">' + center + '</div>'
    + sidebar + '</div>';
}

function updateSbDom(){
  const el = document.getElementById('mmSbBody');
  const t = document.getElementById('mmSbTitle');
  if (el) el.innerHTML = nodeSidebar();
  if (t) t.textContent = S.cstGraph.node ? '节点数据 · 细粒度' : '节点详情';
}
/* 节点点击: 定向更新侧边栏 + 高亮(不全页render, 保留画布滚动) */
function mGraphNode(key, el){
  S.cstGraph.node = key;
  document.querySelectorAll('.mmnode').forEach(x => x.classList.remove('mm-on'));
  if (el) el.classList.add('mm-on');
  updateSbDom();
  const sb = document.getElementById('mmSbBody');
  if (sb) sb.scrollTop = 0;
}
function mmCloseNode(){
  S.cstGraph.node = '';
  document.querySelectorAll('.mmnode').forEach(x => x.classList.remove('mm-on'));
  updateSbDom();
}
function mmSaveScroll(){
  const w = document.querySelector('.mmwrap');
  if (w) S.cstGraph.scroll = { l: w.scrollLeft, t: w.scrollTop };
}

/* 右侧边栏: 节点细粒度数据 */
function nodeSidebar(){
  const st = S.cstGraph;
  const g = curGraph();
  if (!st.node || !g) return '<div class="empty" style="padding:30px 10px"><span class="big">👆</span><br>点击图谱节点<br>查看细粒度数据<div class="small" style="margin-top:8px;color:var(--txt3)">表格→行列数据 · 图片→Mermaid结构<br>文本→正文 · 时序→步骤链 · 知识→规则</div></div>';
  const key = st.node;
  if (key === 'center'){
    return '<div class="mmcenter" style="position:static;margin:0 0 14px;cursor:default;pointer-events:none">'
      + '<div style="font-size:15px;font-weight:700">' + esc(g.center.alias || g.center.label) + '</div>'
      + '<code style="font-size:11px;opacity:.85">' + esc(g.center.label) + '</code></div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">查询</th><td class="small">' + esc(g.question) + '</td></tr>'
      + '<tr><th>章节</th><td class="small">' + esc(g.center.section || '—') + '</td></tr>'
      + '<tr><th>召回分</th><td class="small">' + (g.center.score != null ? g.center.score : '—') + '</td></tr></tbody></table>'
      + '<div class="tip" style="margin-top:12px">实体ID即图谱锚点(E节点)；其四类位置覆盖构成聚合条目(chain_completeness)，是下方不一致性校验的检测对象。</div>';
  }
  if (key.indexOf('rel:') === 0){
    const id = key.slice(4);
    const r = g.related.find(x => x.id_str === id) || g.related[0];
    if (!r) return '<div class="empty">未找到该实体</div>';
    return '<div style="font-size:15px;font-weight:700;margin-bottom:10px">' + esc(r.name) + '</div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">实体ID</th><td class="small"><code>' + esc(r.id_str) + '</code></td></tr>'
      + '<tr><th>关联关系</th><td><span class="tag">' + esc(r.rel) + '</span></td></tr>'
      + '<tr><th>召回得分</th><td class="small">' + r.score + '</td></tr></tbody></table>'
      + '<div class="tip" style="margin-top:12px">召回路径：中心实体 —' + esc(r.rel) + '→ 该实体。相关实体经ID父子/同章节/同表等加权边激活。</div>';
  }
  const parts = key.split(':');
  const mod = parts[1]; const j = parseInt(parts[2], 10);
  const list = g.groups[mod] || [];
  const raw = list.filter(n => (n.score == null ? 1 : n.score) >= S.mmCfg.minW).slice(0, S.mmCfg.topK);
  const n = raw.find(x => list.indexOf(x) === j) || raw[j] || list[j];
  if (!n) return '<div class="empty">该节点已被当前过滤参数隐藏</div>';
  const meta = MM_MODS.find(m => m[0] === mod) || ['', '节点', '#999'];
  let body = '';
  if (mod === 'TXT'){
    body = '<div style="font-size:13px;font-weight:650;margin-bottom:8px">' + esc(n.label) + '</div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">章节</th><td class="small">' + esc(n.section) + '</td></tr>'
      + '<tr><th>正文字数</th><td class="small">' + (n.len || '—') + ' 字</td></tr></tbody></table>'
      + '<div style="font-size:11.5px;font-weight:650;color:var(--txt2);margin:10px 0 4px">正文内容</div>'
      + '<div class="small" style="background:var(--bg);border-radius:8px;padding:10px;line-height:1.9;max-height:200px;overflow-y:auto">' + esc(n.preview || '(无正文)') + '</div>';
  } else if (mod === 'TBL'){
    body = '<div style="font-size:13px;font-weight:650;margin-bottom:8px">' + esc(n.caption || n.label) + '</div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">章节</th><td class="small">' + esc(n.section) + '</td></tr>'
      + '<tr><th>行数</th><td class="small">' + (n.row_count || n.rows && n.rows.length || '—') + '</td></tr></tbody></table>'
      + '<div style="font-size:11.5px;font-weight:650;color:var(--txt2);margin:10px 0 4px">表格数据（表头+前3行）</div>'
      + '<div style="max-height:240px;overflow-y:auto"><table class="tb" style="font-size:10.5px"><tbody>'
      + (n.rows || []).map(r2 => '<tr>' + r2.map(c => '<td style="padding:3px 6px">' + esc(c) + '</td>').join('') + '</tr>').join('')
      + '</tbody></table></div>';
  } else if (mod === 'IMG'){
    body = '<div style="font-size:13px;font-weight:650;margin-bottom:8px">' + esc(n.caption || n.label) + '</div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">图型</th><td class="small">' + esc(n.img_type || '—') + '</td></tr>'
      + '<tr><th>章节</th><td class="small">' + esc(n.section) + '</td></tr>'
      + (n.mm_nodes ? '<tr><th>结构</th><td class="small">' + n.mm_nodes + '节点 / ' + n.mm_edges + '边</td></tr>' : '') + '</tbody></table>'
      + '<div style="font-size:11.5px;font-weight:650;color:var(--txt2);margin:10px 0 4px">Mermaid结构图（born-digital锚点导出）</div>'
      + (n.img ? '<img src="images/' + n.img + '" style="width:100%;border-radius:8px;border:1px solid var(--line);margin-bottom:10px" alt="' + esc(n.caption) + '">' : '')
    + '<div style="font-size:11.5px;font-weight:650;color:var(--txt2);margin:4px 0">Mermaid结构图（born-digital锚点导出）</div>'
    + (n.mermaid
        ? '<pre style="background:#f6f8fa;border-radius:8px;padding:10px;font-size:10.5px;line-height:1.6;max-height:220px;overflow-y:auto;white-space:pre-wrap">' + esc(n.mermaid) + '</pre>'
        : '<div class="small" style="color:var(--txt3)">该图无born-digital锚点（非Visio源）</div>');
  } else if (mod === 'SEQ'){
    body = '<div style="font-size:13px;font-weight:650;margin-bottom:8px">' + esc(n.seq || n.label) + '</div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">章节</th><td class="small">' + esc(n.section) + '</td></tr></tbody></table>'
      + '<div style="font-size:11.5px;font-weight:650;color:var(--txt2);margin:10px 0 4px">步骤链</div>'
      + '<ol style="padding-left:20px;font-size:12px;line-height:2">' + (n.steps || []).map(s => '<li>' + esc(s) + '</li>').join('') + '</ol>'
      + (n.dangling && n.dangling.length ? '<div class="tip warn">悬空引用: ' + esc(n.dangling.join(', ')) + '</div>' : '');
  } else if (mod === 'KNW'){
    body = '<div style="font-size:13px;font-weight:650;margin-bottom:8px">' + esc(n.rule || n.label) + '</div>'
      + '<table><tbody>'
      + '<tr><th style="width:72px">规则</th><td class="small">' + esc(n.desc || n.label) + '</td></tr></tbody></table>'
      + '<div class="tip" style="margin-top:12px">专家知识（KNW节点）由数据转换模块产出，作为校验判定的知识基准。</div>';
  }
  return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
    + '<span style="width:9px;height:9px;border-radius:3px;background:' + meta[2] + '"></span>'
    + '<span style="font-size:11px;font-weight:700;color:' + meta[2] + ';letter-spacing:1px">' + meta[1].toUpperCase() + '</span>'
    + '<span class="tag" style="font-size:10px;margin-left:auto">' + (n.score != null ? '得分' + n.score : '') + '</span></div>'
    + body;
}
function buildGraphCanvas(g){
  const st = S.cstGraph;
  const queried = !!g;
  const dflt = (SRS_DEMO.graphs[st.doc] || {}).question || '';
  const relName = { '问题直接命中':'问题命中','ID父子':'ID父子','同章节':'同章节','同表':'同表' };
  /* 可交互可配置召回条: 查询输入 + 召回参数(深度/每模态/阈值) + 图例点选过滤 */
  const cfg = S.mmCfg;
  const legend = [['E','实体','#2563EB']].concat(MM_MODS).map(m =>
    '<span class="tag" style="font-size:10px;background:' + m[2] + '15;color:' + m[2] + ';cursor:pointer;'
    + (cfg.hidden[m[0]] ? 'opacity:.35' : '') + '" onclick="mmToggleMod(\\\'' + m[0] + '\\\')" title="点击显隐该模态">' + m[1] + '</span>').join('');
  let nContent = 0;
  if (queried){
    MM_MODS.forEach(m => { if (cfg.hidden[m[0]]) return;
      nContent += (g.groups[m[0]] || []).filter(n => (n.score == null ? 1 : n.score) >= cfg.minW).slice(0, cfg.topK).length; });
  }
  const strip = '<div class="card" style="margin-bottom:12px;padding:14px 22px">'
    + '<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">'
    + '<input class="inp" id="mmQ" style="width:590px;height:38px;font-size:13.5px" value="' + esc(S.mmCfg.q || (queried ? g.question : dflt)) + '" placeholder="输入实体 / 功能名 / ID / 问题 查询上下文关联…" onkeydown="if(event.key===\\\'Enter\\\')mmQuery()">'
    + '<button class="btn mmquery-btn" onclick="mmQuery()">🔍 查询</button>'
    + '</div>'
    + '<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:11px">'
    + '<span class="small" style="color:var(--txt3)">召回深度</span>'
    + '<select class="sel" style="width:76px;height:30px" onchange="S.mmCfg.k=+this.value" title="连接实时引擎时生效">'
    + '<option value="1"' + (cfg.k === 1 ? ' selected' : '') + '>1 跳</option><option value="2"' + (cfg.k === 2 ? ' selected' : '') + '>2 跳</option></select>'
    + '<span class="small" style="color:var(--txt3)">每模态数量</span>'
    + '<select class="sel" style="width:76px;height:30px" onchange="S.mmCfg.topK=+this.value;mmApplyCfg()">'
    + [4, 6, 8, 12].map(v => '<option value="' + v + '"' + (cfg.topK === v ? ' selected' : '') + '>' + v + ' 条</option>').join('') + '</select>'
    + '<span class="small" style="color:var(--txt3)">分数阈值</span>'
    + '<select class="sel" style="width:76px;height:30px" onchange="S.mmCfg.minW=+this.value;mmApplyCfg()">'
    + [0.3, 0.5, 0.7].map(v => '<option value="' + v + '"' + (Math.abs(cfg.minW - v) < 1e-9 ? ' selected' : '') + '>' + v + '</option>').join('') + '</select>'
    + '<span class="small" style="color:var(--txt3);margin-left:8px">中心实体 ' + (queried
        ? '<b style="color:var(--primary);font-size:13px">' + esc((g.center.alias || g.center.label).slice(0, 12)) + '</b>'
        : '<span class="muted">待查询</span>') + '</span>'
    + '<span class="small" style="color:var(--txt3)">相关实体 <b style="color:var(--txt);font-size:13px">' + (queried ? g.related.length : 0) + '</b></span>'
    + '<span class="small" style="color:var(--txt3)">召回 <b style="color:var(--txt);font-size:13px">' + nContent + '</b> 条</span>'
    + '</div>'
    + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:11px;padding-top:10px;border-top:1px solid var(--line2)">'
    + '<span class="small" style="color:var(--txt3);margin-right:4px">模态显隐（点击）</span>'
    + legend
    + '<span class="small" style="color:var(--txt3);margin-left:auto">引擎: 自动连接 127.0.0.1:8300（离线自动降级）</span>'
    + '</div>'
    + '</div>';

  /* 未查询: 空态引导 */
  if (!queried){
    return strip
      + '<div class="card" style="flex:1;min-width:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px">'
      + '<div style="text-align:center;padding:30px">'
      + '<span style="font-size:40px">🕸</span>'
      + '<div style="font-size:15px;font-weight:700;margin:12px 0 6px">已选择数据源，尚未召回</div>'
      + '<div class="small" style="color:var(--txt3);line-height:1.9">查询框已预置该数据源的默认实体<br>点击「查询」开始上下文关联召回</div>'
      + '<button class="btn mmquery-btn" style="margin-top:16px" onclick="mmQuery()">🔍 开始查询</button>'
      + '</div></div>';
  }
  const rels = g.related.map(r => '<div class="mmcard mment" onclick="mGraphNode(\\'rel:' + esc(r.id_str) + '\\', this)">'
    + '<div style="font-size:13px;font-weight:650">' + esc(r.name) + '</div>'
    + '<div style="display:flex;gap:6px;margin-top:5px;align-items:center">'
    + '<span class="tag" style="font-size:10px;' + (r.rel === '问题直接命中' ? 'background:var(--blue-bg);color:var(--primary)' : '') + '">' + (relName[r.rel] || r.rel) + '</span>'
    + '<span style="font-size:10px;color:var(--txt3);margin-left:auto">' + r.score.toFixed(2) + '</span></div></div>').join('');
  const center = '<div class="mmcard mmcenter" id="mm-center" onclick="mGraphNode(\\'center\\', this)">'
    + '<div class="mmtag">输入实体</div>'
    + '<div style="font-size:16px;font-weight:700">' + esc(g.center.alias || g.center.label) + '</div>'
    + '<code style="font-size:10px;opacity:.8;word-break:break-all">' + esc(g.center.label) + '</code></div>';
  const groups = MM_MODS.filter(m => !cfg.hidden[m[0]] && (g.groups[m[0]] || []).length).map(m => {
    const raw = g.groups[m[0]];
    const list = raw.filter(n => (n.score == null ? 1 : n.score) >= cfg.minW).slice(0, cfg.topK);
    if (!list.length) return '';
    return '<div class="mmgrp" style="border-color:' + m[2] + '44;background:' + m[2] + '07">'
      + '<div class="mmghd" style="color:' + m[2] + '" id="mm-grp-' + m[0] + '"><span class="dot" style="background:' + m[2] + '"></span>' + m[1] + ' <span class="tag" style="font-size:10px">' + list.length + '</span></div>'
      + list.map((n, j) => '<div class="mmnode" style="border-left:3px solid ' + m[2] + '" onclick="mGraphNode(\\'node:' + m[0] + ':' + raw.indexOf(n) + '\\', this)">'
        + '<div style="font-size:12px;font-weight:550" class="ell">' + esc(nodeTitle(m[0], n)) + '</div>'
        + '<div style="font-size:10.5px;color:var(--txt3)" class="ell">' + esc(nodeSub(m[0], n)) + '</div>'
        + (n.via ? '<div style="font-size:9.5px;color:var(--primary);opacity:.7">⇐ ' + esc(n.via) + '</div>' : '')
        + '</div>').join('') + '</div>';
  }).join('');
  setTimeout(drawMmLinks, 60);
  return strip
    + '<div class="card" style="flex:1;min-width:0;height:calc(100vh - 178px);display:flex;flex-direction:column">'
    + '<div class="card-hd"><h3>上下文关联图谱 · ' + esc((SRS_DEMO.datasets.find(x => x.num === S.cstGraph.doc) || { name: '' }).name.slice(0, 18)) + '</h3>'
      + '<span class="small" style="color:var(--txt3)">中心实体 → 相关实体' + g.related.length + ' → 模态分组' + g.stats.n_content + '条（点击节点查看详情）</span></div>'
    + '<div style="flex:1;overflow:auto;position:relative;background:linear-gradient(180deg,#fafbfd,#f3f6fb)" class="mmwrap">'
      + '<svg class="mmlinks" style="position:absolute;left:0;top:0;pointer-events:none;overflow:visible;z-index:0"></svg>'
      + '<div class="mmcols" style="display:inline-flex;gap:38px;padding:26px 30px;position:relative;z-index:1">'
        + '<div style="width:220px;flex:0 0 220px;display:flex;flex-direction:column;justify-content:center;gap:10px">' + center + '</div>'
        + '<div style="width:210px;flex:0 0 210px;display:flex;flex-direction:column;justify-content:center;gap:10px">'
          + '<div class="small" style="color:var(--txt3);font-weight:600;letter-spacing:2px">相关实体 ' + g.related.length + '</div>' + rels + '</div>'
        + '<div style="width:340px;flex:0 0 340px">'
          + '<div class="small" style="color:var(--txt3);font-weight:600;letter-spacing:2px;margin-bottom:10px">召回内容 ' + g.stats.n_content + '</div>'
          + '<div style="display:flex;flex-direction:column;gap:11px">' + groups + '</div></div>'
      + '</div></div></div>';
}
function nodeTitle(mod, n){
  if (mod === 'TXT') return n.label;
  if (mod === 'TBL' || mod === 'IMG') return n.caption || n.label;
  if (mod === 'SEQ') return n.seq || n.label;
  if (mod === 'KNW') return n.rule || n.label;
  return n.label;
}
function nodeSub(mod, n){
  if (mod === 'TXT') return (n.preview || '') + (n.section ? ' · ' + n.section : '');
  if (mod === 'TBL') return (n.headers || []).join(' | ');
  if (mod === 'IMG') return (n.img_type || '') + ' · ' + (n.section || '');
  if (mod === 'SEQ') return n.label;
  if (mod === 'KNW') return '规则';
  return n.section || '';
}
/* 思维导图连线: 中心→实体, 实体→分组(贝塞尔) */
function drawMmLinks(){
  const svg = document.querySelector('.mmlinks');
  const wrap = document.querySelector('.mmwrap');
  if (!svg || !wrap) return;
  const g = SRS_DEMO.graph_demo;
  const wr = wrap.getBoundingClientRect();
  svg.setAttribute('width', wrap.scrollWidth); svg.setAttribute('height', wrap.scrollHeight);
  const R = el => { const r = el.getBoundingClientRect();
    return { x1: r.left - wr.left + r.width, y1: r.top - wr.top + r.height / 2,
             x2: r.left - wr.left, y2: r.top - wr.top + r.height / 2 }; };
  const bez = (a, b, color, w) => { const dx = Math.max(30, (b.x2 - a.x1) * 0.45);
    return '<path d="M ' + a.x1 + ' ' + a.y1 + ' C ' + (a.x1 + dx) + ' ' + a.y1 + ', ' + (b.x2 - dx) + ' ' + b.y2 + ', ' + b.x2 + ' ' + b.y2 + '" fill="none" stroke="' + color + '" stroke-width="' + w + '" opacity="0.75"/>'; };
  let out = '';
  const cEl = document.getElementById('mm-center');
  if (cEl) { const rc = R(cEl);
    document.querySelectorAll('.mment').forEach(el => { out += bez(rc, R(el), '#2563EB', 1.8); });
    MM_MODS.forEach(m => { const ge = document.getElementById('mm-grp-' + m[0]);
      if (ge) out += bez(rc, R(ge), m[2] + '99', 1.2); });
  }
  svg.innerHTML = out;
}
/* ---- 不一致性校验: 左数据分类树 + 右清单; 52项按 语法/语义/逻辑 三级分类+细分原因 ---- */
S.cstItems = { cat:'' };
function cstItemsOpen(c){ S.cstItems.cat = c; render(); }
function isSrsCatId(catId){ return catName(catId).indexOf('软件需求规格') >= 0; }
/* 52项 → 语法/语义/逻辑 三级分类, 每级细分不一致原因 */
const CST3 = {
  '语法不一致': [
    ['命名与代号规范', ['TERM-08']],
    ['结构完备性', ['GJB-01','GJB-05','GJB-06','GJB-07','GJB-08','GJB-09','GJB-10','GJB-11']],
    ['模态格式规范', ['MM-07','MM-09','MM-11']]
  ],
  '语义不一致': [
    ['术语语义冲突', ['TERM-01','TERM-02','TERM-03','TERM-04','TERM-05','TERM-06','TERM-07']],
    ['参数取值冲突', ['PARAM-01','PARAM-02','PARAM-03','PARAM-04','PARAM-05','PARAM-06','PARAM-07','PARAM-08','PARAM-09','PARAM-10']],
    ['业务语义完备', ['GJB-02','GJB-03','GJB-04']],
    ['值与完备性冲突', ['MM-02','MM-12']]
  ],
  '逻辑不一致': [
    ['控制与推理逻辑', ['LOGIC-01','LOGIC-02','LOGIC-03','LOGIC-04','LOGIC-05','LOGIC-06','LOGIC-07','LOGIC-08','LOGIC-09','LOGIC-10','LOGIC-11']],
    ['时序与流程', ['MM-01','MM-03']],
    ['拓扑与结构', ['MM-04','MM-05','MM-10']],
    ['内容对应', ['MM-06','MM-08']]
  ]
};
const CST3_META = { '语法不一致':'#0891b2', '语义不一致':'#d97706', '逻辑不一致':'#7c3aed' };
/* 从校验总览跳转图谱 */
function goCstGraph(num){
  if (num) S.cstGraph.doc = num;
  S.menu = 'consist'; S.sub = 'graph'; S.modal = null; render();
}
/* 导出报告 */
function exportRpt(){
  var w = window.open('', '_blank');
  if (w){ w.document.write(window.__rpt || ''); w.document.close(); }
}

/* 思维导图CSS(一次性注入) */
(function(){
  const css = '.mmcard{background:#fff;border-radius:12px;cursor:pointer;box-shadow:0 1px 3px rgba(15,23,42,.08),0 4px 14px rgba(15,23,42,.05);border:1px solid #eaeef5;transition:border-color .15s;padding:12px 14px}'
    + '.mmcard:hover{border-color:#c3cfe4}'
    + '.mmcenter{background:linear-gradient(135deg,#2563EB,#3B82F6);color:#fff;border:none;padding:18px 16px}'
    + '.mmtag{font-size:10px;letter-spacing:3px;opacity:.75;margin-bottom:6px}'
    + '.mment{border-left:3px solid #2563EB;padding:10px 12px}'
    + '.mmgrp{border:1px solid;border-radius:14px;padding:9px 11px 11px;display:flex;flex-direction:column;gap:6px}'
    + '.mmghd{display:flex;align-items:center;gap:7px;font-size:12.5px;font-weight:700;padding:2px 2px 7px;cursor:default}'
    + '.mmghd .dot{width:8px;height:8px;border-radius:3px}'
    + '.mmnode{background:#fff;border-radius:10px;padding:7px 10px;cursor:pointer;border:1px solid #eef2f7;font-size:12px}'
    + '.mmnode:hover{border-color:#c3cfe4}'
    + '.mmnode.mm-on{border-color:var(--primary);box-shadow:0 0 0 2px rgba(47,126,244,.3)}'
    + '.stats .stat.p .k,.stats .stat.p .v{color:var(--purple)}'
    + '.stats .stat.y .k,.stats .stat.y .v{color:#b8860b}'
    + '.mmquery-btn{height:38px;padding:0 26px;font-size:14px;font-weight:700;color:#fff;border:none;cursor:pointer;border-radius:8px;'
    + 'background:linear-gradient(135deg,#2f7ef4 0%,#1c62d0 100%);box-shadow:0 2px 10px rgba(47,126,244,.35);transition:.15s;font-family:inherit}'
    + '.mmquery-btn:hover{background:linear-gradient(135deg,#4a90f7 0%,#2f7ef4 100%);box-shadow:0 4px 14px rgba(47,126,244,.45);transform:translateY(-1px)}'
    + '.mmquery-btn:active{transform:translateY(0)}';
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
})();

""".replace("__DEMO_JSON__", json.dumps(DEMO, ensure_ascii=False))



# ============ A1: MENUS consist 4子项 ============
A1_OLD = "{ k:'consist', n:'一致性校验', ic:IC_CONSIST, subs:[{ k:'main', n:'一致性校验', ic:'🧾' }] },"
A1_NEW = """{ k:'consist', n:'一致性校验', ic:IC_CONSIST, subs:[
    { k:'main', n:'校验总览', ic:'🧾' },
    { k:'graph', n:'特征提取与上下文关联', ic:'🕸' }] },"""
html = inject(html, A1_OLD, A1_NEW, "A1-菜单4子项")

# ============ A2: TIPS ============
A2_OLD = "consist:'提示：对各类数据集进行一致性校验，识别问题与答案语义不匹配、答非所问、答案无法对应问题等异常样本。',"
A2_NEW = """consist:'提示：对各类数据集进行一致性校验，先查看总体校验结果，再逐层钻取到每个校验条目的明细与证据。',
  'consist.main':'提示：左侧选择数据源（一个数据源对应一组问答对），勾选条目后「开始校验」仅对选中项执行；每条问答对可查看特征提取与上下文关联、进行不一致性校验；右上「总报告」查看分门别类（语法·语义·逻辑）统计。',
  'consist.graph':'提示：特征提取与上下文关联智能体——左树选择数据源，右侧上下文图谱召回：中心实体→相关实体→五模态分组；点击节点在下方查看细粒度数据（表格行列/图片原图与Mermaid结构/正文/步骤链）。',"""
html = inject(html, A2_OLD, A2_NEW, "A2-提示语")

# ============ A3: 视图映射 ============
A3_OLD = "'consist.main': viewConsist,"
A3_NEW = """'consist.main': viewCstMain,
  'consist.graph': viewCstGraph,"""
html = inject(html, A3_OLD, A3_NEW, "A3-视图映射")

# ============ A5: STD_SEED c1三条 → 16份真实SRS ============
A5_OLD = """  ['c1','XX型飞控软件需求规格说明书.docx','飞控软件数据采集需求：软件应以不低于 50Hz 的频率采集姿态角、角速率、法向过载等飞行参数，采集数据须带时间戳并支持断电续存，存储容量不少于 4 小时飞行数据。'],
  ['c1','需求追踪矩阵.csv','需求追踪要求：每条软件需求须至少关联一条设计条目与一条测试用例，追踪矩阵中不允许出现孤立需求项，评审时对孤立项须给出书面说明。'],
  ['c1','软件需求问答样例.jsonl','软件需求变更控制：需求基线冻结后的变更须经变更控制委员会评审，评审通过后同步更新需求规格说明书、追踪矩阵与相关测试用例，并记录变更影响域。'],"""
srs_lines = []
for s in DEMO["std_data"]:
    txt = s["txt"].replace("'", "\\'").replace("\n", " ")[:78]
    srs_lines.append(f"  ['c1','{s['src']}','{txt}'],")
A5_NEW = "\n".join(srs_lines)
html = inject(html, A5_OLD, A5_NEW, "A5-标准数据16份SRS")

# ============ A6: cleanTasks真实口径 ============
A6_OLD = "['软件需求规格数据清洗','done',[{id:'c1',type:'local'}],['miss-txt','abn-sp','abn-tab','red-txt'],'需求文档切片后清洗',932,153],"
A6_NEW = "['软件需求规格数据清洗','done',[{id:'c1',type:'local'}],['miss-txt','abn-sp','abn-tab','red-txt'],'16份GJB 438C SRS解析为上下文关联图谱(5619节点/23850边/978聚合条目)',5619,978],"
html = inject(html, A6_OLD, A6_NEW, "A6-清洗任务口径")

# ============ A7: 真实QA注入(seedC2前) ============
qa_js = []
for q in DEMO["qa_pairs"]:
    qq = q["q"].replace("'", "\\'").replace("\n", " ")
    aa = q["a"].replace("'", "\\'").replace("\n", " ")
    ev = q["ev"].replace("'", "\\'").replace("\n", " ")
    qa_js.append("    { q:'%s', a:'%s', ev:'%s', doc:'%s', typ:'%s' }," % (qq, aa, ev, q["doc"], q["typ"]))
A7_ANCHOR = "/* 科研生产方案设计数据（c2）：补充问题与对应数据集（一问一条，内容一致）。"
A7_NEW = """/* ===== 数据替换: 真实GJB SRS问答对(替换c1分类模板数据, 一问一条含真实答案与证据) ===== */
const SRS_QA = [
%s
  ];
(function injectSrsQA(){
  const eff = id => { const oc = DB.onlineCats.find(c => c.id === id); return oc ? oc.cat : id; };
  /* 1) 清除c1分类的模板问题与数据集 */
  DB.questions = DB.questions.filter(q => eff(q.cat) !== 'c1');
  DB.datasets = DB.datasets.filter(d => eff(d.cat) !== 'c1');
  /* 2) 注入真实问答对: 问题→数据集(答案为真实answer) */
  SRS_QA.forEach((qa, i) => {
    const std = DB.stdData.find(x => x.cat === 'c1' && x.src.indexOf(qa.doc) === 0)
      || DB.stdData.find(x => x.cat === 'c1');
    const p = n => String(n).padStart(2, '0');
    const d = new Date(2026, 7, 12 + (i %% 10), 9 + (i %% 8), 15 + i);
    const time = d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes())+':00';
    const q = { id: uid('q'), sid: std ? std.id : '', cat: 'c1',
      src: std ? std.src : qa.doc + '.docx', ver: 'V1.' + ((i %% 3) + 1),
      q: qa.q, ans: true, time: time };
    DB.questions.push(q);
    DB.datasets.push({ id: uid('d'), qid: q.id, q: qa.q, a: qa.a, cat: 'c1', src: q.src,
      origin: i %% 4 === 3 ? '人工' : '智能体', score: null, ver: q.ver, fixed: false,
      evaled: false, type: 'qa', time: time, evalDetail: null,
      history: [{ ver: q.ver, time: time, by: '系统生成' }] });
  });
})();
""" % ("\n".join(qa_js))
html = inject(html, A7_ANCHOR, A7_NEW + A7_ANCHOR, "A7-真实问答对注入")

# ============ A4: 模块代码块(一致性校验代码前) ============
A4_ANCHOR = "/* ---- 一致性校验 ---- */"
html = inject(html, A4_ANCHOR, MODULE_CODE + A4_ANCHOR, "A4-模块代码块")

open(OUT, "w", encoding="utf-8").write(html)
print(f"\n构建完成 → {OUT}")
print(f"输出: {len(html)}字符 (原{len(open(SRC, encoding='utf-8').read())})")
