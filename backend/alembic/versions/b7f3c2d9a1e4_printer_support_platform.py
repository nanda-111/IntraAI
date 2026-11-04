"""printer support platform domain tables

Revision ID: b7f3c2d9a1e4
Revises: 72a48025e568
Create Date: 2026-11-04 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7f3c2d9a1e4"
down_revision: str | Sequence[str] | None = "72a48025e568"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    ]


def upgrade() -> None:
    # ---------- users 扩展 ----------
    op.add_column("users", sa.Column("display_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=30), nullable=False, server_default="user"),
    )

    # ---------- 品牌与型号 ----------
    op.create_table(
        "printer_brands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brand_code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_code"),
    )
    op.create_index("ix_printer_brands_brand_code", "printer_brands", ["brand_code"])

    op.create_table(
        "product_models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(length=80), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("series", sa.String(length=120), nullable=False),
        sa.Column("model_code", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("region", sa.String(length=20), nullable=False, server_default="CN"),
        sa.Column("technology", sa.String(length=40), nullable=False, server_default="inkjet"),
        sa.Column("supported_features", sa.JSON(), nullable=True),
        sa.Column("support_status", sa.String(length=20), nullable=False, server_default="planned"),
        sa.Column("official_source_count", sa.Integer(), server_default="0"),
        sa.Column("knowledge_coverage", sa.Integer(), server_default="0"),
        sa.Column("release_note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["brand_id"], ["printer_brands.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id"),
    )
    op.create_index("ix_product_models_model_id", "product_models", ["model_id"])
    op.create_index("ix_product_models_brand_id", "product_models", ["brand_id"])
    op.create_index("ix_product_models_support_status", "product_models", ["support_status"])

    # ---------- 知识来源 ----------
    op.create_table(
        "kb_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="official"),
        sa.Column("authority_level", sa.String(length=4), nullable=False, server_default="A"),
        sa.Column("brand_code", sa.String(length=30), nullable=True),
        sa.Column("model_scope", sa.String(length=160), nullable=True),
        sa.Column("region_scope", sa.String(length=40), server_default="CN"),
        sa.Column("version", sa.String(length=40), server_default="1.0"),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column(
            "verified_status", sa.String(length=20), nullable=False, server_default="verified"
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_kb_sources_source_key", "kb_sources", ["source_key"])

    op.create_table(
        "model_capabilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(length=80), nullable=False),
        sa.Column("fault_category", sa.String(length=40), nullable=False),
        sa.Column("code_system", sa.String(length=60), nullable=True),
        sa.Column("supported_features", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column(
            "verified_status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["model_id"], ["product_models.model_id"]),
        sa.ForeignKeyConstraint(["source_id"], ["kb_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "fault_category", name="uq_model_fault_category"),
    )
    op.create_index("ix_model_capabilities_model_id", "model_capabilities", ["model_id"])

    op.create_table(
        "user_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(length=80), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["product_models.model_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "model_id", name="uq_user_device"),
    )
    op.create_index("ix_user_devices_user_id", "user_devices", ["user_id"])

    # ---------- 知识文档与知识条目 ----------
    op.create_table(
        "kb_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("file_name", sa.String(length=260), nullable=True),
        sa.Column("file_path", sa.String(length=600), nullable=True),
        sa.Column("file_type", sa.String(length=20), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("parse_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("index_version", sa.String(length=40), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_id"], ["kb_sources.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_documents_source_id", "kb_documents", ["source_id"])
    op.create_index("ix_kb_documents_checksum", "kb_documents", ["checksum"])

    op.create_table(
        "repair_knowledge",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doc_id", sa.String(length=80), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("brand_code", sa.String(length=30), nullable=True),
        sa.Column("series", sa.String(length=120), nullable=True),
        sa.Column("model_scope", sa.String(length=160), nullable=False),
        sa.Column("region_scope", sa.String(length=40), nullable=False, server_default="CN"),
        sa.Column("code_system", sa.String(length=60), nullable=True),
        sa.Column("fault_category", sa.String(length=40), nullable=False),
        sa.Column("fault_code", sa.String(length=40), nullable=True),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("symptom", sa.Text(), nullable=True),
        sa.Column("possible_causes", sa.JSON(), nullable=True),
        sa.Column("preconditions", sa.JSON(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("verification_method", sa.Text(), nullable=True),
        sa.Column("safety_warnings", sa.JSON(), nullable=True),
        sa.Column("risk_level", sa.String(length=4), nullable=False, server_default="L1"),
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="official"),
        sa.Column("authority_level", sa.String(length=4), nullable=False, server_default="A"),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), server_default="zh-CN"),
        sa.Column("version", sa.String(length=40), server_default="1.0"),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("version_history", sa.JSON(), nullable=True),
        sa.Column("index_version", sa.String(length=40), nullable=True),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["kb_documents.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["kb_sources.id"]),
        sa.ForeignKeyConstraint(["brand_id"], ["printer_brands.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doc_id", name="uq_repair_knowledge_doc_id"),
    )
    for column in (
        "doc_id",
        "source_id",
        "brand_id",
        "brand_code",
        "model_scope",
        "fault_category",
        "fault_code",
        "source_type",
        "review_status",
        "content_hash",
    ):
        op.create_index(f"ix_repair_knowledge_{column}", "repair_knowledge", [column])

    op.create_table(
        "fault_taxonomy",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fault_code", sa.String(length=40), nullable=False),
        sa.Column("parent_category", sa.String(length=40), nullable=True),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fault_code"),
    )
    op.create_index("ix_fault_taxonomy_fault_code", "fault_taxonomy", ["fault_code"])

    op.create_table(
        "repair_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("raw_brand", sa.String(length=80), nullable=True),
        sa.Column("raw_model", sa.String(length=120), nullable=True),
        sa.Column("problem_text", sa.Text(), nullable=False),
        sa.Column("fault_label", sa.String(length=40), nullable=True),
        sa.Column("repair_outcome", sa.Text(), nullable=True),
        sa.Column("model_known", sa.String(length=10), nullable=False, server_default="unknown"),
        sa.Column("credibility", sa.String(length=20), nullable=False, server_default="unverified"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["source_id"], ["kb_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id"),
    )
    op.create_index("ix_repair_cases_case_id", "repair_cases", ["case_id"])

    # ---------- 诊断 ----------
    op.create_table(
        "diagnosis_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("diagnosis_uid", sa.String(length=60), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(length=80), nullable=True),
        sa.Column("brand_code", sa.String(length=30), nullable=True),
        sa.Column("region", sa.String(length=20), server_default="CN"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="MODEL_PENDING"),
        sa.Column("fault_category", sa.String(length=40), nullable=True),
        sa.Column("brand_error_code", sa.String(length=60), nullable=True),
        sa.Column("symptom", sa.Text(), nullable=True),
        sa.Column("slot_snapshot", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("current_step_no", sa.Integer(), server_default="0"),
        sa.Column("escalation_required", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        *_timestamps(),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["product_models.model_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diagnosis_uid"),
    )
    op.create_index("ix_diagnosis_sessions_diagnosis_uid", "diagnosis_sessions", ["diagnosis_uid"])
    op.create_index("ix_diagnosis_sessions_user_id", "diagnosis_sessions", ["user_id"])
    op.create_index("ix_diagnosis_sessions_model_id", "diagnosis_sessions", ["model_id"])
    op.create_index("ix_diagnosis_sessions_status", "diagnosis_sessions", ["status"])

    op.create_table(
        "diagnosis_turns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagnosis_turns_diagnosis_id", "diagnosis_turns", ["diagnosis_id"])

    op.create_table(
        "diagnosis_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=4), nullable=False, server_default="L1"),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("source_doc_id", sa.String(length=80), nullable=True),
        sa.Column("source_title", sa.String(length=220), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("user_result", sa.Text(), nullable=True),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagnosis_steps_diagnosis_id", "diagnosis_steps", ["diagnosis_id"])

    # ---------- 工单 ----------
    op.create_table(
        "service_tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_no", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=True),
        sa.Column("brand_code", sa.String(length=30), nullable=True),
        sa.Column("model_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("contact", sa.String(length=120), nullable=True),
        sa.Column("contact_type", sa.String(length=20), server_default="phone"),
        sa.Column("fault_category", sa.String(length=40), nullable=True),
        sa.Column("brand_error_code", sa.String(length=60), nullable=True),
        sa.Column("executed_steps", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_no"),
    )
    op.create_index("ix_service_tickets_ticket_no", "service_tickets", ["ticket_no"])
    op.create_index("ix_service_tickets_user_id", "service_tickets", ["user_id"])
    op.create_index("ix_service_tickets_model_id", "service_tickets", ["model_id"])
    op.create_index("ix_service_tickets_status", "service_tickets", ["status"])

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("before_status", sa.String(length=30), nullable=True),
        sa.Column("after_status", sa.String(length=30), nullable=True),
        sa.Column("is_internal", sa.String(length=10), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["ticket_id"], ["service_tickets.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])

    # ---------- 智能客服 ----------
    op.create_table(
        "printer_chat_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=220), nullable=False, server_default="新的咨询"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["product_models.model_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_printer_chat_sessions_user_id", "printer_chat_sessions", ["user_id"])

    op.create_table(
        "printer_chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("intent", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["printer_chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_printer_chat_messages_session_id", "printer_chat_messages", ["session_id"])

    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=30), server_default="assistant"),
        sa.Column("model_id", sa.String(length=80), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("vector_candidates", sa.Integer(), server_default="0"),
        sa.Column("bm25_candidates", sa.Integer(), server_default="0"),
        sa.Column("rerank_count", sa.Integer(), server_default="0"),
        sa.Column("source_doc_ids", sa.JSON(), nullable=True),
        sa.Column("evidence_passed", sa.Integer(), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------- 评测 ----------
    op.create_table(
        "eval_datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand_code", sa.String(length=30), nullable=True),
        sa.Column("model_id", sa.String(length=80), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "eval_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_doc_ids", sa.JSON(), nullable=True),
        sa.Column("expected_fault_category", sa.String(length=40), nullable=True),
        sa.Column("expected_escalation", sa.String(length=10), server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_items_dataset_id", "eval_items", ["dataset_id"])

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("total", sa.Integer(), server_default="0"),
        sa.Column("passed", sa.Integer(), server_default="0"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_runs_dataset_id", "eval_runs", ["dataset_id"])

    op.create_table(
        "eval_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("retrieved_doc_ids", sa.JSON(), nullable=True),
        sa.Column("recall5", sa.Integer(), server_default="0"),
        sa.Column("reciprocal_rank", sa.Integer(), server_default="0"),
        sa.Column("fault_category", sa.String(length=40), nullable=True),
        sa.Column("fault_match", sa.Integer(), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["eval_runs.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["eval_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_results_run_id", "eval_results", ["run_id"])

    # ---------- 审计与反馈 ----------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("before_value", sa.Text(), nullable=True),
        sa.Column("after_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_operator_id", "audit_logs", ["operator_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=30), server_default="assistant"),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), server_default="5"),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])


def downgrade() -> None:
    for table in (
        "user_feedback",
        "audit_logs",
        "eval_results",
        "eval_runs",
        "eval_items",
        "eval_datasets",
        "retrieval_logs",
        "printer_chat_messages",
        "printer_chat_sessions",
        "ticket_events",
        "service_tickets",
        "diagnosis_steps",
        "diagnosis_turns",
        "diagnosis_sessions",
        "repair_cases",
        "fault_taxonomy",
        "repair_knowledge",
        "kb_documents",
        "user_devices",
        "model_capabilities",
        "kb_sources",
        "product_models",
        "printer_brands",
    ):
        op.drop_table(table)
    op.drop_column("users", "role")
    op.drop_column("users", "phone")
    op.drop_column("users", "display_name")
