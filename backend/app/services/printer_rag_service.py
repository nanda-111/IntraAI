"""型号感知 RAG 服务：硬过滤 + 向量/BM25 混合召回 + RRF + 重排序 + 证据校验。

检索顺序（与设计文档一致）：
1. 识别并确认 brand、model_id、region、fault_category 等过滤条件；
2. 先做审核状态、型号范围、地区范围的硬过滤；
3. Chroma 向量召回 + BM25 关键词召回；
4. RRF 融合去重；
5. CrossEncoder 重排序，保留 Top 3~5；
6. Evidence Gate 校验适用范围、来源等级、步骤完整性和安全标记；
7. 只基于通过校验的证据生成回答，输出引用。
"""

from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.printer import registry
from app.domains.printer.fault_taxonomy import category_label, classify_symptom
from app.domains.printer.safety_policy import (
    EVIDENCE_INSUFFICIENT_NOTICE,
    filter_self_service_steps,
    is_high_risk_request,
    refusal_answer,
)
from app.models.chat_session import RetrievalLog
from app.models.printer_brand import PrinterBrand, ProductModel
from app.models.repair_knowledge import KnowledgeSource, RepairKnowledge
from app.services.embedding import get_embeddings
from app.services.llm import chat_completion, chat_completion_stream
from app.services.vector_store import _tokenize_chinese

logger = logging.getLogger(__name__)

REVIEW_OK = ("approved", "published")
COLLECTION_BY_SOURCE = {
    "official": "printer_official_knowledge",
    "faq": "printer_verified_faq",
    "manual": "printer_verified_faq",
    "community": "printer_community_cases",
}
RRF_K = 60
VECTOR_CANDIDATES = 30
BM25_CANDIDATES = 30
RERANK_TOP_K = 5


# ==================== 索引管理 ====================


def _get_chroma_client():
    import chromadb

    return chromadb.PersistentClient(path=settings.CHROMA_DIR)


def _get_collection(source_type: str):
    client = _get_chroma_client()
    name = COLLECTION_BY_SOURCE.get(source_type, "printer_official_knowledge")
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def knowledge_text(item: RepairKnowledge) -> str:
    """向量化主体：维修知识正文，而不是 URL。"""
    parts = [f"型号适用范围：{item.model_scope}", f"故障现象：{item.symptom or item.title}"]
    if item.possible_causes:
        parts.append("可能原因：" + "；".join(str(c) for c in item.possible_causes))
    if item.preconditions:
        parts.append("前置条件：" + "；".join(str(c) for c in item.preconditions))
    steps = [str(step.get("instruction", "")) for step in (item.steps or []) if step]
    if steps:
        parts.append("操作步骤：" + "；".join(f"{i + 1}. {s}" for i, s in enumerate(steps)))
    if item.expected_result:
        parts.append(f"预期结果：{item.expected_result}")
    if item.verification_method:
        parts.append(f"验证方法：{item.verification_method}")
    if item.safety_warnings:
        parts.append("安全提示：" + "；".join(str(w) for w in item.safety_warnings))
    return "\n".join(parts)


def knowledge_metadata(db: Session, item: RepairKnowledge) -> dict:
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == item.source_id).first()
    return {
        "doc_id": item.doc_id,
        "title": item.title,
        "brand_code": item.brand_code or "",
        "series": item.series or "",
        "model_scope": item.model_scope or "",
        "region_scope": item.region_scope or "CN",
        "code_system": item.code_system or "",
        "fault_category": item.fault_category,
        "fault_code": item.fault_code or "",
        "source_type": item.source_type,
        "authority_level": item.authority_level,
        "review_status": item.review_status,
        "source_key": source.source_key if source else "",
        "source_url": source.url if source else "",
        "version": item.version or "1.0",
        "content_hash": item.content_hash or "",
        "risk_level": item.risk_level or "L1",
    }


