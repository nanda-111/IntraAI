"""平台核心流程测试：品牌型号、知识、智能客服、诊断、工单、评测与权限。"""

import json

import pytest

from app.seed import seed_all


@pytest.fixture
def seeded(db_session):
    seed_all(db_session)
    return db_session


@pytest.fixture
def platform_env(monkeypatch):
    """隔离外部依赖：向量、重排序、LLM 与 Chroma 索引。"""
    from app.services import printer_rag_service as rag

    def fake_embeddings(texts):
        return [[0.1] * 768 for _ in texts]

    def fake_rerank(question, candidates, top_k=5):
        return [(text, meta, 0.9) for text, meta in candidates[:top_k]]

    def fake_completion(messages, model=None, temperature=0.3):
        return "", "根据已审核资料：请按下列步骤检查。"

    def fake_stream(messages, model=None, temperature=0.3):
        yield {"type": "answer", "content": "根据已审核资料："}
        yield {"type": "answer", "content": "请按步骤检查。"}

    monkeypatch.setattr(rag, "get_embeddings", fake_embeddings)
    monkeypatch.setattr(rag, "_vector_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(rag, "chat_completion", fake_completion)
    monkeypatch.setattr(rag, "chat_completion_stream", fake_stream)
    monkeypatch.setattr(rag, "index_knowledge", lambda db, item: True)
    monkeypatch.setattr("app.services.reranker.rerank", fake_rerank)
    return rag


class TestProductCatalog:
    def test_list_brands_and_models(self, client, seeded):
        response = client.get("/api/products/brands")
        assert response.status_code == 200
        brands = response.json()
        assert {brand["brand_code"] for brand in brands} == {"HP", "Canon", "Epson", "Brother"}
        assert all(brand["model_count"] >= 1 for brand in brands)

        models = client.get("/api/products/models", params={"q": "2720"}).json()
        assert models
        assert models[0]["model_id"] == "hp_deskjet_2720"
        assert models[0]["support_status"] == "active"

    def test_model_detail_and_capabilities(self, client, seeded):
        detail = client.get("/api/products/models/hp_deskjet_2700_series").json()
        assert detail["brand_code"] == "HP"
        assert detail["knowledge_coverage"] >= 1
        assert detail["sources"]
        categories = {item["fault_category"] for item in detail["capabilities"]}
        assert {"paper_feed", "ink_supply", "print_quality", "connectivity"} <= categories

        codes = client.get("/api/products/models/hp_deskjet_2700_series/error-codes").json()
        assert codes["brand_code"] == "HP"
        assert any(item["code"] == "E4" for item in codes["codes"])

    def test_devices_flow(self, client, seeded, user_headers):
        added = client.post(
            "/api/products/devices",
            json={"model_id": "hp_deskjet_2720", "set_current": True},
            headers=user_headers,
        )
        assert added.status_code == 200
        assert added.json()["is_current"] is True

        devices = client.get("/api/products/devices", headers=user_headers).json()
        assert len(devices) == 1
        assert devices[0]["model"]["model_id"] == "hp_deskjet_2720"

        second = client.post(
            "/api/products/devices",
            json={"model_id": "canon_pixma_ts5380", "set_current": False},
            headers=user_headers,
        )
        assert second.status_code == 200

        switched = client.post(
            "/api/products/devices/canon_pixma_ts5380/current", headers=user_headers
        )
        assert switched.status_code == 200
        assert switched.json()["is_current"] is True

        removed = client.delete("/api/products/devices/canon_pixma_ts5380", headers=user_headers)
        assert removed.status_code == 200


class TestKnowledgeCenter:
    def test_list_and_detail(self, client, seeded):
        response = client.get("/api/knowledge", params={"model_id": "hp_deskjet_2700_series"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] >= 4
        assert all(item["review_status"] == "published" for item in payload["items"])

        detail = client.get("/api/knowledge/rk_hp_paper").json()
        assert detail["fault_category"] == "paper_feed"
        assert detail["steps"]
        assert detail["safety_warnings"]
        assert detail["source"]["authority_level"] == "A"

    def test_filter_by_category_and_code(self, client, seeded):
        payload = client.get(
            "/api/knowledge",
            params={"model_id": "canon_pixma_ts5300_series", "fault_category": "paper_feed"},
        ).json()
        assert payload["total"] == 1
        assert payload["items"][0]["doc_id"] == "rk_canon_paper"


class TestAssistant:
    def test_chat_with_sources(self, client, seeded, user_headers, platform_env):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "epson_ecotank_l3250"},
            headers=user_headers,
        ).json()
        response = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": "Epson L3250 卡纸了怎么处理？"},
            headers=user_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["message"]["sources"]
        assert body["message"]["evidence_sufficient"] is True
        assert "已审核" in body["message"]["content"]

        detail = client.get(f"/api/assistant/sessions/{session['id']}", headers=user_headers).json()
        assert len(detail["messages"]) == 2

    def test_stream_response(self, client, seeded, user_headers, platform_env):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "brother_dcp_t420w"},
            headers=user_headers,
        ).json()
        response = client.post(
            f"/api/assistant/sessions/{session['id']}/messages/stream",
            json={"content": "兄弟打印机卡纸怎么办？"},
            headers=user_headers,
        )
        assert response.status_code == 200
        text = response.text
        assert '"type": "meta"' in text
        assert '"type": "answer"' in text
        assert "[DONE]" in text

    def test_category_filtered_sources(self, client, seeded, user_headers, platform_env):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "hp_deskjet_2720"},
            headers=user_headers,
        ).json()
        body = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": "HP 2720 显示 E4 卡纸怎么处理？"},
            headers=user_headers,
        ).json()
        sources = body["message"]["sources"]
        assert sources
        assert all(item["fault_category"] == "paper_feed" for item in sources)
        assert all(item["doc_id"].startswith("rk_hp_") for item in sources)

    def test_generic_trouble_asks_for_details(self, client, seeded, user_headers, platform_env):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "canon_pixma_ts5380"},
            headers=user_headers,
        ).json()
        body = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": "打印机不能打印怎么办"},
            headers=user_headers,
        ).json()
        assert body["message"]["intent"] == "clarification"
        assert body["message"]["sources"] == []
        assert "具体现象" in body["message"]["content"]

    def test_high_risk_is_refused(self, client, seeded, user_headers, platform_env):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "hp_deskjet_2720"},
            headers=user_headers,
        ).json()
        body = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": "我想拆机短接电源板，请告诉我步骤"},
            headers=user_headers,
        ).json()
        assert body["message"]["intent"] == "clarification"
        assert "不提供自助拆修" in body["message"]["content"]
        assert body["message"]["sources"] == []

    def test_session_isolation(self, client, seeded, user_headers, admin_headers, platform_env):
        session = client.post("/api/assistant/sessions", json={}, headers=user_headers).json()
        forbidden = client.get(f"/api/assistant/sessions/{session['id']}", headers=admin_headers)
        assert forbidden.status_code == 403


