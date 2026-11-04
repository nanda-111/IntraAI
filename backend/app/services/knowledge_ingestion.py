"""知识导入与结构化：文件解析、校验、草稿生成。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from html.parser import HTMLParser

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.printer.fault_taxonomy import FAULT_CATEGORIES
from app.models.repair_knowledge import KnowledgeDocument, KnowledgeSource, RepairKnowledge
from app.services.document_processor import extract_text_with_pages, split_document

ALLOWED_IMPORT_TYPES = {"pdf", "docx", "txt", "md", "html", "htm", "json", "jsonl"}
MAX_IMPORT_SIZE = 20 * 1024 * 1024


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _new_doc_key() -> str:
    return f"rk_{uuid.uuid4().hex[:12]}"


def _normalize_steps(raw) -> list[dict]:
    steps = []
    if not raw:
        return steps
    for index, item in enumerate(raw, start=1):
        if isinstance(item, dict):
            steps.append(
                {
                    "step_no": item.get("step_no", index),
                    "instruction": str(item.get("instruction", "")).strip(),
                    "risk_level": item.get("risk_level", "L1"),
                    "expected_result": item.get("expected_result", ""),
                }
            )
        elif str(item).strip():
            steps.append(
                {
                    "step_no": index,
                    "instruction": str(item).strip(),
                    "risk_level": "L1",
                    "expected_result": "",
                }
            )
    return [step for step in steps if step["instruction"]]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip = True
        elif tag in {"p", "br", "div", "li", "h1", "h2", "h3", "tr"}:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self._parts)).strip()


def extract_html_text(path: str) -> str:
    parser = _HTMLTextExtractor()
    with open(path, encoding="utf-8", errors="ignore") as handle:
        parser.feed(handle.read())
    return parser.text()


def save_upload(filename: str, content: bytes) -> tuple[str, str, str]:
    """保存原始文件，返回 (路径, 扩展名, checksum)。"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMPORT_TYPES:
        raise ValueError(f"不支持的文件类型: {ext}")
    if len(content) > MAX_IMPORT_SIZE:
        raise ValueError("文件超过 20MB 限制")
    target_dir = os.path.join(settings.UPLOAD_DIR, "knowledge")
    os.makedirs(target_dir, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_\-.一-鿿]", "_", filename)
    path = os.path.join(target_dir, f"{uuid.uuid4().hex[:8]}_{safe_name}")
    with open(path, "wb") as handle:
        handle.write(content)
    return path, ext, _sha256_bytes(content)


def _validate_meta(brand_code: str | None, model_scope: str | None) -> None:
    if not model_scope:
        raise ValueError("缺少适用范围 model_scope")
    if not brand_code:
        raise ValueError("缺少品牌 brand_code")


def _make_knowledge(
    *,
    doc_id: str,
    document_id: int | None,
    source_id: int | None,
    brand_code: str,
    series: str | None,
    model_scope: str,
    region_scope: str,
    code_system: str | None,
    fault_category: str,
    fault_code: str | None,
    title: str,
    symptom: str | None,
    possible_causes: list,
    steps: list[dict],
    safety_warnings: list,
    risk_level: str,
    source_type: str,
    authority_level: str,
    review_status: str,
    preconditions: list | None = None,
    expected_result: str | None = None,
    verification_method: str | None = None,
) -> RepairKnowledge:
    if fault_category not in FAULT_CATEGORIES:
        fault_category = "other"
    item = RepairKnowledge(
        doc_id=doc_id,
        document_id=document_id,
        source_id=source_id,
        brand_code=brand_code.upper() if brand_code else None,
        series=series,
        model_scope=model_scope,
        region_scope=region_scope or "CN",
        code_system=code_system,
        fault_category=fault_category,
        fault_code=fault_code,
        title=title[:220],
        symptom=symptom,
        possible_causes=possible_causes or [],
        preconditions=preconditions or [],
        steps=steps,
        expected_result=expected_result,
        verification_method=verification_method,
        safety_warnings=safety_warnings or [],
        risk_level=risk_level if risk_level in {"L1", "L2", "L3"} else "L1",
        source_type=source_type,
        authority_level=authority_level,
        review_status=review_status,
    )
    item.content_hash = _sha256_text(_knowledge_signature(item))
    return item