def index_knowledge(db: Session, item: RepairKnowledge) -> bool:
    """把单条已审核知识写入对应 Chroma collection（尽力而为，失败不阻断业务）。"""
    if item.review_status not in REVIEW_OK:
        return False
    try:
        collection = _get_collection(item.source_type)
        text = knowledge_text(item)
        embedding = get_embeddings([text])[0]
        collection.upsert(
            ids=[item.doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[knowledge_metadata(db, item)],
        )
        item.index_version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        item.indexed_at = datetime.now(UTC).replace(tzinfo=None)
        db.add(item)
        return True
    except Exception as exc:  # 索引失败记录错误，检索会回退到数据库关键词召回
        logger.warning("索引知识失败 %s: %s", item.doc_id, exc)
        return False


def remove_from_index(item: RepairKnowledge) -> None:
    try:
        collection = _get_collection(item.source_type)
        collection.delete(ids=[item.doc_id])
    except Exception as exc:
        logger.debug("删除索引失败 %s: %s", item.doc_id, exc)


def reindex_all(db: Session) -> dict:
    items = db.query(RepairKnowledge).filter(RepairKnowledge.review_status.in_(REVIEW_OK)).all()
    indexed = sum(1 for item in items if index_knowledge(db, item))
    db.commit()
    return {"total": len(items), "indexed": indexed, "failed": len(items) - indexed}


def index_status() -> dict:
    result = {}
    for source_type, name in COLLECTION_BY_SOURCE.items():
        try:
            collection = _get_collection(source_type)
            result[name] = {"count": collection.count(), "source_type": source_type}
        except Exception as exc:
            result[name] = {"count": 0, "error": str(exc), "source_type": source_type}
    return result


# ==================== 检索 ====================


def _db_candidates(
    db: Session,
    brand_code: str | None,
    model: ProductModel | None,
    region: str,
    fault_category: str | None,
    include_community: bool,
) -> list[RepairKnowledge]:
    query = db.query(RepairKnowledge).filter(RepairKnowledge.review_status.in_(REVIEW_OK))
    if brand_code:
        query = query.filter(RepairKnowledge.brand_code == brand_code)
    if region:
        query = query.filter(RepairKnowledge.region_scope.in_([region, "ALL", "*"]))
    if fault_category:
        query = query.filter(RepairKnowledge.fault_category == fault_category)
    source_types = ["official", "faq", "manual"]
    if include_community:
        source_types.append("community")
    query = query.filter(RepairKnowledge.source_type.in_(source_types))

    candidates = query.limit(2000).all()
    if model:
        candidates = [
            item for item in candidates if registry.model_scope_matches(model, item.model_scope)
        ]
    return candidates


def _vector_hits(
    query: str,
    brand_code: str | None,
    model: ProductModel | None,
    region: str,
    fault_category: str | None,
    include_community: bool,
) -> list[str]:
    """Chroma 向量召回，返回 doc_id 列表。"""
    try:
        query_embedding = get_embeddings([query])[0]
    except Exception as exc:
        logger.warning("向量化失败，跳过向量召回: %s", exc)
        return []

    source_types = ["official", "faq", "manual"]
    if include_community:
        source_types.append("community")

    hits: list[str] = []
    for source_type in source_types:
        try:
            collection = _get_collection(source_type)
            if collection.count() == 0:
                continue
            conditions: list[dict] = [{"review_status": {"$in": list(REVIEW_OK)}}]
            if brand_code:
                conditions.append({"brand_code": brand_code})
            if region:
                conditions.append({"region_scope": {"$in": [region, "ALL", "*"]}})
            if fault_category:
                conditions.append({"fault_category": fault_category})
            if model:
                scopes = [model.model_id, model.series or "", "*", "ALL"]
                conditions.append({"model_scope": {"$in": [scope for scope in scopes if scope]}})
            where = conditions[0] if len(conditions) == 1 else {"$and": conditions}
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(VECTOR_CANDIDATES, collection.count()),
                where=where,
                include=["metadatas"],
            )
            metadatas = (result.get("metadatas") or [[]])[0]
            hits.extend(meta.get("doc_id") for meta in metadatas if meta and meta.get("doc_id"))
        except Exception as exc:
            logger.warning("Chroma 召回失败 %s: %s", source_type, exc)
    return hits