class TestDiagnosis:
    def test_full_diagnosis_flow(self, client, seeded, user_headers, platform_env):
        created = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "hp_deskjet_2720", "symptom": "打印机卡纸了，显示 E4"},
            headers=user_headers,
        )
        assert created.status_code == 200
        body = created.json()
        assert body["diagnosis_state"] == "WAIT_USER_ACTION"
        assert body["product"]["model_id"] == "hp_deskjet_2720"
        assert body["fault"]["category"] == "paper_feed"
        assert body["current_step"]["step_no"] == 1
        assert body["sources"]
        step_id = body["current_step"]["step_id"]

        result = client.post(
            f"/api/diagnosis/sessions/{body['id']}/steps/{step_id}/result",
            json={"result": "done", "note": "已按说明操作"},
            headers=user_headers,
        )
        assert result.status_code == 200
        after = result.json()
        assert after["steps"][0]["status"] == "done"
        assert after["current_step"]["step_no"] == 2

        resolved = client.post(
            f"/api/diagnosis/sessions/{body['id']}/messages",
            json={"content": "已解决，可以打印了"},
            headers=user_headers,
        )
        assert resolved.status_code == 200
        assert resolved.json()["diagnosis_state"] == "RESOLVED"
        assert resolved.json()["resolved"] is True

    def test_unsupported_model_blocks_diagnosis(self, client, seeded, user_headers, db_session):
        from app.models.printer_brand import ProductModel

        model = db_session.query(ProductModel).filter_by(model_id="canon_pixma_ts5380").first()
        model.support_status = "building"
        db_session.commit()

        body = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "canon_pixma_ts5380", "symptom": "卡纸"},
            headers=user_headers,
        ).json()
        assert body["diagnosis_state"] == "ESCALATED"
        assert body["escalation_required"] is True

    def test_high_risk_escalation(self, client, seeded, user_headers, platform_env):
        body = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "epson_ecotank_l3250", "symptom": "打印有断线"},
            headers=user_headers,
        ).json()
        escalated = client.post(
            f"/api/diagnosis/sessions/{body['id']}/messages",
            json={"content": "我想拆开外壳自己修电路板"},
            headers=user_headers,
        ).json()
        assert escalated["diagnosis_state"] == "ESCALATED"
        assert escalated["escalation_required"] is True

    def test_diagnosis_isolation(self, client, seeded, user_headers, admin_headers, platform_env):
        body = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "brother_dcp_t420w", "symptom": "不进纸"},
            headers=user_headers,
        ).json()
        forbidden = client.get(f"/api/diagnosis/sessions/{body['id']}", headers=admin_headers)
        assert forbidden.status_code == 403


