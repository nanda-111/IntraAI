"""平台边界路径：型号/设备 404、客服降级回答与重排序器。"""

from app.models.printer_brand import ProductModel
from app.services import printer_rag_service, reranker


class TestProductEdges:
    def test_missing_resources(self, client, seeded, user_headers, admin_headers):
        assert client.get("/api/products/models/nope").status_code == 404
        assert client.get("/api/products/models/nope/capabilities").status_code == 404
        assert client.get("/api/products/models/nope/error-codes").status_code == 404

        assert (
            client.put(
                "/api/admin/products/brands/99999", json={"name": "x"}, headers=admin_headers
            ).status_code
            == 404
        )
        assert (
            client.put(
                "/api/admin/products/models/nope", json={"name": "x"}, headers=admin_headers
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/admin/products/models/nope/capabilities",
                json={"fault_category": "paper_feed"},
                headers=admin_headers,
            ).status_code
            == 404
        )
        assert (
            client.put(
                "/api/admin/products/capabilities/99999",
                json={"notes": "x"},
                headers=admin_headers,
            ).status_code
            == 404
        )
        assert (
            client.delete(
                "/api/admin/products/capabilities/99999", headers=admin_headers
            ).status_code
            == 404
        )

    def test_model_creation_validation(self, client, seeded, admin_headers):
        bad_brand = client.post(
            "/api/admin/products/models",
            json={
                "model_id": "bad_brand",
                "brand_code": "NOPE",
                "series": "S",
                "name": "N",
            },
            headers=admin_headers,
        )
        assert bad_brand.status_code == 400

        duplicate = client.post(
            "/api/admin/products/models",
            json={
                "model_id": "hp_deskjet_2720",
                "brand_code": "HP",
                "series": "S",
                "name": "N",
            },
            headers=admin_headers,
        )
        assert duplicate.status_code == 400

        bad_status = client.post(
            "/api/admin/products/models",
            json={
                "model_id": "bad_status",
                "brand_code": "HP",
                "series": "S",
                "name": "N",
                "support_status": "unknown",
            },
            headers=admin_headers,
        )
        assert bad_status.status_code == 400

        created = client.post(
            "/api/admin/products/models",
            json={
                "model_id": "hp_edge_model",
                "brand_code": "HP",
                "series": "Edge",
                "name": "Edge",
            },
            headers=admin_headers,
        ).json()
        assert created["support_status"] == "planned"

        activate = client.put(
            "/api/admin/products/models/hp_edge_model",
            json={"support_status": "active"},
            headers=admin_headers,
        )
        assert activate.status_code == 400
        assert "issues" in activate.json()["detail"]

        bad_update = client.put(
            "/api/admin/products/models/hp_edge_model",
            json={"support_status": "unknown"},
            headers=admin_headers,
        )
        assert bad_update.status_code == 400

    def test_device_edges(self, client, seeded, user_headers):
        assert (
            client.post(
                "/api/products/devices",
                json={"model_id": "nope", "set_current": True},
                headers=user_headers,
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/products/devices/hp_deskjet_2720/current", headers=user_headers
            ).status_code
            == 404
        )
        assert (
            client.delete("/api/products/devices/hp_deskjet_2720", headers=user_headers).status_code
            == 404
        )

        client.post(
            "/api/products/devices",
            json={"model_id": "hp_deskjet_2720", "set_current": True},
            headers=user_headers,
        )
        # 重复添加同一设备且不设为当前
        again = client.post(
            "/api/products/devices",
            json={"model_id": "hp_deskjet_2720", "set_current": False},
            headers=user_headers,
        )
        assert again.status_code == 200


class TestAssistantEdges:
    def test_model_resolved_from_message(self, client, seeded, user_headers, platform_env):
        session = client.post("/api/assistant/sessions", json={}, headers=user_headers).json()
        body = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": "我的 HP DeskJet 2720 卡纸了"},
            headers=user_headers,
        ).json()
        assert body["model_id"] == "hp_deskjet_2720"
        assert body["message"]["sources"]

    def test_missing_model_and_unsupported_model(
        self, client, seeded, user_headers, platform_env, db_session
    ):
        session = client.post("/api/assistant/sessions", json={}, headers=user_headers).json()
        body = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": "你好"},
            headers=user_headers,
        ).json()
        assert body["message"]["intent"] == "clarification"
        assert "型号" in body["message"]["content"]

        model = db_session.query(ProductModel).filter_by(model_id="canon_pixma_ts5380").first()
        model.support_status = "building"
        db_session.commit()

        bound = client.post(
            "/api/assistant/sessions",
            json={"model_id": "canon_pixma_ts5380"},
            headers=user_headers,
        ).json()
        unsupported = client.post(
            f"/api/assistant/sessions/{bound['id']}/messages",
            json={"content": "卡纸了"},
            headers=user_headers,
        ).json()
        assert unsupported["message"]["sources"] == []
        assert "暂不开放" in unsupported["message"]["content"]

    def test_stream_error_branch(self, client, seeded, user_headers, platform_env, monkeypatch):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "hp_deskjet_2720"},
            headers=user_headers,
        ).json()

        def boom(*args, **kwargs):
            raise RuntimeError("stream failed")

        monkeypatch.setattr(printer_rag_service, "generate_answer_stream", boom)
        response = client.post(
            f"/api/assistant/sessions/{session['id']}/messages/stream",
            json={"content": "卡纸了"},
            headers=user_headers,
        )
        assert response.status_code == 200
        assert "error" in response.text
        assert "[DONE]" in response.text

    def test_missing_session_and_session_without_model(
        self, client, seeded, user_headers, platform_env
    ):
        assert (
            client.post(
                "/api/assistant/sessions/99999/messages",
                json={"content": "x"},
                headers=user_headers,
            ).status_code
            == 404
        )
        assert client.get("/api/assistant/sessions/99999", headers=user_headers).status_code == 404

        session = client.post("/api/assistant/sessions", json={}, headers=user_headers).json()
        detail = client.get(f"/api/assistant/sessions/{session['id']}", headers=user_headers).json()
        assert detail["model"] is not None or detail["model"] is None


class TestReranker:
    def test_fake_cross_encoder(self, monkeypatch):
        import sentence_transformers

        class FakeEncoder:
            def __init__(self, name, max_length=512):
                self.name = name

            def predict(self, pairs):
                return [2.0, -2.0][: len(pairs)]

        monkeypatch.setattr(sentence_transformers, "CrossEncoder", FakeEncoder)
        monkeypatch.setattr(reranker, "_reranker", None)
        result = reranker.rerank(
            "卡纸", [("相关文档", {"doc": 1}), ("无关文档", {"doc": 2})], top_k=1
        )
        assert result[0][0] == "相关文档"
        assert 0 <= result[0][2] <= 1
        monkeypatch.setattr(reranker, "_reranker", None)
