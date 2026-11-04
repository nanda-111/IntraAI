"""平台管理端与辅助流程测试。"""

import json


def _hp_source_id(client, admin_headers):
    sources = client.get("/api/admin/knowledge/sources", headers=admin_headers).json()
    return next(item["id"] for item in sources if item["brand_code"] == "HP")


def _create_knowledge(client, admin_headers, source_id, **overrides):
    payload = {
        "title": "测试维修知识",
        "source_id": source_id,
        "brand_code": "HP",
        "model_scope": "DeskJet 2700 Series",
        "fault_category": "paper_feed",
        "fault_code": "E4",
        "symptom": "测试卡纸",
        "steps": [{"instruction": "检查纸路", "risk_level": "L1", "expected_result": "无残纸"}],
        "safety_warnings": ["断电后检查"],
        "source_type": "faq",
        "authority_level": "C",
        "review_status": "draft",
    }
    payload.update(overrides)
    return client.post("/api/admin/knowledge", json=payload, headers=admin_headers)


class TestProductAdmin:
    def test_brand_crud(self, client, seeded, admin_headers):
        created = client.post(
            "/api/admin/products/brands",
            json={"brand_code": "Test", "name": "测试品牌", "description": "说明"},
            headers=admin_headers,
        )
        assert created.status_code == 200
        brand = created.json()
        assert brand["brand_code"] == "TEST"

        duplicate = client.post(
            "/api/admin/products/brands",
            json={"brand_code": "TEST", "name": "重复"},
            headers=admin_headers,
        )
        assert duplicate.status_code == 400

        updated = client.put(
            f"/api/admin/products/brands/{brand['id']}",
            json={"name": "测试品牌更新", "status": "inactive"},
            headers=admin_headers,
        )
        assert updated.json()["name"] == "测试品牌更新"
        assert updated.json()["status"] == "inactive"

    def test_model_lifecycle(self, client, seeded, admin_headers, platform_env):
        # 新建 active 型号但缺少能力/知识 → 自动降级为 building 并返回警告
        created = client.post(
            "/api/admin/products/models",
            json={
                "model_id": "hp_test_model",
                "brand_code": "HP",
                "series": "Test Series",
                "name": "HP Test",
                "support_status": "active",
            },
            headers=admin_headers,
        ).json()
        assert created["warning"]
        assert created["model"]["support_status"] == "building"

        updated = client.put(
            "/api/admin/products/models/hp_test_model",
            json={"name": "HP Test 更新", "support_status": "planned", "aliases": ["测试型号"]},
            headers=admin_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "HP Test 更新"

        cap = client.post(
            "/api/admin/products/models/hp_test_model/capabilities",
            json={
                "fault_category": "paper_feed",
                "code_system": "HP 错误代码",
                "verified_status": "verified",
            },
            headers=admin_headers,
        )
        assert cap.status_code == 200
        cap_id = cap.json()["capabilities"][0]["id"]

        duplicate_cap = client.post(
            "/api/admin/products/models/hp_test_model/capabilities",
            json={"fault_category": "paper_feed"},
            headers=admin_headers,
        )
        assert duplicate_cap.status_code == 400

        cap_updated = client.put(
            f"/api/admin/products/capabilities/{cap_id}",
            json={"notes": "复核通过"},
            headers=admin_headers,
        )
        assert cap_updated.status_code == 200

        source_id = _hp_source_id(client, admin_headers)
        knowledge = _create_knowledge(
            client,
            admin_headers,
            source_id,
            model_scope="hp_test_model",
            review_status="published",
        ).json()
        assert knowledge["review_status"] == "published"

        activated = client.put(
            "/api/admin/products/models/hp_test_model",
            json={"support_status": "active"},
            headers=admin_headers,
        )
        assert activated.status_code == 200
        assert activated.json()["support_status"] == "active"

        models = client.get(
            "/api/products/models",
            params={"brand": "HP", "status": "active", "q": "Test"},
        )
        assert models.status_code == 200
        assert any(item["model_id"] == "hp_test_model" for item in models.json())

        detail = client.get("/api/products/models", params={"series": "Test"})
        assert detail.status_code == 200

        deleted_cap = client.delete(
            f"/api/admin/products/capabilities/{cap_id}", headers=admin_headers
        )
        assert deleted_cap.status_code == 200

        deleted = client.delete("/api/admin/products/models/hp_test_model", headers=admin_headers)
        assert deleted.status_code == 200
        missing = client.delete("/api/admin/products/models/hp_test_model", headers=admin_headers)
        assert missing.status_code == 404

    def test_device_current_fallback(self, client, seeded, user_headers):
        client.post(
            "/api/products/devices",
            json={"model_id": "hp_deskjet_2720", "set_current": True},
            headers=user_headers,
        )
        client.post(
            "/api/products/devices",
            json={"model_id": "epson_ecotank_l3250", "set_current": False},
            headers=user_headers,
        )
        removed = client.delete("/api/products/devices/hp_deskjet_2720", headers=user_headers)
        assert removed.status_code == 200
        devices = client.get("/api/products/devices", headers=user_headers).json()
        assert devices[0]["model_id"] == "epson_ecotank_l3250"
        assert devices[0]["is_current"] is True


class TestKnowledgeAdminOps:
    def test_source_crud_and_delete_guard(self, client, seeded, admin_headers, platform_env):
        created = client.post(
            "/api/admin/knowledge/sources",
            json={
                "title": "测试来源",
                "url": "https://example.com",
                "brand_code": "HP",
                "model_scope": "DeskJet 2700 Series",
                "authority_level": "A",
            },
            headers=admin_headers,
        ).json()
        assert created["source_key"].startswith("src_")

        updated = client.put(
            f"/api/admin/knowledge/sources/{created['id']}",
            json={"title": "测试来源更新", "authority_level": "C", "version": "2.0"},
            headers=admin_headers,
        )
        assert updated.json()["title"] == "测试来源更新"

        knowledge = _create_knowledge(
            client, admin_headers, created["id"], review_status="published"
        ).json()
        blocked = client.delete(
            f"/api/admin/knowledge/sources/{created['id']}", headers=admin_headers
        )
        assert blocked.status_code == 400

        empty_source = client.post(
            "/api/admin/knowledge/sources",
            json={"title": "空来源", "brand_code": "HP", "authority_level": "A"},
            headers=admin_headers,
        ).json()
        assert (
            client.delete(
                f"/api/admin/knowledge/sources/{empty_source['id']}", headers=admin_headers
            ).status_code
            == 200
        )

        missing = client.put(
            "/api/admin/knowledge/sources/99999", json={"title": "x"}, headers=admin_headers
        )
        assert missing.status_code == 404
        assert knowledge["review_status"] == "published"

    def test_import_txt_duplicate_and_failure(self, client, seeded, admin_headers, platform_env):
        source_id = _hp_source_id(client, admin_headers)
        base = {
            "source_id": str(source_id),
            "brand_code": "HP",
            "model_scope": "DeskJet 2700 Series",
            "fault_category": "paper_feed",
        }
        response = client.post(
            "/api/admin/knowledge/import",
            data=base,
            files={"file": ("manual.txt", "第一段内容。\n\n第二段内容。".encode(), "text/plain")},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["parse_status"] == "parsed"
        assert response.json()["created"] >= 1

        duplicate = client.post(
            "/api/admin/knowledge/import",
            data=base,
            files={"file": ("manual.txt", "第一段内容。\n\n第二段内容。".encode(), "text/plain")},
            headers=admin_headers,
        ).json()
        assert duplicate["duplicate"] is True

        bad_type = client.post(
            "/api/admin/knowledge/import",
            data=base,
            files={"file": ("bad.exe", b"binary", "application/octet-stream")},
            headers=admin_headers,
        )
        assert bad_type.status_code == 400

        invalid_category = client.post(
            "/api/admin/knowledge/import",
            data={**base, "fault_category": "invalid"},
            files={"file": ("other.txt", b"text", "text/plain")},
            headers=admin_headers,
        )
        assert invalid_category.status_code == 400

        missing_source = client.post(
            "/api/admin/knowledge/import",
            data={**base, "source_id": "99999"},
            files={"file": ("other2.txt", b"text", "text/plain")},
            headers=admin_headers,
        )
        assert missing_source.status_code == 404

    def test_import_structured_and_parse_failure(self, client, seeded, admin_headers, platform_env):
        source_id = _hp_source_id(client, admin_headers)
        record = {
            "title": "JSON 导入知识",
            "model_scope": "DeskJet 2700 Series",
            "fault_category": "paper_feed",
            "symptom": "JSON 卡纸",
            "steps": ["检查纸路", {"instruction": "重新装纸", "risk_level": "L1"}],
            "safety_warnings": ["断电检查"],
        }
        response = client.post(
            "/api/admin/knowledge/import",
            data={
                "source_id": str(source_id),
                "brand_code": "HP",
                "model_scope": "DeskJet 2700 Series",
            },
            files={"file": ("knowledge.json", json.dumps([record]).encode(), "application/json")},
            headers=admin_headers,
        ).json()
        assert response["created"] == 1
        doc_id = response["items"][0]["doc_id"]
        detail = client.get(f"/api/admin/knowledge/{doc_id}", headers=admin_headers).json()
        assert len(detail["steps"]) == 2

        failed = client.post(
            "/api/admin/knowledge/import",
            data={
                "source_id": str(source_id),
                "brand_code": "HP",
                "model_scope": "DeskJet 2700 Series",
            },
            files={"file": ("broken.json", b"{not json", "application/json")},
            headers=admin_headers,
        ).json()
        assert failed["parse_status"] == "failed"

        documents = client.get("/api/admin/knowledge/documents", headers=admin_headers).json()
        assert documents
        filtered = client.get(
            "/api/admin/knowledge/documents",
            params={"parse_status": "failed"},
            headers=admin_headers,
        ).json()
        assert any(item["parse_status"] == "failed" for item in filtered)

    def test_knowledge_review_lifecycle_and_rollback(
        self, client, seeded, admin_headers, platform_env
    ):
        source_id = _hp_source_id(client, admin_headers)
        created = _create_knowledge(client, admin_headers, source_id).json()
        doc_id = created["doc_id"]

        # 未审核不能发布
        early = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "publish"},
            headers=admin_headers,
        )
        assert early.status_code == 400

        updated = client.put(
            f"/api/admin/knowledge/{doc_id}",
            json={"title": "修改后的标题", "version": "2.0"},
            headers=admin_headers,
        )
        assert updated.json()["title"] == "修改后的标题"
        assert updated.json()["version_history"]

        rollback = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "rollback"},
            headers=admin_headers,
        )
        assert rollback.json()["title"] == "测试维修知识"

        approved = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "approve", "note": "通过"},
            headers=admin_headers,
        )
        assert approved.json()["review_status"] == "approved"

        published = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "publish"},
            headers=admin_headers,
        )
        assert published.json()["review_status"] == "published"

        rejected = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "reject", "note": "退回"},
            headers=admin_headers,
        )
        assert rejected.json()["review_status"] == "rejected"

        archived = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "archive"},
            headers=admin_headers,
        )
        assert archived.json()["review_status"] == "archived"

        invalid_action = client.post(
            f"/api/admin/knowledge/{doc_id}/review",
            json={"action": "unknown"},
            headers=admin_headers,
        )
        assert invalid_action.status_code == 400

    def test_review_validation_and_delete(self, client, seeded, admin_headers, platform_env):
        source_id = _hp_source_id(client, admin_headers)
        empty_steps = _create_knowledge(
            client, admin_headers, source_id, steps=[], safety_warnings=[]
        ).json()
        response = client.post(
            f"/api/admin/knowledge/{empty_steps['doc_id']}/review",
            json={"action": "approve"},
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "步骤" in response.json()["detail"]

        high_risk = _create_knowledge(client, admin_headers, source_id, risk_level="L3").json()
        blocked = client.post(
            f"/api/admin/knowledge/{high_risk['doc_id']}/review",
            json={"action": "approve"},
            headers=admin_headers,
        )
        assert blocked.status_code == 400

        deleted = client.delete(
            f"/api/admin/knowledge/{empty_steps['doc_id']}", headers=admin_headers
        )
        assert deleted.status_code == 200
        missing = client.delete(
            f"/api/admin/knowledge/{empty_steps['doc_id']}", headers=admin_headers
        )
        assert missing.status_code == 404

    def test_knowledge_list_filters_and_public_visibility(
        self, client, seeded, admin_headers, platform_env
    ):
        source_id = _hp_source_id(client, admin_headers)
        item = _create_knowledge(
            client, admin_headers, source_id, title="筛选目标知识", review_status="published"
        ).json()
        listing = client.get(
            "/api/admin/knowledge",
            params={
                "status": "published",
                "brand": "HP",
                "fault_category": "paper_feed",
                "q": "筛选",
            },
            headers=admin_headers,
        ).json()
        assert listing["total"] >= 1
        assert any(entry["doc_id"] == item["doc_id"] for entry in listing["items"])

        public = client.get(
            "/api/knowledge",
            params={"q": "筛选目标知识", "source_type": "faq", "fault_code": "E4", "region": "CN"},
        ).json()
        assert any(entry["doc_id"] == item["doc_id"] for entry in public["items"])

        client.post(
            f"/api/admin/knowledge/{item['doc_id']}/review",
            json={"action": "archive"},
            headers=admin_headers,
        )
        gone = client.get(f"/api/knowledge/{item['doc_id']}")
        assert gone.status_code == 404

    def test_index_and_meta_endpoints(self, client, seeded, admin_headers, platform_env):
        status = client.get("/api/admin/knowledge/index-status", headers=admin_headers)
        assert status.status_code == 200
        reindex = client.post("/api/admin/knowledge/reindex", headers=admin_headers)
        assert reindex.status_code == 200
        meta = client.get("/api/admin/knowledge/meta/categories", headers=admin_headers)
        assert meta.status_code == 200
        assert meta.json()["fault_categories"]