def _knowledge_signature(item: RepairKnowledge) -> str:
    payload = {
        "model_scope": item.model_scope,
        "fault_category": item.fault_category,
        "title": item.title,
        "symptom": item.symptom,
        "steps": item.steps,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def import_file(
    db: Session,
    *,
    source: KnowledgeSource,
    filename: str,
    content: bytes,
    brand_code: str,
    model_scope: str,
    region_scope: str = "CN",
    series: str | None = None,
    fault_category: str = "other",
    fault_code: str | None = None,
    code_system: str | None = None,
    source_type: str | None = None,
    authority_level: str | None = None,
    risk_level: str = "L1",
    uploaded_by: int | None = None,
) -> dict:
    """保存并解析文件，生成待审核知识草稿。"""
    _validate_meta(brand_code, model_scope)
    path, ext, checksum = save_upload(filename, content)

    existing = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.checksum == checksum, KnowledgeDocument.source_id == source.id)
        .first()
    )
    if existing:
        return {
            "duplicate": True,
            "document_id": existing.id,
            "created": 0,
            "message": "相同来源的同一文件已导入，已跳过重复导入。",
        }

    document = KnowledgeDocument(
        source_id=source.id,
        title=filename,
        file_name=filename,
        file_path=path,
        file_type=ext,
        checksum=checksum,
        parse_status="parsing",
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.flush()

    created_items: list[RepairKnowledge] = []
    try:
        if ext in {"json", "jsonl"}:
            created_items = _import_structured(
                db,
                document=document,
                source=source,
                path=path,
                ext=ext,
                brand_code=brand_code,
                model_scope=model_scope,
                region_scope=region_scope,
                series=series,
                source_type=source_type or source.source_type,
                authority_level=authority_level or source.authority_level,
            )
        else:
            created_items = _import_document(
                db,
                document=document,
                source=source,
                path=path,
                ext=ext,
                brand_code=brand_code,
                model_scope=model_scope,
                region_scope=region_scope,
                series=series,
                fault_category=fault_category,
                fault_code=fault_code,
                code_system=code_system,
                source_type=source_type or source.source_type,
                authority_level=authority_level or source.authority_level,
                risk_level=risk_level,
            )
        document.parse_status = "parsed"
        document.chunk_count = len(created_items)
        db.commit()
    except Exception as exc:
        document.parse_status = "failed"
        document.parse_error = str(exc)
        db.commit()
        return {
            "duplicate": False,
            "document_id": document.id,
            "created": 0,
            "parse_status": "failed",
            "message": str(exc),
        }

    return {
        "duplicate": False,
        "document_id": document.id,
        "created": len(created_items),
        "parse_status": "parsed",
        "items": [
            {"doc_id": item.doc_id, "title": item.title, "review_status": item.review_status}
            for item in created_items
        ],
    }


def _import_structured(
    db: Session,
    *,
    document: KnowledgeDocument,
    source: KnowledgeSource,
    path: str,
    ext: str,
    brand_code: str,
    model_scope: str,
    region_scope: str,
    series: str | None,
    source_type: str,
    authority_level: str,
) -> list[RepairKnowledge]:
    with open(path, encoding="utf-8", errors="ignore") as handle:
        raw = handle.read()
    if ext == "jsonl":
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        parsed = json.loads(raw)
        records = parsed if isinstance(parsed, list) else [parsed]

    items: list[RepairKnowledge] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        item = _make_knowledge(
            doc_id=record.get("doc_id") or _new_doc_key(),
            document_id=document.id,
            source_id=source.id,
            brand_code=(record.get("brand_code") or brand_code).upper(),
            series=record.get("series") or series,
            model_scope=record.get("model_scope") or model_scope,
            region_scope=record.get("region_scope") or region_scope,
            code_system=record.get("code_system"),
            fault_category=record.get("fault_category") or "other",
            fault_code=record.get("fault_code"),
            title=record.get("title") or record.get("symptom") or "未命名知识",
            symptom=record.get("symptom"),
            possible_causes=record.get("possible_causes") or [],
            preconditions=record.get("preconditions") or [],
            steps=_normalize_steps(record.get("steps")),
            expected_result=record.get("expected_result"),
            verification_method=record.get("verification_method"),
            safety_warnings=record.get("safety_warnings") or [],
            risk_level=record.get("risk_level", "L1"),
            source_type=record.get("source_type") or source_type,
            authority_level=record.get("authority_level") or authority_level,
            review_status="pending",
        )
        db.add(item)
        items.append(item)
    db.flush()
    return items


def _import_document(
    db: Session,
    *,
    document: KnowledgeDocument,
    source: KnowledgeSource,
    path: str,
    ext: str,
    brand_code: str,
    model_scope: str,
    region_scope: str,
    series: str | None,
    fault_category: str,
    fault_code: str | None,
    code_system: str | None,
    source_type: str,
    authority_level: str,
    risk_level: str,
) -> list[RepairKnowledge]:
    if ext in {"html", "htm"}:
        text = extract_html_text(path)
        pages = [(text, 1)] if text else []
    else:
        pages = extract_text_with_pages(path, ext)
    if not pages:
        raise ValueError("未能从文件中解析出文本")
    document.extracted_text = "\n".join(text for text, _ in pages)[:200000]

    chunks = split_document("", chunk_size=500, overlap=50, pages=pages)
    if not chunks:
        raise ValueError("文本切片为空")

    items: list[RepairKnowledge] = []
    for index, chunk in enumerate(chunks, start=1):
        body = chunk.get("text", "").strip()
        if not body:
            continue
        title_line = body.splitlines()[0][:80]
        item = _make_knowledge(
            doc_id=_new_doc_key(),
            document_id=document.id,
            source_id=source.id,
            brand_code=brand_code,
            series=series,
            model_scope=model_scope,
            region_scope=region_scope,
            code_system=code_system,
            fault_category=fault_category,
            fault_code=fault_code,
            title=f"{os.path.splitext(document.file_name or '资料')[0]} · {index} {title_line}",
            symptom=body,
            possible_causes=[],
            steps=[],  # 原文片段尚未结构化，审核时需补充步骤后才会进入检索
            safety_warnings=["请对照官方资料核对步骤后再发布。"],
            risk_level=risk_level,
            source_type=source_type,
            authority_level=authority_level,
            review_status="pending",
        )
        db.add(item)
        items.append(item)
    db.flush()
    return items


def create_knowledge_direct(db: Session, payload: dict) -> RepairKnowledge:
    """管理员手工创建结构化知识条目。"""
    item = _make_knowledge(
        doc_id=_new_doc_key(),
        document_id=None,
        source_id=payload.get("source_id"),
        brand_code=payload.get("brand_code") or "",
        series=payload.get("series"),
        model_scope=payload.get("model_scope") or "",
        region_scope=payload.get("region_scope") or "CN",
        code_system=payload.get("code_system"),
        fault_category=payload.get("fault_category") or "other",
        fault_code=payload.get("fault_code"),
        title=payload.get("title") or "未命名知识",
        symptom=payload.get("symptom"),
        possible_causes=payload.get("possible_causes") or [],
        preconditions=payload.get("preconditions") or [],
        steps=_normalize_steps(payload.get("steps")),
        expected_result=payload.get("expected_result"),
        verification_method=payload.get("verification_method"),
        safety_warnings=payload.get("safety_warnings") or [],
        risk_level=payload.get("risk_level", "L1"),
        source_type=payload.get("source_type") or "manual",
        authority_level=payload.get("authority_level") or "C",
        review_status=payload.get("review_status", "draft"),
    )
    db.add(item)
    db.flush()
    return item
