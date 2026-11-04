"""平台领域服务与检索链路单元测试。"""

from datetime import datetime, timedelta

import pytest

from app.domains.printer import capabilities, fault_taxonomy, registry, safety_policy
from app.models.diagnosis import DiagnosisStep
from app.models.printer_brand import ModelCapability, ProductModel
from app.models.repair_knowledge import KnowledgeSource, RepairKnowledge
from app.services import diagnosis_service, knowledge_ingestion, knowledge_review, ticket_service
from app.services import printer_rag_service as rag
from app.services.audit_service import _dump


class TestRegistry:
    def test_detect_brand_and_resolve_variants(self, db_session, seeded):
        assert registry.detect_brand("我的惠普打印机") == "HP"
        assert registry.detect_brand("Canon TS5380") == "Canon"
        assert registry.detect_brand("nothing") is None

        exact = registry.resolve_model(db_session, "hp_deskjet_2720")
        assert exact["confidence"] == 1.0
        assert exact["model"].model_id == "hp_deskjet_2720"

        alias = registry.resolve_model(db_session, "DJ2720")
        assert alias["confidence"] == 0.9

        fuzzy = registry.resolve_model(db_session, "HP DeskJet 2720 卡纸")
        assert fuzzy["model"].model_id == "hp_deskjet_2720"
        assert fuzzy["confidence"] == 0.7

        ambiguous = registry.resolve_model(db_session, "DeskJet")
        assert ambiguous["requires_confirmation"] is True
        assert len(ambiguous["candidates"]) >= 1

        missing = registry.resolve_model(db_session, "完全未知设备")
        assert missing["model"] is None

        by_brand = registry.resolve_model(db_session, "", brand_code="HP", region="CN")
        assert by_brand["requires_confirmation"] is True

    def test_require_model_and_scope(self, db_session, seeded):
        with pytest.raises(ValueError):
            registry.require_model(db_session, None)
        with pytest.raises(ValueError):
            registry.require_model(db_session, "nope")

        model = registry.require_model(db_session, "hp_deskjet_2720")
        assert registry.model_scope_matches(model, "DeskJet 2700 Series")
        assert registry.model_scope_matches(model, "hp_deskjet_2720")
        assert registry.model_scope_matches(model, "*")
        assert registry.model_scope_matches(model, "DJ2720")
        assert not registry.model_scope_matches(model, "Canon TS5300")
        assert not registry.model_scope_matches(model, None)

        assert registry.supports_fault_category(db_session, model, "paper_feed")
        assert not registry.supports_fault_category(db_session, model, "unknown")
        assert not registry.supports_fault_category(db_session, model, None)

    def test_support_status_and_codes(self, db_session, seeded):
        assert registry.support_status_label("active") == "已支持"
        assert registry.is_diagnosis_supported(
            registry.require_model(db_session, "hp_deskjet_2720")
        )
        assert registry.extract_error_code("显示 E4") == "E4"
        assert registry.extract_error_code("Support Code E03") == "E03"
        assert registry.extract_error_code("错误 5100") == "5100"
        assert registry.extract_error_code("没有代码") is None