def _bm25_hits(query: str, candidates: list[RepairKnowledge]) -> list[str]:
    if not candidates:
        return []
    try:
        from rank_bm25 import BM25Okapi

        corpus = [knowledge_text(item) for item in candidates]
        tokenized = [_tokenize_chinese(text) for text in corpus]
        query_tokens = _tokenize_chinese(query)
        if not query_tokens:
            return []
        scores = BM25Okapi(tokenized).get_scores(query_tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [candidates[i].doc_id for i in ranked[:BM25_CANDIDATES] if scores[i] > 0]
    except Exception as exc:
        logger.warning("BM25 召回失败: %s", exc)
        return []


def _rrf_fuse(vector_ids: list[str], bm25_ids: list[str]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(vector_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    return scores


def _rerank(query: str, items: list[RepairKnowledge]) -> dict[str, float]:
    try:
        from app.services.reranker import rerank

        pairs = [(knowledge_text(item), item) for item in items]
        reranked = rerank(query, pairs, top_k=len(items))
        return {item.doc_id: score for _, item, score in reranked}
    except Exception as exc:
        logger.warning("重排序不可用，使用 RRF 分数: %s", exc)
        return {}


def _evidence_gate(
    db: Session, item: RepairKnowledge, model: ProductModel | None
) -> tuple[bool, str]:
    if item.review_status not in REVIEW_OK:
        return False, "review_status"
    if model and not registry.model_scope_matches(model, item.model_scope):
        return False, "model_scope"
    if item.source_type == "community":
        return False, "community_not_official"
    if item.authority_level not in {"A", "C"}:
        return False, "authority"
    if not item.steps:
        return False, "steps_missing"
    if item.valid_to:
        valid_to = item.valid_to
        if valid_to.tzinfo is not None:
            valid_to = valid_to.replace(tzinfo=None)
        if valid_to < datetime.now():
            return False, "expired"
    if item.risk_level == "L3":
        return False, "high_risk"
    return True, "ok"


def _source_payload(db: Session, item: RepairKnowledge) -> dict:
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == item.source_id).first()
    return {
        "doc_id": item.doc_id,
        "source_id": source.source_key if source else None,
        "title": item.title,
        "url": source.url if source else None,
        "model_scope": item.model_scope,
        "region_scope": item.region_scope,
        "source_type": item.source_type,
        "authority_level": item.authority_level,
        "version": item.version,
        "fault_category": item.fault_category,
        "fault_code": item.fault_code,
        "risk_level": item.risk_level,
        "safety_warnings": item.safety_warnings or [],
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def retrieve(
    db: Session,
    query: str,
    model: ProductModel | None = None,
    brand_code: str | None = None,
    region: str | None = "CN",
    fault_category: str | None = None,
    top_k: int = RERANK_TOP_K,
    include_community: bool = False,
    channel: str = "assistant",
    user_id: int | None = None,
    log: bool = True,
) -> dict:
    """执行完整的型号感知检索与证据校验。"""
    started = time.perf_counter()
    region = region or "CN"
    if model:
        brand_code = brand_code or _brand_code(db, model)
        fault_category = fault_category or None

    candidates = _db_candidates(db, brand_code, model, region, fault_category, include_community)
    by_id = {item.doc_id: item for item in candidates}

    vector_ids = _vector_hits(query, brand_code, model, region, fault_category, include_community)
    bm25_ids = _bm25_hits(query, candidates)
    fused = _rrf_fuse(vector_ids, bm25_ids)

    # Chroma 中的 id 可能不在当前过滤候选中（旧版本/已下架），以数据库候选为准
    ranked_ids = [doc_id for doc_id in fused if doc_id in by_id]
    if not ranked_ids and candidates:
        # 兜底：数据库候选按关键词命中数排序，保证无索引时仍可检索
        ranked_ids = _fallback_order(query, candidates)

    shortlist = [by_id[doc_id] for doc_id in ranked_ids[: max(top_k * 3, 15)]]
    rerank_scores = _rerank(query, shortlist)
    if rerank_scores:
        shortlist.sort(
            key=lambda item: rerank_scores.get(item.doc_id, fused.get(item.doc_id, 0.0)),
            reverse=True,
        )
    else:
        shortlist.sort(key=lambda item: fused.get(item.doc_id, 0.0), reverse=True)

    # 相关性门槛：避免把同品牌其他故障的无关资料一并展示为“证据”
    if shortlist and rerank_scores:
        top_score = max(rerank_scores.values(), default=0.0)
        threshold = max(0.05, top_score * 0.3)
        relevant = [item for item in shortlist if rerank_scores.get(item.doc_id, 0.0) >= threshold]
        if relevant:
            shortlist = relevant
    elif shortlist and fused:
        top_score = max(fused.get(item.doc_id, 0.0) for item in shortlist)
        if top_score > 0:
            shortlist = [
                item for item in shortlist if fused.get(item.doc_id, 0.0) >= top_score * 0.45
            ]

    results = []
    rejected: list[dict] = []
    for item in shortlist:
        passed, reason = _evidence_gate(db, item, model)
        payload = _source_payload(db, item)
        payload["score"] = round(rerank_scores.get(item.doc_id, fused.get(item.doc_id, 0.0)), 4)
        payload["gate_passed"] = passed
        payload["gate_reason"] = reason
        if passed:
            results.append(payload)
        else:
            rejected.append(payload)
        if len(results) >= top_k:
            break

    latency_ms = int((time.perf_counter() - started) * 1000)
    outcome = {
        "query": query,
        "model_id": model.model_id if model else None,
        "brand_code": brand_code,
        "region": region,
        "fault_category": fault_category,
        "results": results,
        "rejected": rejected,
        "evidence_sufficient": bool(results),
        "filter_conditions": {
            "brand_code": brand_code,
            "model_id": model.model_id if model else None,
            "model_scope": [model.model_id, model.series] if model else None,
            "region": region,
            "fault_category": fault_category,
            "review_status": list(REVIEW_OK),
        },
        "vector_candidates": len(vector_ids),
        "bm25_candidates": len(bm25_ids),
        "rerank_count": len(shortlist),
        "latency_ms": latency_ms,
    }
    if log:
        _write_log(db, outcome, channel, user_id)
    return outcome


def _fallback_order(query: str, candidates: list[RepairKnowledge]) -> list[str]:
    query_tokens = set(_tokenize_chinese(query))
    scored = []
    for item in candidates:
        tokens = set(_tokenize_chinese(knowledge_text(item)))
        overlap = len(query_tokens & tokens)
        scored.append((overlap, item.doc_id))
    scored.sort(reverse=True)
    return [doc_id for overlap, doc_id in scored if overlap > 0]


def _brand_code(db: Session, model: ProductModel) -> str | None:
    brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
    return brand.brand_code if brand else None


def _write_log(db: Session, outcome: dict, channel: str, user_id: int | None) -> None:
    try:
        log = RetrievalLog(
            user_id=user_id,
            channel=channel,
            model_id=outcome.get("model_id"),
            query=outcome["query"][:2000],
            filters=outcome.get("filter_conditions") or {},
            vector_candidates=outcome.get("vector_candidates", 0),
            bm25_candidates=outcome.get("bm25_candidates", 0),
            rerank_count=outcome.get("rerank_count", 0),
            source_doc_ids=[item["doc_id"] for item in outcome.get("results", [])],
            evidence_passed=len(outcome.get("results", [])),
            latency_ms=outcome.get("latency_ms", 0),
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.debug("写入检索日志失败: %s", exc)


# ==================== 回答生成 ====================

SYSTEM_PROMPT = """你是多品牌打印机售后支持助手。必须严格遵守：
1. 只能依据【证据】回答，不得使用证据之外的具体维修步骤或耗材规格；
2. 每个型号专属结论必须引用证据编号，如 [E1]；
3. 不同品牌的错误码、指示灯含义不可互换；未确认型号时先澄清；
4. 不提供拆机、电源组件、电路板或内部电气维修的自助步骤；
5. 证据不足时明确说明并建议补充信息或转人工。
6. 回答使用简洁中文，先给结论，再给操作步骤，最后列出来源与安全提示。

【证据】
{context}
"""


def build_context(results: list[dict], details: dict[str, RepairKnowledge]) -> str:
    if not results:
        return "（没有通过证据校验的适用资料）"
    parts = []
    for index, item in enumerate(results, start=1):
        knowledge = details.get(item["doc_id"])
        body = knowledge_text(knowledge) if knowledge else item.get("title", "")
        parts.append(
            f"[E{index}] 标题：{item['title']}\n"
            f"适用型号：{item['model_scope']}；地区：{item['region_scope']}；"
            f"来源等级：{item['authority_level']}；版本：{item['version']}\n{body}"
        )
    return "\n\n---\n\n".join(parts)


def _clarification_question(outcome: dict) -> str:
    if outcome.get("brand_code") and not outcome.get("evidence_sufficient"):
        return EVIDENCE_INSUFFICIENT_NOTICE
    return "请先确认打印机的品牌、系列和具体型号，并描述故障现象或面板错误码/灯态。"


def _fallback_answer(
    outcome: dict, details: dict[str, RepairKnowledge], model: ProductModel | None
) -> str:
    results = outcome.get("results") or []
    if not results:
        return _clarification_question(outcome)

    lines = []
    model_name = model.name if model else "当前型号"
    lines.append(f"根据已审核的 {model_name} 资料，建议按以下步骤排查：")
    primary = details.get(results[0]["doc_id"])
    if primary:
        lines.append(f"\n问题判断：{primary.symptom or primary.title}")
        causes = primary.possible_causes or []
        if causes:
            lines.append("可能原因：" + "；".join(str(c) for c in causes))
        steps = filter_self_service_steps(primary.steps or [])
        for index, step in enumerate(steps, start=1):
            instruction = step.get("instruction") if isinstance(step, dict) else str(step)
            lines.append(f"{index}. {instruction}")
        warnings = primary.safety_warnings or []
        if warnings:
            lines.append("\n安全提示：" + "；".join(str(w) for w in warnings))
    lines.append("\n来源：")
    for index, item in enumerate(results, start=1):
        lines.append(
            f"[E{index}] {item['title']}（{item['model_scope']}，{item['authority_level']} 级来源）"
        )
    lines.append("\n以上步骤来自已审核资料。若执行后仍未解决，可提交售后工单转人工处理。")
    return "\n".join(lines)


def generate_answer(
    db: Session,
    question: str,
    outcome: dict,
    model: ProductModel | None = None,
    history: list[dict] | None = None,
) -> dict:
    """生成受控回答，返回 {answer, sources, evidence_sufficient, intent}。"""
    if is_high_risk_request(question):
        return {
            "answer": refusal_answer(),
            "sources": [],
            "evidence_sufficient": False,
            "intent": "safety_refusal",
        }

    results = outcome.get("results") or []
    details = _load_details(db, results)
    sources = [
        {key: value for key, value in item.items() if key not in {"gate_passed", "gate_reason"}}
        for item in results
    ]
    if not results:
        return {
            "answer": _clarification_question(outcome),
            "sources": [],
            "evidence_sufficient": False,
            "intent": "clarification",
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=build_context(results, details))}
    ]
    for item in history or []:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append({"role": item["role"], "content": str(item["content"])[:4000]})
    messages.append({"role": "user", "content": question})

    try:
        _, answer = chat_completion(messages)
        if not answer.strip():
            raise ValueError("empty answer")
    except Exception as exc:
        logger.warning("LLM 不可用，使用证据模板回答: %s", exc)
        answer = _fallback_answer(outcome, details, model)

    return {
        "answer": answer,
        "sources": sources,
        "evidence_sufficient": True,
        "intent": "evidence_answer",
    }


def generate_answer_stream(
    db: Session,
    question: str,
    outcome: dict,
    model: ProductModel | None = None,
    history: list[dict] | None = None,
):
    """流式生成：先发送 meta，再发送 token，最后发送 done。"""
    if is_high_risk_request(question):
        yield {
            "type": "meta",
            "sources": [],
            "evidence_sufficient": False,
            "intent": "safety_refusal",
        }
        yield {"type": "answer", "content": refusal_answer()}
        yield {"type": "done"}
        return

    results = outcome.get("results") or []
    details = _load_details(db, results)
    sources = [
        {key: value for key, value in item.items() if key not in {"gate_passed", "gate_reason"}}
        for item in results
    ]
    yield {
        "type": "meta",
        "sources": sources,
        "evidence_sufficient": bool(results),
        "intent": "evidence_answer" if results else "clarification",
        "filter_conditions": outcome.get("filter_conditions"),
    }
    if not results:
        yield {"type": "answer", "content": _clarification_question(outcome)}
        yield {"type": "done"}
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=build_context(results, details))}
    ]
    for item in history or []:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append({"role": item["role"], "content": str(item["content"])[:4000]})
    messages.append({"role": "user", "content": question})

    try:
        produced = False
        for chunk in chat_completion_stream(messages):
            if chunk.get("type") == "answer" and chunk.get("content"):
                produced = True
            yield chunk
        if not produced:
            raise ValueError("empty stream")
    except Exception as exc:
        logger.warning("LLM 流式不可用，使用证据模板回答: %s", exc)
        yield {"type": "answer", "content": _fallback_answer(outcome, details, model)}
    yield {"type": "done"}


