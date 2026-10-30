"""S1 evidence compiler: frozen evidence blocks -> typed schemas + focused views.

GJB 438C SRS tables (capability / use-case / interface / value-domain /
trace / qualification) are compiled from raw HTML into typed relational
schemas so downstream consistency checks operate on rows and columns instead
of blob text.  Figure evidence (Mermaid exports from anchor_v2) is parsed
into structured node/edge lists.  For every atomic claim a focused view
selects the minimal row/column subset relevant to its claim type:

- numeric claim      -> matched parameter row + min/max/precision/unit columns
- enumeration claim  -> matched prose enumeration sentences + member columns
- identifier claim   -> identifier columns
- exception claim    -> the E1 row of the matching use case
- step claim         -> the main-event-flow row of the matching use case

This layer is deterministic: schema rules and substring anchors only, no
model calls.  Table signatures, column canon maps, key columns and focused
column profiles are declared in the rule pack (config/rulepacks/*.json,
see docs/srs_project/64_rulepack_design.md); this module keeps the HTML
grid mechanics, claim-type routing and focus-selection semantics.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from srs_verify.answer_structure import StructuredClaim
from srs_verify.evidence_statements import (
    _linearize_text,
    _strip_tags,
    _table_rows,
)
from srs_verify.qa_models import RetrievedEvidence, SourceRef
from srs_verify.rulepack import (
    RulePack,
    TableSchemaSpec,
    UseCaseFields,
    compile_pattern,
    default_rulepack,
)

BASE = Path(__file__).resolve().parents[2]
MERMAID_EXPORT_PATH = BASE / "data/gjb_438c/anchor_v2/mermaid_export.json"
CONTENT_LIST_GLOB = "data/gjb_438c/mineru_standard/{}/office/*_content_list.json"

CAPABILITY_TABLE = "capability_table"
USE_CASE_TABLE = "use_case_table"
INTERFACE_TABLE = "interface_table"
VALUE_DOMAIN_TABLE = "value_domain_table"
TRACE_TABLE = "trace_table"
QUALIFICATION_TABLE = "qualification_table"
GENERIC_TABLE = "generic_table"

_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_TAG = re.compile(
    r"<t(?P<tag>[dh])(?P<attrs>(?:\s+[\w-]+(?:\s*=\s*\"[^\"]*\"))*)\s*>"
    r"(?P<body>.*?)</t(?P=tag)>",
    re.S,
)
_ATTR = re.compile(r"([\w-]+)\s*=\s*\"([^\"]*)\"")

_IDENTIFIER_TOKEN = re.compile(r"[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+){2,}")
_EXCEPTION_HINT = re.compile(r"异常流|E\d+")
_NUMERIC_HINT = re.compile(
    r"字符|字节|毫秒|分钟|小时|帧|条|次|个|位|MB|KB|GB|最大|最小|精度|"
    r"不超过|至少|最多|上限|下限|范围|长度|容量"
)
_DIGIT = re.compile(r"\d")
_STEP_HINT = re.compile(r"步骤|动作|事件流")
_ENUM_SEPARATOR = re.compile(r"[、；]")
_ENUM_HINT = re.compile(r"包括|分为|如下|适用于")

_ANCHOR_RUN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")
_SECTION_NUMBER = re.compile(r"\d+(?:\.\d+)+")

_MM_NODE = re.compile(
    r"^\s*(?P<id>[A-Za-z][A-Za-z0-9_]*)\s*"
    r"(?:\(\[(?P<stadium>[^\n]*)\]\)"
    r"|\[(?P<process>[^\n]*)\]"
    r"|\{(?P<decision>[^\n]*)\}"
    r"|\((?P<round>[^\n]*)\))\s*$"
)
_MM_EDGE = re.compile(
    r"^\s*(?P<src>[A-Za-z0-9_]+)\s*(?P<arrow>-->|---|-\.->|==>)\s*"
    r"(?:\|\"?(?P<label>[^\"|]*)\"?\s*\|)?\s*(?P<dst>[A-Za-z0-9_]+)\s*$"
)


@dataclass(frozen=True)
class TableRow:
    """One typed table row: scope key, use-case field name and (column, value) cells."""

    row_index: int
    key: str
    field: str
    cells: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class TableSchema:
    """A compiled table with recognized kind and canonical columns."""

    evidence_id: str
    kind: str
    caption: str
    columns: tuple[str, ...]
    rows: tuple[TableRow, ...]
    direction: str = ""


@dataclass(frozen=True)
class TextEvidence:
    """A prose block linearized into sentences."""

    evidence_id: str
    sentences: tuple[str, ...]


@dataclass(frozen=True)
class FigureNode:
    node_id: str
    label: str
    shape: str


@dataclass(frozen=True)
class FigureEdge:
    src_id: str
    dst_id: str
    label: str
    directed: bool


@dataclass(frozen=True)
class FigureGraph:
    """One Mermaid figure parsed into node/edge lists."""

    figure_id: str
    diagram_type: str
    nodes: tuple[FigureNode, ...]
    edges: tuple[FigureEdge, ...]
    mermaid: str


@dataclass(frozen=True)
class EvidenceSchema:
    """Typed relational schema compiled from frozen evidence blocks."""

    tables: tuple[TableSchema, ...]
    figures: tuple[FigureGraph, ...]
    texts: tuple[TextEvidence, ...]

    def tables_of_kind(self, kind: str) -> tuple[TableSchema, ...]:
        return tuple(table for table in self.tables if table.kind == kind)

    def kind_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for table in self.tables:
            counts[table.kind] = counts.get(table.kind, 0) + 1
        return counts


@dataclass(frozen=True)
class FocusedView:
    """The minimal evidence subset relevant to one atomic claim."""

    claim_id: str
    claim_type: str
    evidence_id: str
    evidence_kind: str
    table_kind: str = ""
    row_keys: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    cells: tuple[tuple[str, str], ...] = ()
    statements: tuple[str, ...] = ()
    node_ids: tuple[str, ...] = ()
    node_labels: tuple[str, ...] = ()
    figure_edges: tuple[str, ...] = ()


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _hit(anchors: tuple[str, ...], text: str) -> bool:
    haystack = _norm_text(text)
    if len(haystack) < 2:
        return False
    return any(
        anchor and (anchor in haystack or haystack in anchor) for anchor in anchors
    )


def _enum_score(text: str) -> int:
    return len(_ENUM_SEPARATOR.findall(text))


def claim_type(claim: StructuredClaim) -> str:
    """Classify one atomic claim into its focused-view routing type."""
    text = claim.text
    if _IDENTIFIER_TOKEN.search(text) or "标识符" in text:
        return "identifier"
    if _EXCEPTION_HINT.search(text):
        return "exception"
    if _DIGIT.search(text) and _NUMERIC_HINT.search(text):
        return "numeric"
    if claim.structure == "step" or _STEP_HINT.search(text):
        return "step"
    if _enum_score(text) >= 2 or (_enum_score(text) >= 1 and _ENUM_HINT.search(text)):
        return "enumeration"
    return "generic"


def _claim_anchors(claim: StructuredClaim) -> tuple[str, ...]:
    anchors: list[str] = []

    def add(term: str) -> None:
        value = _norm_text(term)
        if _anchor_ok(value) and value not in anchors:
            anchors.append(value)

    if claim.scope_hint:
        add(claim.scope_hint)
    id_values = [
        _norm_text(match.group(0)) for match in _IDENTIFIER_TOKEN.finditer(claim.text)
    ]
    for value in id_values:
        add(value)
    for match in _SECTION_NUMBER.finditer(claim.text):
        add(match.group(0))
    for run in _ANCHOR_RUN.findall(claim.text):
        value = _norm_text(run)
        if any(value != other and value in other for other in id_values):
            continue
        add(run)
    return tuple(anchors)


def _anchor_ok(value: str) -> bool:
    if not value:
        return False
    if value.isascii():
        has_digit = any(char.isdigit() for char in value)
        return len(value) >= 4 or (len(value) >= 3 and has_digit)
    return len(value) >= 2


def _table_grid(table_html: str) -> list[list[str]]:
    """Rebuild the physical cell grid, honoring rowspan/colspan merges."""
    grid: list[list[str]] = []
    active: dict[int, str] = {}
    remaining: dict[int, int] = {}

    def consume(col: int, row: list[str]) -> int:
        while col in active:
            row.append(active[col])
            remaining[col] -= 1
            if remaining[col] <= 0:
                active.pop(col, None)
                remaining.pop(col, None)
            col += 1
        return col

    for row_match in _TR.finditer(table_html):
        row: list[str] = []
        col = 0
        for cell in _CELL_TAG.finditer(row_match.group(1)):
            col = consume(col, row)
            attrs = dict(_ATTR.findall(cell.group("attrs")))
            text = _strip_tags(cell.group("body"))
            try:
                rowspan = max(int(attrs.get("rowspan", "1")), 1)
                colspan = max(int(attrs.get("colspan", "1")), 1)
            except ValueError:
                rowspan, colspan = 1, 1
            row.append(text)
            row.extend("" for _ in range(1, colspan))
            if rowspan > 1:
                for offset in range(colspan):
                    active[col + offset] = text
                    remaining[col + offset] = rowspan - 1
            col += colspan
        col = consume(col, row)
        grid.append(row)
    return grid


def _norm_header(raw: str) -> str:
    text = re.sub(r"（[^）]*）", "", _strip_tags(raw))
    return re.sub(r"[\s*]+", "", text)


def _caption_of(text: str) -> str:
    start = text.find("<table")
    end = text.rfind("</table>")
    prefix = text[:start] if start >= 0 else ""
    suffix = text[end + len("</table>"):] if end >= 0 else ""
    lines = [line for chunk in (prefix, suffix)
             for line in (re.sub(r"\s+", " ", part).strip()
                          for part in chunk.splitlines()) if line]
    return " ".join(lines)


def _classify_table(
        headers: list[str], raw_text: str, caption: str,
        pack: RulePack) -> str:
    """按rule pack的classify_order执行表头签名判定(首个命中表型)."""
    return pack.classify_table(frozenset(headers), headers, caption, raw_text)


def _compile_column_table(
        grid: list[list[str]], kind: str, pack: RulePack,
) -> tuple[tuple[str, ...], tuple[TableRow, ...]]:
    if not grid:
        return (), ()
    spec = pack.table_spec(kind)
    columns = tuple(
        spec.canon_map.get(_norm_header(cell), _norm_header(cell))
        for cell in grid[0])
    col_index: dict[str, int] = {}
    for position, column in enumerate(columns):
        col_index.setdefault(column, position)
    if kind == TRACE_TABLE:
        forward = bool(columns) and columns[0].startswith(
            spec.direction_first_column_prefix)
        key_columns = spec.trace_key_columns[
            "forward" if forward else "reverse"]
    else:
        key_columns = spec.key_columns
    key_positions = [col_index[name] for name in key_columns if name in col_index]
    rows: list[TableRow] = []
    for row_number, raw_row in enumerate(grid[1:], start=2):
        if not any(cell for cell in raw_row):
            continue
        cells = tuple(
            (columns[position], raw_row[position])
            for position in range(min(len(columns), len(raw_row)))
            if raw_row[position]
        )
        key = ""
        for position in key_positions:
            if position < len(raw_row) and raw_row[position]:
                key = raw_row[position]
                break
        if not key:
            key = next((cell for cell in raw_row if len(cell) >= 2), "")
        rows.append(TableRow(row_index=row_number, key=key, field="", cells=cells))
    return columns, tuple(rows)


def _canon_field(field: str, spec: UseCaseFields) -> str:
    lowered = field.lower()
    if lowered.startswith("use"):
        return "Use Case名称"
    if lowered.startswith("actor"):
        return "Actors"
    return spec.field_canon.get(field, field)


def _compile_use_case(
        rows: list[list[str]], spec: TableSchemaSpec,
) -> tuple[TableRow, ...]:
    fields = spec.use_case_fields
    if fields is None:
        return ()
    name_rx = compile_pattern(fields.name_pattern)
    actors_rx = compile_pattern(fields.actors_pattern)
    field_rx = compile_pattern(fields.field_pattern)
    flow_header_rx = compile_pattern(fields.flow_header_pattern)
    subheader_rx = compile_pattern(fields.subheader_pattern)
    flow_subcolumns = spec.flow_subcolumns
    compiled: list[TableRow] = []
    use_case = ""
    in_flow = False
    for row_number, cells in enumerate(rows, start=1):
        if not cells:
            continue
        name_match = name_rx.match(cells[0])
        if name_match:
            use_case = name_match.group("name").strip()
            in_flow = False
            compiled.append(TableRow(
                row_number, use_case, "Use Case名称", (("Use Case名称", use_case),)))
            if len(cells) >= 2:
                actors_match = actors_rx.match(cells[1])
                if actors_match:
                    compiled.append(TableRow(
                        row_number, use_case, "Actors",
                        (("Actors", actors_match.group("actors").strip()),)))
            continue
        field_match = field_rx.match(cells[0])
        if field_match and len(cells) <= 2:
            field = _canon_field(field_match.group("field"), fields)
            value = field_match.group("value").strip()
            if not value and len(cells) == 2:
                value = cells[1].strip()
            in_flow = False
            if value:
                compiled.append(TableRow(row_number, use_case, field, ((field, value),)))
            continue
        if flow_header_rx.match(cells[0]) and len(cells) == 1:
            in_flow = True
            continue
        if in_flow and subheader_rx.match(cells[0]):
            continue
        if in_flow:
            values = tuple(cells[: len(flow_subcolumns)])
            values = values + ("",) * (len(flow_subcolumns) - len(values))
            pairs = tuple(
                (column, value) for column, value in zip(flow_subcolumns, values)
                if value
            )
            if pairs:
                compiled.append(TableRow(row_number, use_case, "主事件流", pairs))
    return tuple(compiled)


def _compile_table(block: RetrievedEvidence, pack: RulePack) -> TableSchema:
    raw_text = block.text
    caption = _caption_of(raw_text)
    grid = _table_grid(raw_text)
    headers = [_norm_header(cell) for cell in grid[0]] if grid else []
    kind = _classify_table(headers, raw_text, caption, pack)
    if kind == USE_CASE_TABLE:
        use_case_spec = pack.table_spec(USE_CASE_TABLE)
        columns = use_case_spec.columns
        rows = _compile_use_case(_table_rows(raw_text), use_case_spec)
    else:
        columns, rows = _compile_column_table(grid, kind, pack)
    direction = ""
    if kind == TRACE_TABLE and columns:
        trace_spec = pack.table_spec(TRACE_TABLE)
        direction = (
            "forward" if columns[0].startswith(
                trace_spec.direction_first_column_prefix) else "reverse")
    return TableSchema(
        evidence_id=block.evidence_id,
        kind=kind,
        caption=caption,
        columns=columns,
        rows=rows,
        direction=direction,
    )


def _mermaid_kind(code: str) -> str:
    stripped = code.strip()
    first = stripped.splitlines()[0].strip() if stripped else ""
    if first.startswith(("flowchart", "graph")):
        return "flowchart"
    if first.startswith("stateDiagram"):
        return "state"
    return "unknown"


def _clean_label(raw: str) -> str:
    return raw.strip().strip('"').strip()


def parse_mermaid(code: str) -> tuple[tuple[FigureNode, ...], tuple[FigureEdge, ...]]:
    """Parse Mermaid text into structured node/edge lists."""
    nodes: dict[str, FigureNode] = {}
    edges: list[FigureEdge] = []
    for line in code.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("flowchart", "graph", "stateDiagram", "%%")):
            continue
        node_match = _MM_NODE.match(line)
        if node_match:
            node_id = node_match.group("id")
            label, shape = "", "process"
            for group_name, shape_name in (
                ("stadium", "terminal"),
                ("process", "process"),
                ("decision", "decision"),
                ("round", "data"),
            ):
                value = node_match.group(group_name)
                if value is not None:
                    label, shape = _clean_label(value), shape_name
                    break
            if node_id not in nodes:
                nodes[node_id] = FigureNode(node_id=node_id, label=label, shape=shape)
            continue
        edge_match = _MM_EDGE.match(line)
        if edge_match:
            src = edge_match.group("src")
            dst = edge_match.group("dst")
            arrow = edge_match.group("arrow")
            edges.append(FigureEdge(
                src_id=src,
                dst_id=dst,
                label=_clean_label(edge_match.group("label") or ""),
                directed=arrow != "---",
            ))
            for node_id in (src, dst):
                nodes.setdefault(
                    node_id, FigureNode(node_id=node_id, label="", shape="process"))
    return tuple(nodes.values()), tuple(edges)


def _block_text(item: dict[str, object]) -> str:
    parts: list[str] = []
    text = str(item.get("text", "") or "").strip()
    if text:
        parts.append(text)
    list_items = item.get("list_items", [])
    if isinstance(list_items, list):
        parts.extend(str(part).strip() for part in list_items if str(part).strip())
    body = str(item.get("table_body", "") or "").strip()
    if body:
        parts.append(body)
    captions = item.get("table_caption", [])
    if isinstance(captions, list):
        parts.extend(str(part).strip() for part in captions if str(part).strip())
    elif captions:
        parts.append(str(captions).strip())
    return "\n".join(parts)


def load_content_list_evidence(doc_glob: str = "04*") -> tuple[RetrievedEvidence, ...]:
    """Load MinerU content_list blocks (text/list/table) as evidence blocks."""
    paths = sorted(BASE.glob(CONTENT_LIST_GLOB.format(doc_glob)))
    if not paths:
        raise FileNotFoundError(f"no content_list.json matches: {doc_glob}")
    blocks: list[RetrievedEvidence] = []
    for source in paths:
        doc_id = source.stem.removesuffix("_content_list")
        prefix = doc_id[:2]
        items = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError(f"content_list must be a JSON list: {source}")
        section = ""
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type", "other"))
            if kind in {"index", "footer", "image"}:
                continue
            text = _block_text(item)
            if not text:
                continue
            heading = str(item.get("text", "") or "")
            if item.get("text_level") and re.match(r"^\d+(?:\.\d+)*\b", heading):
                section = heading
            blocks.append(RetrievedEvidence(
                evidence_id=f"{prefix}-blk-{index:06d}",
                text=text,
                source_type={"text": "text", "list": "text", "table": "table"}.get(
                    kind, "other"),
                source_ref=SourceRef(
                    doc_id=doc_id,
                    section=section,
                    page=item.get("page_idx") if isinstance(item.get("page_idx"), int)
                    else None,
                    block_id=f"block-{index:06d}",
                ),
                scope_id=f"{doc_id}:block-{index:06d}",
                extraction_method="mineru_content_list",
                extraction_confidence=1.0,
            ))
    return tuple(blocks)


def load_figure_evidence(
    doc_prefix: str = "04", path: Path | None = None,
) -> tuple[RetrievedEvidence, ...]:
    """Load the anchor_v2 Mermaid exports of one document as figure evidence."""
    source = path or MERMAID_EXPORT_PATH
    data = json.loads(source.read_text(encoding="utf-8"))
    blocks: list[RetrievedEvidence] = []
    for index, key in enumerate(
            sorted(key for key in data if str(key).startswith(doc_prefix))):
        entry = data[key]
        key_text = str(key)
        doc_id = str(entry.get("doc") or key_text.split(":", 1)[0])
        embed = str(entry.get("embed") or key_text)
        blocks.append(RetrievedEvidence(
            evidence_id=f"{doc_prefix}-fig-{index:03d}",
            text=str(entry.get("mermaid", "")),
            source_type="figure",
            source_ref=SourceRef(doc_id=doc_id, block_id=key_text, region_id=embed),
            scope_id=f"{doc_id}:{embed}",
            extraction_method="anchor_v2_mermaid_export",
            extraction_confidence=1.0,
        ))
    return tuple(blocks)


def compile_evidence(
        evidence: tuple[RetrievedEvidence, ...],
        rulepack: RulePack | None = None,
) -> EvidenceSchema:
    """Compile frozen evidence blocks into the typed EvidenceSchema.

    ``rulepack`` selects the table-schema configuration (signatures / canon
    maps / key columns / column profiles); the default (None) lazily loads
    ``srs_gjb_v1`` — identical to the pre-rulepack hardcoded behavior.
    """
    pack = rulepack or default_rulepack()
    tables: list[TableSchema] = []
    texts: list[TextEvidence] = []
    figures: list[FigureGraph] = []
    for block in evidence:
        if block.source_type == "figure":
            nodes, edges = parse_mermaid(block.text)
            figures.append(FigureGraph(
                figure_id=block.evidence_id,
                diagram_type=_mermaid_kind(block.text),
                nodes=nodes,
                edges=edges,
                mermaid=block.text,
            ))
        elif block.source_type == "table" or "<table" in block.text:
            tables.append(_compile_table(block, pack))
        else:
            sentences = tuple(
                statement.text
                for statement in _linearize_text(block.text, block.evidence_id)
            )
            texts.append(TextEvidence(evidence_id=block.evidence_id, sentences=sentences))
    return EvidenceSchema(
        tables=tuple(tables), figures=tuple(figures), texts=tuple(texts))


def _key_hit(anchors: tuple[str, ...], key: str) -> bool:
    if not key:
        return False
    return _hit(anchors, key)


def _match_rows(table: TableSchema, anchors: tuple[str, ...]) -> list[TableRow]:
    keyed = [row for row in table.rows if _key_hit(anchors, row.key)]
    if keyed:
        return keyed
    return [
        row for row in table.rows
        if any(_hit(anchors, value) for _column, value in row.cells)
    ]


def _focused_columns(
        table: TableSchema, ctype: str, pack: RulePack) -> tuple[str, ...]:
    profile = pack.table_spec(table.kind).profile(ctype)
    if not profile:
        return table.columns
    selected = tuple(column for column in table.columns if column in profile)
    return selected or table.columns


def _scope_filter(rows: list[TableRow], claim: StructuredClaim) -> list[TableRow]:
    scope = _norm_text(claim.scope_hint) if claim.scope_hint else ""
    if len(scope) < 2 or not rows:
        return rows
    scoped = [row for row in rows if _hit((scope,), row.key)]
    return scoped or rows


def _use_case_rows(
    table: TableSchema, claim: StructuredClaim, ctype: str,
    anchors: tuple[str, ...],
) -> list[TableRow]:
    if ctype == "exception":
        return _scope_filter(
            [row for row in table.rows if row.field.startswith("异常流")], claim)
    if ctype == "step":
        return _scope_filter(
            [row for row in table.rows if row.field == "主事件流"], claim)
    keyed = [row for row in table.rows if _key_hit(anchors, row.key)]
    if keyed:
        hits = [
            row for row in keyed
            if _hit(anchors, row.field)
            or any(_hit(anchors, value) for _column, value in row.cells)
        ]
        return hits or keyed
    return [
        row for row in table.rows
        if _hit(anchors, row.field)
        or any(_hit(anchors, value) for _column, value in row.cells)
    ]


def _focus_table(
        table: TableSchema, claim: StructuredClaim, ctype: str,
        anchors: tuple[str, ...], pack: RulePack,
) -> FocusedView | None:
    if table.kind == USE_CASE_TABLE:
        rows = _use_case_rows(table, claim, ctype, anchors)
        columns = tuple(
            dict.fromkeys(column for row in rows for column, _value in row.cells))
        cells = tuple(
            (column, value) for row in rows for column, value in row.cells)
    else:
        rows = _match_rows(table, anchors)
        if not rows:
            return None
        columns = _focused_columns(table, ctype, pack)
        cells = tuple(
            (column, value)
            for row in rows
            for column, value in row.cells
            if column in columns
        )
    if not rows or not cells:
        return None
    row_keys = tuple(dict.fromkeys(row.key for row in rows if row.key))
    return FocusedView(
        claim_id=claim.claim_id,
        claim_type=ctype,
        evidence_id=table.evidence_id,
        evidence_kind="table",
        table_kind=table.kind,
        row_keys=row_keys,
        columns=columns,
        cells=cells,
    )


def _focus_text(
    text_evidence: TextEvidence, claim: StructuredClaim, ctype: str,
    anchors: tuple[str, ...],
) -> FocusedView | None:
    hits = [
        sentence for sentence in text_evidence.sentences if _hit(anchors, sentence)
    ]
    if ctype == "enumeration" and hits:
        enum_hits = [
            sentence for sentence in hits
            if _enum_score(sentence) >= 2 or _ENUM_HINT.search(sentence)
        ]
        if enum_hits:
            hits = enum_hits
    if not hits:
        return None
    return FocusedView(
        claim_id=claim.claim_id,
        claim_type=ctype,
        evidence_id=text_evidence.evidence_id,
        evidence_kind="text",
        statements=tuple(hits),
    )


def _focus_figure(
    graph: FigureGraph, claim: StructuredClaim, ctype: str,
    anchors: tuple[str, ...],
) -> FocusedView | None:
    matched = [node for node in graph.nodes if node.label and _hit(anchors, node.label)]
    if not matched:
        return None
    matched_ids = {node.node_id for node in matched}
    label_of = {node.node_id: node.label for node in graph.nodes}
    edge_lines: list[str] = []
    for edge in graph.edges:
        if edge.src_id not in matched_ids or edge.dst_id not in matched_ids:
            continue
        src = label_of.get(edge.src_id, edge.src_id)
        dst = label_of.get(edge.dst_id, edge.dst_id)
        arrow = "-->" if edge.directed else "---"
        if edge.label:
            edge_lines.append(f"{src} {arrow}|{edge.label}| {dst}")
        else:
            edge_lines.append(f"{src} {arrow} {dst}")
    return FocusedView(
        claim_id=claim.claim_id,
        claim_type=ctype,
        evidence_id=graph.figure_id,
        evidence_kind="figure",
        node_ids=tuple(node.node_id for node in matched),
        node_labels=tuple(node.label for node in matched),
        figure_edges=tuple(edge_lines),
    )


def focus_views(
        schema: EvidenceSchema, claims: list[StructuredClaim],
        rulepack: RulePack | None = None,
) -> list[FocusedView]:
    """Build the focused view of every claim against every evidence block.

    ``rulepack`` supplies the column profiles (default None → srs_gjb_v1);
    it must match the pack used to compile ``schema``.
    """
    pack = rulepack or default_rulepack()
    views: list[FocusedView] = []
    for claim in claims:
        ctype = claim_type(claim)
        anchors = _claim_anchors(claim)
        for table in schema.tables:
            view = _focus_table(table, claim, ctype, anchors, pack)
            if view:
                views.append(view)
        for text_evidence in schema.texts:
            view = _focus_text(text_evidence, claim, ctype, anchors)
            if view:
                views.append(view)
        for graph in schema.figures:
            view = _focus_figure(graph, claim, ctype, anchors)
            if view:
                views.append(view)
    return views


def compile_and_focus(
        evidence: tuple[RetrievedEvidence, ...], claims: list[StructuredClaim],
        rulepack: RulePack | None = None,
) -> tuple[EvidenceSchema, list[FocusedView]]:
    """Compile the schema and build every claim's focused views in one call."""
    pack = rulepack or default_rulepack()
    schema = compile_evidence(evidence, pack)
    return schema, focus_views(schema, claims, pack)


__all__ = [
    "CAPABILITY_TABLE",
    "EvidenceSchema",
    "FocusedView",
    "FigureEdge",
    "FigureGraph",
    "FigureNode",
    "GENERIC_TABLE",
    "INTERFACE_TABLE",
    "QUALIFICATION_TABLE",
    "TableSchema",
    "TableRow",
    "TextEvidence",
    "TRACE_TABLE",
    "USE_CASE_TABLE",
    "VALUE_DOMAIN_TABLE",
    "claim_type",
    "compile_and_focus",
    "compile_evidence",
    "focus_views",
    "load_content_list_evidence",
    "load_figure_evidence",
    "parse_mermaid",
]