class TestFaultTaxonomyAndSafety:
    def test_categories_and_codes(self):
        assert fault_taxonomy.normalize_category("卡纸") == "paper_feed"
        assert fault_taxonomy.normalize_category("PAPER_FEED") == "paper_feed"
        assert fault_taxonomy.normalize_category("打印质量") == "print_quality"
        assert fault_taxonomy.normalize_category(None) is None
        assert fault_taxonomy.category_label("paper_feed") == "进纸与卡纸"
        assert fault_taxonomy.category_label(None) == "未分类"

        assert fault_taxonomy.classify_symptom("打印机卡纸了") == "paper_feed"
        assert fault_taxonomy.classify_symptom("wifi 离线") == "connectivity"
        assert fault_taxonomy.classify_symptom("") is None

        hp = fault_taxonomy.lookup_error_code("HP", "e4")
        assert hp["category"] == "paper_feed"
        assert fault_taxonomy.lookup_error_code("Canon", "E03")["category"] == "paper_feed"
        # 跨品牌不映射
        assert fault_taxonomy.lookup_error_code("HP", "E03") is None
        assert fault_taxonomy.lookup_error_code("HP", None) is None
        assert fault_taxonomy.code_system_for("canon")
        assert fault_taxonomy.code_system_for(None) is None
        assert fault_taxonomy.known_codes_for_brand("HP")
        assert fault_taxonomy.known_codes_for_brand("brother")
        assert fault_taxonomy.known_codes_for_brand(None) == []

    def test_safety_policy(self):
        assert safety_policy.classify_text_risk("拆开外壳修电路板") == "L3"
        assert safety_policy.classify_text_risk("清洁进纸滚轮") == "L2"
        assert safety_policy.classify_text_risk("观察指示灯") == "L1"
        assert safety_policy.is_high_risk_request("拆机") is True
        assert safety_policy.is_high_risk_request(None) is False

        steps = [
            {"risk_level": "L1"},
            {"risk_level": "L2"},
            {"risk_level": "L3"},
        ]
        assert len(safety_policy.filter_self_service_steps(steps)) == 2
        assert safety_policy.allows_step({"risk_level": "L2"})
        assert not safety_policy.allows_step({"risk_level": "L3"})
        assert not safety_policy.allows_step({"risk_level": "L1"}, requested_risk="L3")
        assert "高风险" in safety_policy.refusal_answer()
        assert safety_policy.risk_label("L2") == "谨慎操作"
        assert safety_policy.step_risk({"risk_level": "bad"}) == "L1"


class TestCapabilitiesDomain:
    def test_check_category(self, db_session, seeded):
        model = registry.require_model(db_session, "hp_deskjet_2720")
        listing = capabilities.capability_list(db_session, model.model_id)
        assert listing
        assert capabilities.check_category(db_session, model, "paper_feed")["supported"]
        assert not capabilities.check_category(db_session, model, None)["supported"]
        assert not capabilities.check_category(db_session, model, "unknown")["supported"]

        capabilities.refresh_coverage(db_session, model, 99)
        assert model.knowledge_coverage == 99


