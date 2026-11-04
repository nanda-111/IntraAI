"""知识来源、文档、维修知识、故障分类与维修案例 ORM 模型。"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class FaultTaxonomy(Base):
    """统一故障大类（fault_taxonomy）。

    统一分类只用于统计和路由，不产生跨品牌错误码等价关系。
    """

    __tablename__ = "fault_taxonomy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fault_code = Column(String(40), unique=True, nullable=False, index=True)
    parent_category = Column(String(40), nullable=True)
    label = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeSource(Base):
    """知识来源登记（kb_sources）。"""

    __tablename__ = "kb_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_key = Column(String(80), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    url = Column(String(500), nullable=True)
    source_type = Column(
        String(30), default="official", nullable=False
    )  # official / faq / community / manual
    authority_level = Column(String(4), default="A", nullable=False)  # A / B / C / D
    brand_code = Column(String(30), nullable=True)
    model_scope = Column(String(160), nullable=True)
    region_scope = Column(String(40), default="CN")
    version = Column(String(40), default="1.0")
    license_note = Column(Text, nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    verified_status = Column(String(20), default="verified", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeDocument(Base):
    """原始文档与解析任务（kb_documents）。"""

    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    file_name = Column(String(260), nullable=True)
    file_path = Column(String(600), nullable=True)
    file_type = Column(String(20), nullable=True)
    checksum = Column(String(64), nullable=True, index=True)
    parse_status = Column(
        String(20), default="pending", nullable=False
    )  # pending / parsing / parsed / failed
    parse_error = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    index_version = Column(String(40), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RepairKnowledge(Base):
    """可检索的维修知识单元（repair_knowledge）。"""

    __tablename__ = "repair_knowledge"
    __table_args__ = (UniqueConstraint("doc_id", name="uq_repair_knowledge_doc_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(80), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("printer_brands.id"), nullable=True, index=True)
    brand_code = Column(String(30), nullable=True, index=True)
    series = Column(String(120), nullable=True)
    model_scope = Column(String(160), nullable=False, index=True)  # model_id / series / *
    region_scope = Column(String(40), default="CN", nullable=False)
    code_system = Column(String(60), nullable=True)
    fault_category = Column(String(40), nullable=False, index=True)
    fault_code = Column(String(40), nullable=True, index=True)
    title = Column(String(220), nullable=False)
    symptom = Column(Text, nullable=True)
    possible_causes = Column(JSON, default=list)
    preconditions = Column(JSON, default=list)
    steps = Column(JSON, default=list)
    expected_result = Column(Text, nullable=True)
    verification_method = Column(Text, nullable=True)
    safety_warnings = Column(JSON, default=list)
    risk_level = Column(String(4), default="L1", nullable=False)
    source_type = Column(String(30), default="official", nullable=False, index=True)
    authority_level = Column(String(4), default="A", nullable=False)
    review_status = Column(String(20), default="draft", nullable=False, index=True)
    # draft / pending / approved / published / rejected / archived
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)
    language = Column(String(20), default="zh-CN")
    version = Column(String(40), default="1.0")
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    version_history = Column(JSON, default=list)
    index_version = Column(String(40), nullable=True)
    indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RepairCase(Base):
    """社区/人工维修案例（repair_cases），不得直接作为官方维修步骤。"""

    __tablename__ = "repair_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(80), unique=True, nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=True)
    raw_brand = Column(String(80), nullable=True)
    raw_model = Column(String(120), nullable=True)
    problem_text = Column(Text, nullable=False)
    fault_label = Column(String(40), nullable=True)
    repair_outcome = Column(Text, nullable=True)
    model_known = Column(String(10), default="unknown", nullable=False)  # known / unknown
    credibility = Column(String(20), default="unverified", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
