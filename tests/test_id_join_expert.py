"""Tests for the ID→主体注册表 join expert (L1, TERM-07)."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import (  # noqa: E402
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.id_join_expert import (  # noqa: E402
    METHOD,
    build_id_registry,
    extract_id_claims,
    verify_id_joins,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

DOC_ID = "04数据统一访问服务软件需求规格说明-终稿"

#: 能力表(表39形态): 序号/Use case名称/项目唯一标识符/需求描述/...
CAPABILITY_TABLE = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>连接池配置</p></td>"
    "<td><p>PZXQ-GN-LJCGL-LJCPZ</p></td><td><p>支持配置连接池</p></td>"
    "<td><p>新研</p></td><td><p>桌面</p></td><td><p>运行阶段</p></td>"
    "<td><p>4.1.2</p></td></tr>"
    "<tr><td><p>2</p></td><td><p>连接池初始化</p></td>"
    "<td><p>PZXQ-GN-LJCGL-LJCCSH</p></td><td><p>提供初始化连接池的能力</p></td>"
    "<td><p>新研</p></td><td><p>桌面</p></td><td><p>运行阶段</p></td>"
    "<td><p>4.1.2</p></td></tr>"
    "</tbody></table>"
)

#: 接口表(表48/53形态): 接口需求名称/接口需求标识/发送方/接收方/...
INTERFACE_TABLE = (
    "<table><tr><td><p>序号</p></td><td><p>接口需求名称</p></td>"
    "<td><p>接口需求标识</p></td><td><p>接口类型</p></td>"
    "<td><p>发送方</p></td><td><p>接收方</p></td>"
    "<td><p>接口内容</p></td><td><p>接口优先级</p></td></tr>"
    "<tr><td><p>1</p></td><td><p>代码生成与对象化访问接口</p></td>"
    "<td><p>PZXQ-NBJK-DMSC-DXHFW</p></td><td><p>API</p></td>"
    "<td><p>代码生成</p></td><td><p>对象化访问</p></td>"
    "<td><p>头文件路径信息</p></td><td><p>中</p></td></tr>"
    "</table>"
)

SECTION_DUAL_A = "3.2.5.1 连接池管理-连接池配置（PZXQ-GN-LJCGL-LJCCSH）"
SECTION_DUAL_B = "3.2.5.2 连接池管理-连接池初始化（PZXQ-GN-LJCGL-LJCCSH）"
SECTION_SWAPPED = "3.4.2 代码生成与对象化访问接口（PZXQ-NBJK-DXHFW-DMSC）"
SECTION_MISSING = "3.2.1.4.1.1 BLOB数据操作-BLOB数据插入（PZXQ-GN-SQLFW-BLOBSJCZ-BLOBSJCR）"
BLOB_TABLE = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "</tr></thead><tbody>"
    "<tr><td></td><td><p>Blob数据插入</p></td>"
    "<td><p>PZXQ-GN-SQLFW-BLOBSJCR</p></td>"
    "<td><p>支持对BLOB数据的插入</p></td></tr>"
    "</tbody></table>"
)


def make_request(answer: str, *texts: str, question: str = "标识符是什么？",
                 instance_id: str = "qa-idjoin") -> QAInput:
    evidence = tuple(
        RetrievedEvidence(
            evidence_id=f"ev-{index:02d}",
            text=text,
            source_type="table" if "<table" in text else "text",
            source_ref=SourceRef(doc_id=DOC_ID, section=""),
            scope_id=f"{DOC_ID}:ev-{index:02d}",
            completeness="open",
        )
        for index, text in enumerate(texts, start=1)
    )
    return QAInput(
        instance_id=instance_id,
        question=question,
        answer=answer,
        context_freeze_id="frozen-idjoin-1",
        evidence=evidence,
    )


def statements_of(*texts: str) -> list[EvidenceStatement]:
    request = make_request("", *texts)
    return linearize_context(request.evidence)


def refutes(results: list) -> list:
    return [r for r in results if r.verdict == "refute"]


def test_build_id_registry_extracts_table_and_section_bindings() -> None:
    registry = build_id_registry(statements_of(
        CAPABILITY_TABLE, SECTION_DUAL_A, INTERFACE_TABLE))
    assert set(registry) == {
        "PZXQ-GN-LJCGL-LJCPZ", "PZXQ-GN-LJCGL-LJCCSH",
        "PZXQ-NBJK-DMSC-DXHFW",
    }
    ljccsh = registry["PZXQ-GN-LJCGL-LJCCSH"]
    # 表39(连接池初始化) + 3.2.5.2节标题均注册; 3.2.5.1节标题主体=叶子名
    subjects = {registration.subject for registration in ljccsh}
    assert subjects == {"连接池初始化", "连接池配置"}
    ljcpz = registry["PZXQ-GN-LJCGL-LJCPZ"]
    assert [registration.subject for registration in ljcpz] == ["连接池配置"]
    assert ljcpz[0].field_name == "标识符"
    assert ljcpz[0].evidence_id == "ev-01"
    assert ljcpz[0].statement_id.startswith("ev-01#")
    dmsc = registry["PZXQ-NBJK-DMSC-DXHFW"]
    assert [registration.subject for registration in dmsc] == ["代码生成与对象化访问接口"]


def test_build_id_registry_compacts_ids_with_internal_space() -> None:
    spaced = "3.2.1.4.1.2 BLOB数据操作-BLOB数据修改（PZXQ-GN-SQLFW-BLOBSJCZ- BLOBSJXG）"
    registry = build_id_registry(statements_of(spaced))
    assert "PZXQ-GN-SQLFW-BLOBSJCZ-BLOBSJXG" in registry


def test_extract_id_claims_subject_forms() -> None:
    claims = extract_id_claims(
        "数据库关闭能力的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。")
    assert [(c.identifier, c.subject) for c in claims] == [
        ("PZXQ-GN-SJKCZ-SJKGB", "数据库关闭")]
    claims = extract_id_claims(
        "数据统一访问服务与运行支撑服务接口的接口需求标识为PZXQ-JK-SJTYFW-YXZCFW。")
    assert claims[0].subject == "数据统一访问服务与运行支撑服务接口"
    claims = extract_id_claims("数据源适配接口（PZXQ-GN-SJYSP）与SQL访问。")
    assert claims[0].subject == "数据源适配接口"
    # 连接词保留: answer声称两个用例共用同一ID
    claims = extract_id_claims(
        "连接池配置用例和连接池初始化用例的项目唯一标识符均为PZXQ-GN-LJCGL-LJCCSH。")
    assert claims[0].subject == "连接池配置用例和连接池初始化"
    # markdown列表的角色词前缀不构成主体 → 裸ID
    claims = extract_id_claims("2. **与运行支撑服务接口**：\n   - 接口标识：PZXQ-JK-SJTYFW-YXZCFW\n")
    assert claims[0].subject is None
    # 角色词/泛指词主体降为裸ID
    claims = extract_id_claims("接口标识为PZXQ-JK-UNKNOWN。")
    assert claims[0].subject is None
    # 重复声明按(ID,主体)去重
    claims = extract_id_claims("X的标识为PZXQ-GN-A。X的标识为PZXQ-GN-A。")
    assert len(claims) == 1


def test_check1_double_registration_refutes_shared_id() -> None:
    request = make_request(
        "连接池配置用例和连接池初始化用例的项目唯一标识符均为PZXQ-GN-LJCGL-LJCCSH。",
        CAPABILITY_TABLE, SECTION_DUAL_A, SECTION_DUAL_B)
    results = verify_id_joins(request, statements_of(
        CAPABILITY_TABLE, SECTION_DUAL_A, SECTION_DUAL_B))
    fired = refutes(results)
    assert len(fired) == 1
    claim = fired[0]
    assert claim.claim_text == "PZXQ-GN-LJCGL-LJCCSH"
    assert claim.verdict == "refute"
    assert claim.method == METHOD
    assert claim.check_item_candidates == ("TERM-07",)
    assert claim.confidence == 1.0
    assert "双登记" in claim.rationale
    assert "连接池配置" in claim.rationale and "连接池初始化" in claim.rationale
    # 暴露表39侧连接池配置的真实注册(违例的另一半证据)
    assert "PZXQ-GN-LJCGL-LJCPZ" in claim.rationale
    assert set(claim.evidence_refs) == {
        "ev-01#s6", "ev-02#s0", "ev-03#s0"}
    assert claim.claim_id == "qa-idjoin-idjoin01"


def test_check2_subject_id_mismatch_refutes_wrong_family_id() -> None:
    # VIO-02形态: 表4登记SJKGBGN, answer声称同族另一ID
    table = (
        "<table><thead><tr><th><p>序号</p></th>"
        "<th><p>Use case名称</p></th><th><p>项目唯一标识符</p></th>"
        "<th><p>需求描述</p></th></tr></thead><tbody>"
        "<tr><td></td><td><p>数据库关闭</p></td>"
        "<td><p>PZXQ-GN-SJKCZ-SJKGBGN</p></td><td><p>关闭数据库</p></td></tr>"
        "</tbody></table>")
    request = make_request("数据库关闭能力的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。", table)
    results = verify_id_joins(request, statements_of(table))
    fired = refutes(results)
    assert len(fired) == 1
    assert "subject-ID错配" in fired[0].rationale
    assert "PZXQ-GN-SJKCZ-SJKGBGN" in fired[0].rationale
    assert "ID家族错配" in fired[0].rationale
    assert fired[0].evidence_refs


def test_check3_segment_order_swap_is_detected() -> None:
    # VIO-04形态: 表53=DMSC-DXHFW, 3.4.2节标题=DXHFW-DMSC
    request = make_request(
        "代码生成与对象化访问接口的接口需求标识为PZXQ-NBJK-DMSC-DXHFW。",
        INTERFACE_TABLE, SECTION_SWAPPED)
    results = verify_id_joins(request, statements_of(
        INTERFACE_TABLE, SECTION_SWAPPED))
    fired = refutes(results)
    assert len(fired) == 1
    assert "段序颠倒" in fired[0].rationale
    assert "PZXQ-NBJK-DXHFW-DMSC" in fired[0].rationale
    assert set(fired[0].evidence_refs) == {"ev-01#s0", "ev-02#s0"}


def test_check3_missing_segment_is_detected() -> None:
    # VIO-05形态: 表23=BLOBSJCR(缺段), 节标题=BLOBSJCZ-BLOBSJCR
    request = make_request(
        "BLOB数据插入能力的项目唯一标识符为PZXQ-GN-SQLFW-BLOBSJCR。",
        BLOB_TABLE, SECTION_MISSING)
    results = verify_id_joins(request, statements_of(
        BLOB_TABLE, SECTION_MISSING))
    fired = refutes(results)
    assert len(fired) == 1
    assert "缺组件段BLOBSJCZ" in fired[0].rationale
    # Blob/BLOB大小写归一后表侧与节侧主体是同一实体
    assert set(fired[0].evidence_refs) == {"ev-01#s0", "ev-02#s0"}


def test_consistent_binding_emits_no_conflict_claim() -> None:
    # 主体在表与节标题两侧登记同一ID → 无冲突, 不产生任何claim
    consistent_section = "3.2.5.2 连接池管理-连接池初始化（PZXQ-GN-LJCGL-LJCCSH）"
    request = make_request(
        "连接池初始化用例的项目唯一标识符为PZXQ-GN-LJCGL-LJCCSH。",
        CAPABILITY_TABLE, consistent_section)
    assert verify_id_joins(request, statements_of(
        CAPABILITY_TABLE, consistent_section)) == []


def test_cross_family_parent_ids_do_not_conflict() -> None:
    # 能力ID(PZXQ-GN-*)与接口ID(PZXQ-NBJK-*)是不同族: 主体包含匹配但
    # ID族不同不算TERM-07冲突(父子层级, 防假refute)
    request = make_request(
        "数据源适配接口（PZXQ-GN-SJYSP）与SQL访问接口的连接方式是明确的。",
        INTERFACE_TABLE,
        "3.2.5 数据源适配（PZXQ-GN-SJYSP）")
    assert verify_id_joins(request, statements_of(
        INTERFACE_TABLE, "3.2.5 数据源适配（PZXQ-GN-SJYSP）")) == []


def test_check4_bare_id_supports_registered_and_nie_unregistered() -> None:
    request = make_request("提供PZXQ-GN-LJCGL-LJCPZ等能力。", CAPABILITY_TABLE)
    results = verify_id_joins(request, statements_of(CAPABILITY_TABLE))
    assert len(results) == 1
    claim = results[0]
    assert claim.verdict == "support"
    assert claim.claim_text == "PZXQ-GN-LJCGL-LJCPZ"
    assert claim.evidence_refs == ("ev-01#s0",)

    unknown = make_request("提供PZXQ-GN-XXX-YYY等能力。", CAPABILITY_TABLE)
    results = verify_id_joins(unknown, statements_of(CAPABILITY_TABLE))
    assert len(results) == 1
    assert results[0].verdict == "not_in_evidence"


def test_check4_support_requires_verbatim_evidence() -> None:
    # 注册表命中但证据原文无该ID(如ID内空格) → 不重复旧通道的support
    spaced = (
        "<table><thead><tr><th><p>序号</p></th>"
        "<th><p>Use case名称</p></th><th><p>项目唯一标识符</p></th>"
        "<th><p>需求描述</p></th></tr></thead><tbody>"
        "<tr><td></td><td><p>连接池配置</p></td>"
        "<td><p>PZXQ-GN-LJCGL- LJCPZ</p></td>"
        "<td><p>支持配置连接池</p></td></tr></tbody></table>")
    request = make_request("提供PZXQ-GN-LJCGL-LJCPZ等能力。", spaced)
    statements = statements_of(spaced)
    registry = build_id_registry(statements)
    assert "PZXQ-GN-LJCGL-LJCPZ" in registry  # 空白折叠后注册表命中
    results = verify_id_joins(request, statements)
    assert results[0].verdict == "not_in_evidence"


def test_unregistered_subject_does_not_fire() -> None:
    # answer主体未注册 → 无法仲裁, 不产生claim(保守NIE语义留给旧通道)
    request = make_request("未知能力的标识符为PZXQ-GN-SQLFW-BLOBSJCR。",
                           CAPABILITY_TABLE)
    assert verify_id_joins(request, statements_of(CAPABILITY_TABLE)) == []


def test_module_integration_refute_overrides_legacy_support() -> None:
    # 端到端: 旧identifier通道对表侧ID给support, id_join专家的refute
    # 在per-claim融合(同claim文本 refute>support)中压制误support
    module = QAConsistencyModule(use_experts=True)
    request = make_request(
        "代码生成与对象化访问接口的接口需求标识为PZXQ-NBJK-DMSC-DXHFW。",
        INTERFACE_TABLE, SECTION_SWAPPED)
    result = module.verify(request)
    assert result.verdict == "refute"
    fused = [claim for claim in result.claim_results
             if claim.claim_text == "PZXQ-NBJK-DMSC-DXHFW"]
    assert len(fused) == 1
    assert fused[0].verdict == "refute"
    assert fused[0].method == METHOD


def test_module_consistent_identifier_answer_stays_supported() -> None:
    module = QAConsistencyModule(use_experts=True)
    request = make_request(
        "连接池初始化用例的项目唯一标识符为PZXQ-GN-LJCGL-LJCCSH。",
        CAPABILITY_TABLE)
    result = module.verify(request)
    assert result.verdict == "support"


# ── 精确绑定优先: 父/子功能主体不混淆(G4 P1 a-fix, S1QA-053) ──

#: S1QA-053形态: ev-000067(子功能标识表) + ev-000035(父功能表)同族注册
CHILD_CAPABILITY_TABLE = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "</tr></thead><tbody>"
    "<tr><td></td><td><p>删除数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-SJXG</p></td>"
    "<td><p>支持删除数据记录</p></td></tr>"
    "<tr><td></td><td><p>增加数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-ZXSW</p></td>"
    "<td><p>支持增加数据记录</p></td></tr>"
    "<tr><td></td><td><p>修改数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-TJSW</p></td>"
    "<td><p>支持修改数据记录</p></td></tr>"
    "</tbody></table>"
)

#: 父功能"修改数据"的能力表行(ev-000035形态): 主体是子功能主体的父级
PARENT_CAPABILITY_TABLE = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "</tr></thead><tbody>"
    "<tr><td></td><td><p>修改数据</p></td>"
    "<td><p>PZXQ-GN-SQLFW-XGSJ</p></td>"
    "<td><p>支持修改数据记录的删除/增加/修改</p></td></tr>"
    "</tbody></table>"
)


def test_exact_binding_parent_registration_does_not_refute_child_claim() -> None:
    """S1QA-053 claim#3: 子功能精确绑定(TJSW)在册时, 父功能"修改数据"的
    XGSJ注册不构成绑定冲突——旧包含式匹配曾把父子两级混为同主体误refute."""
    request = make_request(
        "修改数据记录的项目唯一标识符为PZXQ-GN-SQLFW-TJSW。",
        CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE)
    assert verify_id_joins(request, statements_of(
        CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE)) == []


def test_exact_binding_child_claiming_parent_id_still_refutes() -> None:
    """声称子主体的ID是父功能的ID → 仍检出subject-ID错配(真冲突)."""
    request = make_request(
        "修改数据记录的项目唯一标识符为PZXQ-GN-SQLFW-XGSJ。",
        CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE)
    results = verify_id_joins(request, statements_of(
        CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE))
    fired = refutes(results)
    assert len(fired) == 1
    assert "subject-ID错配" in fired[0].rationale
    assert "PZXQ-GN-SQLFW-TJSW" in fired[0].rationale


def test_exact_binding_parent_claiming_child_id_still_refutes() -> None:
    """声称父主体的ID是子功能的ID → 精确层命中父注册, 仍检出错配."""
    request = make_request(
        "修改数据的项目唯一标识符为PZXQ-GN-SQLFW-TJSW。",
        CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE)
    results = verify_id_joins(request, statements_of(
        CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE))
    fired = refutes(results)
    assert len(fired) == 1
    assert "PZXQ-GN-SQLFW-XGSJ" in fired[0].rationale


def test_containment_fallback_direction_is_claimed_subset_registered() -> None:
    """包含回退方向固定: claimed(短/上位)⊂registered(长/具体)算命中,
    claimed(长/子)⊃registered(短/父)不算——父条目不仲裁子功能声称."""
    section = ("3.2.1.4.1.3 数据库操作-数据库关闭"
               "（PZXQ-GN-SJKCZ-SJKGBGN）")
    table = (
        "<table><thead><tr><th><p>序号</p></th>"
        "<th><p>Use case名称</p></th><th><p>项目唯一标识符</p></th>"
        "<th><p>需求描述</p></th></tr></thead><tbody>"
        "<tr><td></td><td><p>数据库关闭</p></td>"
        "<td><p>PZXQ-GN-SJKCZ-SJKGB</p></td>"
        "<td><p>关闭数据库</p></td></tr></tbody></table>")
    statements = statements_of(table, section)
    # 无精确命中: claimed「数据库操作」⊂registered全名「数据库操作-数据库关闭」
    # → 包含层命中SJKGBGN注册, 声称同族另一ID仍检出错配
    request = make_request(
        "数据库操作的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。",
        table, section)
    results = verify_id_joins(request, statements)
    assert len(refutes(results)) == 1
    # 无精确命中且claimed更长(声称子级, 注册表只有父级短名) → 不算命中, 不fire
    only_parent = make_request(
        "数据库操作-数据库关闭的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGBGN。",
        table)
    parent_statements = statements_of(section)
    assert verify_id_joins(only_parent, parent_statements) == []


def test_module_s1qa_053_false_refute_is_eliminated() -> None:
    """端到端: 053式answer(复述子功能标识表, 证据含父功能表)不再误refute."""
    module = QAConsistencyModule(use_experts=True)
    answer = ("修改数据记录的功能标识表中包含以下内容：\n\n"
              "| 1 | 删除数据记录 | PZXQ-GN-SQLFW-SJXG | 支持删除数据记录 |\n"
              "| 2 | 增加数据记录 | PZXQ-GN-SQLFW-ZXSW | 支持增加数据记录 |\n"
              "| 3 | 修改数据记录 | PZXQ-GN-SQLFW-TJSW | 支持修改数据记录 |")
    request = make_request(
        answer, CHILD_CAPABILITY_TABLE, PARENT_CAPABILITY_TABLE,
        question="修改数据记录的功能标识表中包含哪些内容？",
        instance_id="qa-053-style")
    result = module.verify(request)
    assert result.verdict == "support"
    fused = {claim.claim_text: claim.verdict
             for claim in result.claim_results}
    assert fused.get("PZXQ-GN-SQLFW-TJSW") == "support"