class TestPrinterRagService:
    def test_knowledge_text_and_metadata(self, db_session, seeded):
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()
        text = rag.knowledge_text(item)
        assert "操作步骤" in text
        meta = rag.knowledge_metadata(db_session, item)
        assert meta["brand_code"] == "HP"
        assert meta["review_status"] == "published"

    def test_evidence_gate(self, db_session, seeded):
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()
        model = registry.require_model(db_session, "hp_deskjet_2720")
        assert rag._evidence_gate(db_session, item, model)[0]

        item.review_status = "draft"
        assert rag._evidence_gate(db_session, item, model)[1] == "review_status"
        item.review_status = "published"
        item.source_type = "community"
        assert rag._evidence_gate(db_session, item, model)[1] == "community_not_official"
        item.source_type = "faq"
        item.authority_level = "D"
        assert rag._evidence_gate(db_session, item, model)[1] == "authority"
        item.authority_level = "C"
        item.steps = []
        assert rag._evidence_gate(db_session, item, model)[1] == "steps_missing"
        item.steps = [{"instruction": "x"}]
        item.risk_level = "L3"
        assert rag._evidence_gate(db_session, item, model)[1] == "high_risk"
        item.risk_level = "L1"
        item.valid_to = datetime.now() - timedelta(days=1)
        assert rag._evidence_gate(db_session, item, model)[1] == "expired"
        item.valid_to = None
        item.model_scope = "别的型号"
        assert rag._evidence_gate(db_session, item, model)[1] == "model_scope"

    def test_fallback_order_and_rrf(self, db_session, seeded):
        candidates = (
            db_session.query(RepairKnowledge).filter(RepairKnowledge.brand_code == "HP").all()
        )
        order = rag._fallback_order("卡纸 E4", candidates)
        assert order
        assert order[0] == "rk_hp_paper"
        assert rag._fallback_order("完全无关的词汇", candidates) == []

        fused = rag._rrf_fuse(["a", "b"], ["b", "c"])
        assert fused["b"] > fused["a"]
        assert fused["b"] > fused["c"]

    def test_retrieve_with_mocked_externals(self, db_session, seeded, monkeypatch):
        model = registry.require_model(db_session, "hp_deskjet_2720")
        monkeypatch.setattr(rag, "_vector_hits", lambda *args, **kwargs: ["rk_hp_paper"])
        monkeypatch.setattr(rag, "get_embeddings", lambda texts: [[0.1] * 8 for _ in texts])
        monkeypatch.setattr(
            "app.services.reranker.rerank",
            lambda q, c, top_k=5: [(text, meta, 0.95) for text, meta in c],
        )
        outcome = rag.retrieve(
            db_session,
            "卡纸 E4",
            model=model,
            brand_code="HP",
            fault_category="paper_feed",
            channel="test",
            log=False,
        )
        assert outcome["evidence_sufficient"]
        assert outcome["results"][0]["doc_id"] == "rk_hp_paper"
        assert outcome["vector_candidates"] == 1
        assert outcome["filter_conditions"]["brand_code"] == "HP"

        no_evidence = rag.retrieve(
            db_session,
            "完全无关的问题",
            model=model,
            brand_code="HP",
            fault_category="scanner",
            channel="test",
            log=False,
        )
        assert no_evidence["evidence_sufficient"] is False

    def test_index_and_status(self, db_session, seeded, monkeypatch):
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()

        class FakeCollection:
            def __init__(self):
                self.upserted = None
                self.deleted = None

            def upsert(self, **kwargs):
                self.upserted = kwargs

            def delete(self, ids=None):
                self.deleted = ids

            def count(self):
                return 1

            def query(self, **kwargs):
                return {"metadatas": [[{"doc_id": "rk_hp_paper"}]]}

        collection = FakeCollection()
        monkeypatch.setattr(rag, "_get_collection", lambda source_type: collection)
        monkeypatch.setattr(rag, "get_embeddings", lambda texts: [[0.1] * 8 for _ in texts])

        assert rag.index_knowledge(db_session, item) is True
        assert collection.upserted["ids"] == ["rk_hp_paper"]
        assert item.index_version

        rag.remove_from_index(item)
        assert collection.deleted == ["rk_hp_paper"]

        monkeypatch.setattr(rag, "index_knowledge", lambda db, record: True)
        assert rag.reindex_all(db_session)["indexed"] >= 1
        status = rag.index_status()
        assert status["printer_official_knowledge"]["count"] == 1

        hits = rag._vector_hits("卡纸", "HP", None, "CN", None, False)
        assert hits
        assert all(item == "rk_hp_paper" for item in hits)

    def test_generate_answer_paths(self, db_session, seeded, monkeypatch):
        model = registry.require_model(db_session, "hp_deskjet_2720")
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()
        outcome = {
            "results": [
                {
                    "doc_id": item.doc_id,
                    "title": item.title,
                    "model_scope": item.model_scope,
                    "region_scope": "CN",
                    "authority_level": "C",
                    "version": "1.0",
                    "fault_category": "paper_feed",
                    "risk_level": "L2",
                    "safety_warnings": item.safety_warnings,
                }
            ],
            "filter_conditions": {},
        }

        monkeypatch.setattr(rag, "chat_completion", lambda messages, **kwargs: ("", "LLM 回答"))
        result = rag.generate_answer(db_session, "卡纸 E4", outcome, model=model)
        assert result["answer"] == "LLM 回答"
        assert result["sources"]

        def raise_error(messages, **kwargs):
            raise RuntimeError("llm down")

        monkeypatch.setattr(rag, "chat_completion", raise_error)
        fallback = rag.generate_answer(db_session, "卡纸 E4", outcome, model=model)
        assert "来源" in fallback["answer"]

        empty = rag.generate_answer(db_session, "卡纸", {"results": []}, model=model)
        assert empty["evidence_sufficient"] is False

        refused = rag.generate_answer(db_session, "拆机修电路板", outcome, model=model)
        assert refused["intent"] == "safety_refusal"

        context = rag.build_context(outcome["results"], {item.doc_id: item})
        assert item.title in context
        assert rag.build_context([], {}) == "（没有通过证据校验的适用资料）"

        sources = rag.summarize_sources(outcome["results"])
        assert sources[0]["fault_category_label"] == "进纸与卡纸"

    def test_generate_answer_stream_paths(self, db_session, seeded, monkeypatch):
        model = registry.require_model(db_session, "hp_deskjet_2720")
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()
        outcome = {
            "results": [
                {
                    "doc_id": item.doc_id,
                    "title": item.title,
                    "model_scope": item.model_scope,
                    "region_scope": "CN",
                    "authority_level": "C",
                    "version": "1.0",
                    "fault_category": "paper_feed",
                    "risk_level": "L2",
                }
            ]
        }

        high_risk = list(rag.generate_answer_stream(db_session, "拆机", outcome, model=model))
        assert high_risk[-1]["type"] == "done"
        assert high_risk[0]["intent"] == "safety_refusal"

        no_result = list(
            rag.generate_answer_stream(db_session, "卡纸", {"results": []}, model=model)
        )
        assert no_result[0]["type"] == "meta"
        assert no_result[0]["evidence_sufficient"] is False

        def fake_stream(messages, **kwargs):
            yield {"type": "answer", "content": "流式回答"}

        monkeypatch.setattr(rag, "chat_completion_stream", fake_stream)
        streamed = list(rag.generate_answer_stream(db_session, "卡纸", outcome, model=model))
        assert any(chunk.get("content") == "流式回答" for chunk in streamed)
        assert streamed[-1]["type"] == "done"

        def broken_stream(messages, **kwargs):
            raise RuntimeError("down")
            yield  # pragma: no cover

        monkeypatch.setattr(rag, "chat_completion_stream", broken_stream)
        fallback = list(rag.generate_answer_stream(db_session, "卡纸", outcome, model=model))
        assert any("来源" in (chunk.get("content") or "") for chunk in fallback)

    def test_classify_intent(self, db_session, seeded):
        model = registry.require_model(db_session, "hp_deskjet_2720")
        assert rag.classify_intent(db_session, "拆机修电路板", model) == "safety_refusal"
        assert rag.classify_intent(db_session, "打印机卡纸了", model) == "troubleshooting"
        assert rag.classify_intent(db_session, "怎么安装墨盒", model) == "knowledge"
        assert rag.classify_intent(db_session, "E4 是什么", model) == "error_code"
        assert rag.classify_intent(db_session, "你好", model) == "general"