def _load_details(db: Session, results: list[dict]) -> dict[str, RepairKnowledge]:
    ids = [item["doc_id"] for item in results]
    if not ids:
        return {}
    items = db.query(RepairKnowledge).filter(RepairKnowledge.doc_id.in_(ids)).all()
    return {item.doc_id: item for item in items}


def classify_intent(db: Session, question: str, model: ProductModel | None) -> str:
    """简单意图识别：诊断 / 知识查询 / 错误码 / 高危 / 通用咨询。"""
    if is_high_risk_request(question):
        return "safety_refusal"
    lowered = question.lower()
    if any(
        word in lowered
        for word in ("不能打印", "无法打印", "故障", "报错", "错误代码", "卡纸", "不进纸")
    ):
        return "troubleshooting"
    if any(word in lowered for word in ("怎么安装", "如何安装", "说明书", "耗材", "维护", "清洁")):
        return "knowledge"
    if registry.extract_error_code(question):
        return "error_code"
    if model and classify_symptom(question):
        return "troubleshooting"
    return "general"


def summarize_sources(sources: list[dict]) -> list[dict]:
    """回答中展示给前端的引用卡片。"""
    return [
        {
            "doc_id": item.get("doc_id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "model_scope": item.get("model_scope"),
            "authority_level": item.get("authority_level"),
            "fault_category": item.get("fault_category"),
            "fault_category_label": category_label(item.get("fault_category")),
            "risk_level": item.get("risk_level"),
            "version": item.get("version"),
            "safety_warnings": item.get("safety_warnings") or [],
        }
        for item in sources
    ]


def _tokenize(text: str) -> list[str]:
    return [token for token in _tokenize_chinese(text) if token and not re.fullmatch(r"\W+", token)]