class TestTickets:
    def _create_escalated_diagnosis(self, client, headers):
        body = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "brother_dcp_t420w", "symptom": "卡纸"},
            headers=headers,
        ).json()
        client.post(
            f"/api/diagnosis/sessions/{body['id']}/messages",
            json={"content": "我要转人工"},
            headers=headers,
        )
        return body["id"]

    def test_ticket_creation_and_admin_flow(
        self, client, seeded, user_headers, admin_headers, test_admin, platform_env
    ):
        diagnosis_id = self._create_escalated_diagnosis(client, user_headers)
        created = client.post(
            "/api/tickets",
            json={
                "diagnosis_id": diagnosis_id,
                "contact": "13800138000",
                "priority": "high",
            },
            headers=user_headers,
        )
        assert created.status_code == 200
        ticket = created.json()
        assert ticket["ticket_no"].startswith("T")
        assert ticket["status"] == "pending"
        assert ticket["executed_steps"]

        listed = client.get("/api/tickets", headers=user_headers).json()
        assert len(listed) == 1

        assigned = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"assignee_id": test_admin.id, "status": "assigned", "note": "已分配"},
            headers=admin_headers,
        )
        assert assigned.status_code == 200
        assert assigned.json()["status"] == "assigned"
        assert assigned.json()["contact"].startswith("138***")

        processing = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"status": "processing", "note": "正在处理", "internal": True},
            headers=admin_headers,
        )
        assert processing.status_code == 200
        assert processing.json()["status"] == "processing"

        comment = client.post(
            f"/api/tickets/{ticket['id']}/comments",
            json={"content": "补充：重启后仍然卡纸"},
            headers=user_headers,
        )
        assert comment.status_code == 200

        closed = client.post(
            f"/api/tickets/{ticket['id']}/close",
            json={"note": "用户确认已解决"},
            headers=user_headers,
        )
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"

    def test_ticket_isolation(self, client, seeded, user_headers, admin_headers, platform_env):
        ticket = client.post(
            "/api/tickets", json={"title": "测试工单", "contact": "a@b.com"}, headers=user_headers
        ).json()
        forbidden = client.get(f"/api/tickets/{ticket['id']}", headers=admin_headers)
        assert forbidden.status_code == 403

    def test_invalid_status_transition(self, client, seeded, user_headers, admin_headers):
        ticket = client.post(
            "/api/tickets", json={"title": "测试工单"}, headers=user_headers
        ).json()
        response = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"status": "resolved"},
            headers=admin_headers,
        )
        assert response.status_code == 400