class TestDiagnosisService:
    def test_lifecycle_and_summary(self, db_session, seeded, test_user):
        session = diagnosis_service.create_session(db_session, test_user)
        assert session.status == "MODEL_PENDING"

        session = diagnosis_service.set_model(db_session, session, test_user, "hp_deskjet_2720")
        assert session.status == "COLLECTING"

        session = diagnosis_service.close_session(db_session, session, True, "已解决")
        assert session.status == "RESOLVED"
        assert "型号" in session.summary
        assert diagnosis_service.list_sessions(db_session, test_user)

        payload = diagnosis_service.build_payload(db_session, session)
        assert payload["diagnosis_state"] == "RESOLVED"
        assert payload["turns"]

    def test_unsupported_model_and_capability(self, db_session, seeded, test_user):
        model = db_session.query(ProductModel).filter_by(model_id="canon_pixma_ts5380").first()
        model.support_status = "building"
        db_session.commit()
        session = diagnosis_service.create_session(
            db_session, test_user, model_id="canon_pixma_ts5380"
        )
        assert session.status == "ESCALATED"

        cap = (
            db_session.query(ModelCapability)
            .filter_by(model_id="epson_ecotank_l3250", fault_category="paper_feed")
            .first()
        )
        cap.verified_status = "pending"
        db_session.commit()
        session2 = diagnosis_service.create_session(
            db_session,
            test_user,
            model_id="epson_ecotank_l3250",
            symptom="卡纸",
            fault_category="paper_feed",
        )
        assert session2.status == "ESCALATED"

    def test_no_evidence_escalates(self, db_session, seeded, test_user, monkeypatch):
        monkeypatch.setattr(
            diagnosis_service.printer_rag_service,
            "retrieve",
            lambda *args, **kwargs: {"evidence_sufficient": False, "results": []},
        )
        session = diagnosis_service.create_session(
            db_session,
            test_user,
            model_id="hp_deskjet_2720",
            symptom="打印机卡纸了",
        )
        assert session.status == "ESCALATED"
        assert session.escalation_required

    def test_step_result_validation(self, db_session, seeded, test_user, platform_env):
        session = diagnosis_service.create_session(
            db_session,
            test_user,
            model_id="hp_deskjet_2720",
            symptom="卡纸 E4",
        )
        step = (
            db_session.query(DiagnosisStep)
            .filter_by(diagnosis_id=session.id, status="ready")
            .first()
        )
        with pytest.raises(ValueError):
            diagnosis_service.submit_step_result(db_session, session, 99999, "done")
        with pytest.raises(ValueError):
            diagnosis_service.submit_step_result(db_session, session, step.id, "invalid")

        session = diagnosis_service.submit_step_result(db_session, session, step.id, "done")
        assert session.status in {"WAIT_USER_ACTION", "STEP_READY"}


