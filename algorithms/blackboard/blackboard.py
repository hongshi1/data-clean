"""Blackboard运行时: 版本化状态 + 决策日志 + 去重 + 最终上下文.

经典黑板(Hearsay-II)的现代形态:
  - Agent不直接通信, 只读写本对象
  - 每次write带 (channel, confidence, 认识论状态), 版本号+1
  - 每次状态迁移追加DecisionRecord → save后可审计/可回放
  - final_context() 输出"视图": 按subject聚合的事实/假设/置信度 —— 这是LLM
    被允许看到的全部内容(不是整个黑板塞进prompt)
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .schemas import (Channel, Critique, DecisionRecord, Epistemic,
                      EvidenceItem, Plan, TaskSpec)

_DIGEST_KEYS = ("table_structure", "diagram_structure", "prose_features",
                "element_correspondence", "discrepancy_set", "drift_status",
                "entity_mentions", "chunk_occurrences", "semantic_links",
                "vlm_extraction", "ocr_extraction", "image_hits",
                "detection_verdicts", "syntax_detections")


class Blackboard:
    """一次任务的共享状态空间. 生命周期 = runner的一个agent loop."""

    def __init__(self, task: TaskSpec, plan: Plan) -> None:
        self.task = task
        self.plan = plan
        self.version = 0
        self.evidence: list[EvidenceItem] = []
        self.records: list[DecisionRecord] = []
        self.agent_runs: set[tuple[str, str]] = set()   # (agent, subject)
        self.iteration = 0
        self.embedding_mode = "unavailable"             # runner注入
        self._fingerprints: set[str] = set()

    # ── 决策日志 ──────────────────────────────────────────
    def log(self, action: str, agent: str = "", channel: str = "",
            state_version: int | None = None, **detail: Any) -> None:
        self.records.append(DecisionRecord(
            seq=len(self.records), action=action, agent=agent, channel=channel,
            detail=detail, state_version=self.version if state_version is None else state_version))

    # ── 写入协议 ──────────────────────────────────────────
    def write(self, agent: str, item: EvidenceItem) -> bool:
        """唯一写入口. 去重(fingerprint) + 版本推进 + 审计记录.

        返回False表示重复写入(被吞掉但留痕).
        """
        fp = item.fingerprint()
        if fp in self._fingerprints:
            self.log("duplicate", agent=agent, channel=item.channel.value,
                     subject=item.subject, fingerprint=fp)
            return False
        self._fingerprints.add(fp)
        item.written_by = agent
        item.state_version = self.version + 1
        self.version += 1
        self.evidence.append(item)
        self.log("write", agent=agent, channel=item.channel.value,
                 item=item.brief(), fingerprint=fp)
        return True

    def mark_agent_run(self, agent: str, subject: str) -> None:
        self.agent_runs.add((agent, subject))

    def has_run(self, agent: str, subject: str) -> bool:
        return (agent, subject) in self.agent_runs

    def bump_iteration(self) -> None:
        self.iteration += 1

    # ── 读取视图 ──────────────────────────────────────────
    def by_subject(self, subject: str) -> list[EvidenceItem]:
        return [e for e in self.evidence if e.subject == subject]

    def subjects_written(self) -> set[str]:
        return {e.subject for e in self.evidence}

    def best_confidence(self, subject: str) -> float:
        confs = [e.confidence for e in self.by_subject(subject)]
        return max(confs) if confs else 0.0

    # ── 最终上下文(视图) ──────────────────────────────────
    def final_context(self, critique: Critique) -> dict[str, Any]:
        """输出给下游(检测器/LLM/人)的最终上下文表示."""
        subjects: dict[str, Any] = {}
        for key in sorted(self.subjects_written()):
            items = self.by_subject(key)
            facts = [e.brief() for e in items
                     if e.epistemic in (Epistemic.FACT, Epistemic.VERIFIED)]
            hyps = [e.brief() for e in items
                    if e.epistemic in (Epistemic.HYPOTHESIS, Epistemic.REFUTED)]
            subjects[key] = {
                "n_items": len(items),
                "n_facts": len(facts),
                "n_hypotheses": len(hyps),
                "best_confidence": round(self.best_confidence(key), 3),
                "channels": sorted({e.channel.value for e in items}),
                "digest": self._digest(key, items),
            }

        ctx = {
            "task": asdict(self.task),
            "verdict": critique.verdict,
            "iterations": self.iteration,
            "n_evidence": len(self.evidence),
            "n_records": len(self.records),
            "subjects": subjects,
            "missing": critique.missing,
            "missing_critical": critique.missing_critical,
            "open_semantic": critique.open_semantic,
            "reasons": critique.reasons,
            "embedding_mode": self.embedding_mode,
        }
        # 域特定汇总: 分歧清单 + 检测判决直接给出(检测层的输入与输出)
        discs = self._collect_payload("discrepancy_set", "discrepancies")
        if discs:
            ctx["discrepancies"] = discs
            ctx["n_discrepancies"] = sum(len(d) if isinstance(d, list) else 0 for d in discs)
        for e in self.by_subject("detection_verdicts"):
            ctx["detection"] = e.payload
            break
        return ctx

    def _digest(self, key: str, items: list[EvidenceItem]) -> dict[str, Any]:
        """subject级的紧凑摘要: 下游消费的领域形态."""
        out: dict[str, Any] = {}
        for e in items:
            p = e.payload
            if key == "table_structure":
                names = [n["text"] for n in p.get("nodes", []) if n.get("text")]
                out.update({"table_type": p.get("type", "?"), "n_items": p.get("n_items", len(names)),
                            "item_names": names[:20]})
                if p.get("uc_name"):
                    out["uc_name"] = p["uc_name"]
                if p.get("actors"):
                    out["actors"] = p["actors"]
                if p.get("exceptions"):
                    out["n_exceptions"] = len(p["exceptions"])
            elif key == "diagram_structure":
                texts = [n["text"] for n in p.get("nodes", []) if n.get("text")]
                out.update({"n_nodes": len(texts), "node_texts": texts[:20],
                            "n_edges": len(p.get("edges", [])),
                            "mapping_confidence": p.get("mapping_confidence", ""),
                            "channel": e.channel.value})
            elif key == "prose_features":
                out.update({
                    "n_behaviors": len(p.get("behaviors", [])),
                    "n_enumerations": len(p.get("enumerations", [])),
                    "enumeration_items": [it for en in p.get("enumerations", [])
                                          for it in en.get("items", [])][:20],
                    "constraints": p.get("constraints", [])[:10],
                    "references": p.get("references", [])[:10],
                    "ids": p.get("ids", [])[:10],
                })
            elif key == "element_correspondence":
                out.update({"n_table": p.get("n_table", 0), "n_diag": p.get("n_diag", 0),
                            "n_matched": p.get("n_matched", 0),
                            "match_rate": p.get("match_rate")})
            elif key == "drift_status":
                out.update({"status": p.get("status"), "align_score": p.get("align_score"),
                            "n_drift": p.get("n_drift", 0)})
            elif key == "entity_mentions":
                out.update({"entity_id": p.get("entity_id", ""), "n_mentions": p.get("n_mentions", 0),
                            "sections": p.get("sections", [])[:15]})
            elif key == "chunk_occurrences":
                out.update({"n_occurrences": p.get("n_occurrences", 0),
                            "sections": p.get("sections", [])[:15]})
            elif key == "semantic_links":
                out.update({"n_matches": len(p.get("matches", [])),
                            "matches": p.get("matches", [])[:15]})
            elif key == "detection_verdicts":
                s = p.get("summary", {})
                out.update({"summary": s,
                            "n_report": s.get("n_report", 0),
                            "n_pass": s.get("n_pass", 0),
                            "n_abstain": s.get("n_abstain", 0),
                            "n_tool_issue": s.get("n_tool_issue", 0),
                            "coverage": s.get("coverage"),
                            "pi_scene": s.get("pi_scene")})
            elif key == "syntax_detections":
                out.update({"doc": p.get("doc", ""),
                            "n_detections": p.get("n_detections", 0),
                            "by_rule": p.get("by_rule", {})})
        return out

    def _collect_payload(self, subject: str, field_name: str) -> list[Any]:
        vals = []
        for e in self.by_subject(subject):
            v = e.payload.get(field_name)
            if v:
                vals.append(v)
        return vals

    # ── 持久化 ────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return {
            "task": asdict(self.task),
            "version": self.version,
            "iteration": self.iteration,
            "embedding_mode": self.embedding_mode,
            "evidence": [
                {"subject": e.subject, "channel": e.channel.value,
                 "epistemic": e.epistemic.value, "confidence": e.confidence,
                 "conf_source": e.conf_source.value, "payload": e.payload,
                 "provenance": asdict(e.provenance), "note": e.note,
                 "written_by": e.written_by, "state_version": e.state_version}
                for e in self.evidence
            ],
            "n_records": len(self.records),
        }

    def save(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        state_path = out_dir / "state.json"
        state_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        log_path = out_dir / "decision_log.jsonl"
        with open(log_path, "w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(rec.to_json() + "\n")
        return state_path

    @classmethod
    def load(cls, state_path: Path, plan: Plan) -> "Blackboard":
        """从state.json重建黑板(回放审计用)."""
        data = json.loads(state_path.read_text(encoding="utf-8"))
        from .schemas import ConfSource, Epistemic, Provenance, TaskType
        task = TaskSpec(task_id=data["task"]["task_id"],
                        task_type=TaskType(data["task"]["task_type"]),
                        **{k: v for k, v in data["task"].items()
                           if k not in ("task_id", "task_type")})
        bb = cls(task, plan)
        bb.version = data["version"]
        bb.iteration = data["iteration"]
        bb.embedding_mode = data.get("embedding_mode", "unavailable")
        for e in data["evidence"]:
            item = EvidenceItem(
                subject=e["subject"], channel=Channel(e["channel"]),
                epistemic=Epistemic(e["epistemic"]), confidence=e["confidence"],
                conf_source=ConfSource(e["conf_source"]), payload=e["payload"],
                provenance=Provenance(**e["provenance"]), note=e.get("note", ""),
                written_by=e.get("written_by", ""),
                state_version=e.get("state_version", 0))
            bb.evidence.append(item)
            bb._fingerprints.add(item.fingerprint())
        return bb