class TestKnowledgeAdmin:
    def _create_source(self, client, admin_headers):
        return client.post(
            "/api/admin/knowledge/sources",
            json={
                "title": "测试官方来源",
                "url": "https://example.com/manual",
                "authority_level": "A",
                "brand_code": "HP",
                "model_scope": "DeskJet 2700 Series",
            },
            headers=admin_headers,
        ).json()

    def test_review_publish_flow(self, client, seeded, user_headers, admin_headers, platform_env):
        source = self._create_source(client, admin_headers)
        created = client.post(
            "/api/admin/knowledge",
            json={
                "title": "测试知识条目",
                "source_id": source["id"],
                "brand_code": "HP",
                "model_scope": "hp_deskjet_2700_series",
                "fault_category": "paper_feed",
                "fault_code": "E4",
                "symptom": "测试卡纸现象",
                "steps": [
                    {"instruction": "检查纸路", "risk_level": "L1", "expected_result": "无残纸"}
                ],
                "safety_warnings": ["断电后检查"],
                "source_type": "faq",
                "authority_level": "C",
            },
            headers=admin_headers,
        )
        assert created.status_code == 200
        doc_id = created.json()["doc_id"]

        approved = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "approve", "note": "内容核对通过"},
            headers=admin_headers,
        )
        assert approved.status_code == 200
        assert approved.json()["review_status"] == "approved"

        published = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "publish"},
            headers=admin_headers,
        )
        assert published.status_code == 200
        assert published.json()["review_status"] == "published"

        public = client.get("/api/knowledge", params={"q": "测试知识条目"}).json()
        assert any(item["doc_id"] == doc_id for item in public["items"])

    def test_user_cannot_manage_knowledge(self, client, seeded, user_headers):
        response = client.post(
            "/api/admin/knowledge/sources", json={"title": "x"}, headers=user_headers
        )
        assert response.status_code == 403

    def test_publish_requires_steps(self, client, seeded, admin_headers, platform_env):
        source = self._create_source(client, admin_headers)
        created = client.post(
            "/api/admin/knowledge",
            json={
                "title": "空步骤知识",
                "source_id": source["id"],
                "brand_code": "HP",
                "model_scope": "hp_deskjet_2700_series",
                "fault_category": "paper_feed",
                "steps": [],
                "safety_warnings": [],
                "source_type": "faq",
                "authority_level": "C",
            },
            headers=admin_headers,
        ).json()
        response = client.post(
            f"/api/admin/knowledge/{created['doc_id']}/review",
            json={"action": "approve"},
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "步骤" in response.json()["detail"]


class TestEvaluationAndDashboard:
    def test_evaluation_run(self, client, seeded, admin_headers, platform_env):
        datasets = client.get("/api/admin/evaluation/datasets", headers=admin_headers).json()
        assert len(datasets) >= 5
        hp_dataset = next(item for item in datasets if item["brand_code"] == "HP")

        run = client.post(
            f"/api/admin/evaluation/datasets/{hp_dataset['id']}/run", headers=admin_headers
        )
        assert run.status_code == 200
        payload = run.json()
        assert payload["status"] == "finished"
        assert payload["metrics"]["recall_at_5"] == 1.0
        assert payload["metrics"]["mrr_at_5"] > 0
        assert len(payload["results"]) == 5

    def test_safety_dataset(self, client, seeded, admin_headers, platform_env):
        datasets = client.get("/api/admin/evaluation/datasets", headers=admin_headers).json()
        safety = next(item for item in datasets if item["category"] == "safety")
        run = client.post(
            f"/api/admin/evaluation/datasets/{safety['id']}/run", headers=admin_headers
        ).json()
        assert run["metrics"]["escalation_recall"] == 1.0

    def test_dashboard(self, client, seeded, admin_headers, user_headers):
        response = client.get("/api/admin/dashboard", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["models"]["total"] == 9
        assert payload["knowledge"]["total"] == 24
        assert payload["knowledge"]["published"] == 24
        assert payload["brand_coverage"]

        denied = client.get("/api/admin/dashboard", headers=user_headers)
        assert denied.status_code == 403

    def test_role_permissions(self, client, seeded, admin_headers, test_user):
        response = client.put(
            f"/api/admin/users/{test_user.id}/role",
            json={"role": "agent"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "agent"

        from app.core.security import create_access_token

        token = create_access_token({"sub": test_user.username})
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/admin/tickets", headers=headers).status_code == 200
        denied = client.post("/api/admin/knowledge/sources", json={"title": "x"}, headers=headers)
        assert denied.status_code == 403

    def test_system_settings_hide_secrets(self, client, seeded, admin_headers):
        response = client.get("/api/admin/settings", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert "api_key_configured" in payload["llm"]
        assert "api_key" not in payload["llm"]
        assert json.dumps(payload)  # 可序列化