class TestKnowledgeIngestion:
    def test_helpers(self, tmp_path, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
        path, ext, checksum = knowledge_ingestion.save_upload("a.txt", b"hello")
        assert ext == "txt"
        assert checksum
        assert (tmp_path / "knowledge").exists()

        with pytest.raises(ValueError):
            knowledge_ingestion.save_upload("a.exe", b"x")
        monkeypatch.setattr(knowledge_ingestion, "MAX_IMPORT_SIZE", 1)
        with pytest.raises(ValueError):
            knowledge_ingestion.save_upload("b.txt", b"too large")

        html_path = tmp_path / "page.html"
        html_path.write_text(
            "<html><script>bad()</script><body><p>正文</p></body></html>", encoding="utf-8"
        )
        assert "正文" in knowledge_ingestion.extract_html_text(str(html_path))

        steps = knowledge_ingestion._normalize_steps(
            ["步骤一", {"instruction": "步骤二", "risk_level": "L2"}, ""]
        )
        assert len(steps) == 2
        assert steps[1]["risk_level"] == "L2"
        assert knowledge_ingestion._normalize_steps(None) == []

    def test_import_and_direct_create(self, tmp_path, monkeypatch, db_session, seeded):
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
        source = (
            db_session.query(KnowledgeSource).filter_by(source_key="src_hp_support_2700").first()
        )

        result = knowledge_ingestion.import_file(
            db_session,
            source=source,
            filename="data.jsonl",
            content=(
                '{"title":"导入一","model_scope":"DeskJet 2700 Series","fault_category":"paper_feed",'
                '"steps":["检查纸路"],"safety_warnings":["断电"]}\n'
                '{"title":"导入二","fault_category":"bad_category"}\n'
            ).encode(),
            brand_code="HP",
            model_scope="DeskJet 2700 Series",
        )
        assert result["created"] == 2

        with pytest.raises(ValueError):
            knowledge_ingestion.import_file(
                db_session,
                source=source,
                filename="x.txt",
                content=b"text",
                brand_code="",
                model_scope="",
            )

        item = knowledge_ingestion.create_knowledge_direct(
            db_session,
            {
                "title": "手工知识",
                "brand_code": "hp",
                "model_scope": "DeskJet 2700 Series",
                "fault_category": "invalid",
                "steps": [{"instruction": "检查"}],
                "safety_warnings": [],
            },
        )
        assert item.fault_category == "other"
        assert item.brand_code == "HP"
        assert item.content_hash


class TestKnowledgeReviewService:
    def test_validation_and_actions(self, db_session, seeded, test_admin):
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()
        assert knowledge_review.validate_for_publish(item) == []

        with pytest.raises(ValueError):
            knowledge_review.review_action(db_session, item, "rollback", test_admin)
        with pytest.raises(ValueError):
            knowledge_review.review_action(db_session, item, "unknown", test_admin)

        archived = knowledge_review.review_action(db_session, item, "archive", test_admin, "下架")
        assert archived["review_status"] == "archived"

    def test_rollback_with_history(self, db_session, seeded, test_admin):
        item = db_session.query(RepairKnowledge).filter_by(doc_id="rk_hp_paper").first()
        item.version_history = [
            {
                "title": "旧标题",
                "symptom": "旧现象",
                "possible_causes": [],
                "steps": [{"instruction": "旧步骤"}],
                "safety_warnings": ["旧提示"],
                "risk_level": "L1",
                "fault_category": "paper_feed",
                "fault_code": "E4",
                "version": "0.9",
            }
        ]
        db_session.commit()
        payload = knowledge_review.review_action(db_session, item, "rollback", test_admin)
        assert payload["title"] == "旧标题"
        assert payload["version"] == "0.9"


class TestTicketService:
    def test_mask_and_payload(self, db_session, seeded, test_user):
        assert ticket_service.mask_contact("a@b.com").endswith("@b.com")
        assert "***" in ticket_service.mask_contact("13800138000")
        assert ticket_service.mask_contact("123") == "***"
        assert ticket_service.mask_contact(None) is None

        ticket = ticket_service.create_ticket(
            db_session,
            test_user,
            title="测试",
            contact="13800138000",
            priority="high",
        )
        assert ticket.ticket_no.startswith("T")
        payload = ticket_service.ticket_payload(db_session, ticket, mask=True)
        assert payload["contact"] != "13800138000"

        with pytest.raises(ValueError):
            ticket_service.update_ticket(db_session, ticket, test_user, status="resolved")

        updated = ticket_service.update_ticket(
            db_session, ticket, test_user, status="assigned", note="分配"
        )
        assert updated.status == "assigned"

        event = ticket_service.add_user_message(db_session, ticket, test_user, "补充")
        assert event.event_type == "comment"

        closed = ticket_service.user_close(db_session, ticket, test_user, "完成")
        assert closed.status == "closed"

        other = ticket_service.create_ticket(db_session, test_user, title="另一个")
        other.user_id = test_user.id + 1
        db_session.commit()
        with pytest.raises(PermissionError):
            ticket_service.add_user_message(db_session, other, test_user, "无权")
        with pytest.raises(PermissionError):
            ticket_service.user_close(db_session, other, test_user)

    def test_list_filters(self, db_session, seeded, test_user):
        ticket_service.create_ticket(db_session, test_user, title="筛选工单", summary="x")
        assert ticket_service.list_tickets(db_session, test_user)
        assert ticket_service.list_all_tickets(db_session, keyword="筛选")
        assert ticket_service.list_all_tickets(db_session, status="pending")


class TestAuditHelpers:
    def test_dump(self):
        assert _dump(None) is None
        assert _dump("text") == "text"
        assert '"a": 1' in _dump({"a": 1})
        assert _dump(object())
