"""评测服务：按品牌/型号分层运行检索、分类与升级指标。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domains.printer import registry
from app.domains.printer.fault_taxonomy import classify_symptom
from app.domains.printer.safety_policy import is_high_risk_request
from app.models.evaluation import EvalDataset, EvalItem, EvalResult, EvalRun
from app.models.user import User
from app.services import printer_rag_service


def run_dataset(db: Session, dataset: EvalDataset, user: User) -> EvalRun:
    items = db.query(EvalItem).filter(EvalItem.dataset_id == dataset.id).order_by(EvalItem.id).all()
    run = EvalRun(
        dataset_id=dataset.id,
        status="running",
        created_by=user.id,
        total=len(items),
        started_at=datetime.now(),
    )
    db.add(run)
    db.flush()

    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    fault_scores: list[float] = []
    escalation_scores: list[float] = []
    latencies: list[int] = []
    passed = 0

    for item in items:
        model = None
        if dataset.model_id:
            model = (
                db.query(registry.ProductModel)
                .filter(registry.ProductModel.model_id == dataset.model_id)
                .first()
            )
        if model is None:
            resolved = registry.resolve_model(db, text=item.question)
            model = resolved.get("model")
        if is_high_risk_request(item.question):
            outcome = {
                "results": [],
                "evidence_sufficient": False,
                "latency_ms": 0,
                "fault_category": None,
            }
            predicted_category = None
        else:
            outcome = printer_rag_service.retrieve(
                db,
                item.question,
                model=model,
                region=model.region if model else "CN",
                fault_category=item.expected_fault_category or classify_symptom(item.question),
                channel="evaluation",
                user_id=user.id,
                log=False,
            )
            predicted_category = (
                outcome["results"][0].get("fault_category")
                if outcome["results"]
                else classify_symptom(item.question)
            )
        retrieved = [result["doc_id"] for result in outcome["results"]]
        expected = item.expected_doc_ids or []
        recall = 1.0 if expected and any(doc in retrieved[:5] for doc in expected) else 0.0
        rr = 0.0
        for rank, doc_id in enumerate(retrieved[:5], start=1):
            if doc_id in expected:
                rr = 1.0 / rank
                break
        fault_match = (
            1.0
            if item.expected_fault_category and predicted_category == item.expected_fault_category
            else 0.0
        )
        expected_escalation = str(item.expected_escalation).lower() == "true"
        actual_escalation = not outcome["evidence_sufficient"]
        escalation_hit = 1.0 if expected_escalation == actual_escalation else 0.0
        if recall or (not expected and outcome["evidence_sufficient"]):
            passed += 1

        if expected:
            recalls.append(recall)
        reciprocal_ranks.append(rr)
        if item.expected_fault_category:
            fault_scores.append(fault_match)
        escalation_scores.append(escalation_hit)
        latencies.append(outcome["latency_ms"])

        db.add(
            EvalResult(
                run_id=run.id,
                item_id=item.id,
                question=item.question,
                retrieved_doc_ids=retrieved,
                recall5=int(recall),
                reciprocal_rank=int(rr),
                fault_category=predicted_category,
                fault_match=int(fault_match),
                latency_ms=outcome["latency_ms"],
            )
        )

    run.metrics = {
        "recall_at_5": _mean(recalls),
        "mrr_at_5": _mean(reciprocal_ranks),
        "fault_accuracy": _mean(fault_scores),
        "escalation_recall": _mean(escalation_scores),
        "avg_latency_ms": _mean(latencies),
        "items_with_expected_docs": len(recalls),
        "note": "指标基于当前测试集与真实检索结果计算，不等同于全量线上效果。",
    }
    run.passed = passed
    run.status = "finished"
    run.finished_at = datetime.now()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def run_payload(db: Session, run: EvalRun) -> dict:
    dataset = db.query(EvalDataset).filter(EvalDataset.id == run.dataset_id).first()
    results = db.query(EvalResult).filter(EvalResult.run_id == run.id).order_by(EvalResult.id).all()
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "dataset_name": dataset.name if dataset else None,
        "status": run.status,
        "metrics": run.metrics or {},
        "total": run.total,
        "passed": run.passed,
        "created_by": run.created_by,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error": run.error,
        "results": [
            {
                "id": result.id,
                "item_id": result.item_id,
                "question": result.question,
                "retrieved_doc_ids": result.retrieved_doc_ids or [],
                "recall5": bool(result.recall5),
                "reciprocal_rank": result.reciprocal_rank,
                "fault_category": result.fault_category,
                "fault_match": bool(result.fault_match),
                "latency_ms": result.latency_ms,
            }
            for result in results
        ],
    }
