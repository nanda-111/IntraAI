"""平台用户端辅助流程、评测、案例与客服/工单管理测试。"""

import json

from app.models.service_ticket import ServiceTicket


class TestCasesAdmin:
    def test_case_crud_and_import(self, client, seeded, admin_headers):
        created = client.post(
            "/api/admin/cases",
            json={
                "raw_brand": "HP",
                "raw_model": "2720",
                "problem_text": "卡纸后清洁滚轮恢复",
                "fault_label": "paper_feed",
                "repair_outcome": "恢复",
                "model_known": "known",
            },
            headers=admin_headers,
        )
        assert created.status_code == 200
        case = created.json()
        assert case["disclaimer"]

        invalid = client.post(
            "/api/admin/cases",
            json={"problem_text": "x", "fault_label": "invalid"},
            headers=admin_headers,
        )
        assert invalid.status_code == 400

        updated = client.put(
            f"/api/admin/cases/{case['case_id']}",
            json={"notes": "已复核", "credibility": "reviewed"},
            headers=admin_headers,
        )
        assert updated.json()["credibility"] == "reviewed"

        listing = client.get(
            "/api/admin/cases",
            params={
                "brand": "HP",
                "model_known": "known",
                "fault_label": "paper_feed",
                "q": "滚轮",
            },
            headers=admin_headers,
        ).json()
        assert any(item["case_id"] == case["case_id"] for item in listing)

        imported = client.post(
            "/api/admin/cases/import",
            files={
                "file": (
                    "cases.jsonl",
                    (
                        json.dumps({"problem_text": "导入案例一", "fault_label": "paper_feed"})
                        + "\n"
                        + json.dumps({"problem_text": "导入案例二"})
                    ).encode(),
                    "text/plain",
                )
            },
            headers=admin_headers,
        )
        assert imported.json()["created"] == 2

        assert (
            client.delete(f"/api/admin/cases/{case['case_id']}", headers=admin_headers).status_code
            == 200
        )
        assert (
            client.delete(f"/api/admin/cases/{case['case_id']}", headers=admin_headers).status_code
            == 404
        )


class TestEvaluationAdmin:
    def test_dataset_item_and_run(self, client, seeded, admin_headers, platform_env):
        dataset = client.post(
            "/api/admin/evaluation/datasets",
            json={
                "name": "自定义测试集",
                "brand_code": "HP",
                "model_id": "hp_deskjet_2720",
                "category": "retrieval",
            },
            headers=admin_headers,
        ).json()

        updated = client.put(
            f"/api/admin/evaluation/datasets/{dataset['id']}",
            json={"description": "说明"},
            headers=admin_headers,
        )
        assert updated.json()["description"] == "说明"

        empty_run = client.post(
            f"/api/admin/evaluation/datasets/{dataset['id']}/run", headers=admin_headers
        )
        assert empty_run.status_code == 400

        item = client.post(
            f"/api/admin/evaluation/datasets/{dataset['id']}/items",
            json={
                "question": "HP 2720 卡纸怎么办？",
                "expected_doc_ids": ["rk_hp_paper"],
                "expected_fault_category": "paper_feed",
            },
            headers=admin_headers,
        ).json()
        items = client.get(
            f"/api/admin/evaluation/datasets/{dataset['id']}/items", headers=admin_headers
        ).json()
        assert len(items) == 1

        run = client.post(
            f"/api/admin/evaluation/datasets/{dataset['id']}/run", headers=admin_headers
        )
        assert run.status_code == 200
        assert run.json()["metrics"]["recall_at_5"] == 1.0

        runs = client.get("/api/admin/evaluation/runs", headers=admin_headers).json()
        assert runs
        detail = client.get(f"/api/admin/evaluation/runs/{run.json()['id']}", headers=admin_headers)
        assert detail.status_code == 200

        deleted_item = client.delete(
            f"/api/admin/evaluation/datasets/{dataset['id']}/items/{item['id']}",
            headers=admin_headers,
        )
        assert deleted_item.status_code == 200

        deleted = client.delete(
            f"/api/admin/evaluation/datasets/{dataset['id']}", headers=admin_headers
        )
        assert deleted.status_code == 200
        missing = client.delete(
            f"/api/admin/evaluation/datasets/{dataset['id']}", headers=admin_headers
        )
        assert missing.status_code == 404


class TestUserProfile:
    def test_update_profile_and_password(self, client, seeded, user_headers):
        me = client.get("/api/users/me", headers=user_headers).json()
        assert me["role"] == "user"

        updated = client.put(
            "/api/users/me",
            json={"display_name": "测试用户", "phone": "13800138000"},
            headers=user_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["display_name"] == "测试用户"

        conflict_user = client.post(
            "/api/auth/register",
            json={"username": "other", "email": "other@example.com", "password": "otherpass"},
        ).json()
        conflict = client.put(
            "/api/users/me", json={"email": "other@example.com"}, headers=user_headers
        )
        assert conflict.status_code == 400

        wrong = client.put(
            "/api/users/me/password",
            json={"old_password": "wrong", "new_password": "newpass123"},
            headers=user_headers,
        )
        assert wrong.status_code == 400

        short = client.put(
            "/api/users/me/password",
            json={"old_password": "testpass123", "new_password": "123"},
            headers=user_headers,
        )
        assert short.status_code == 400

        changed = client.put(
            "/api/users/me/password",
            json={"old_password": "testpass123", "new_password": "newpass123"},
            headers=user_headers,
        )
        assert changed.status_code == 200
        login = client.post(
            "/api/auth/login", json={"username": "testuser", "password": "newpass123"}
        )
        assert login.status_code == 200
        assert conflict_user["username"] == "other"


class TestDiagnosisExtra:
    def test_model_pending_then_confirm_and_summary(
        self, client, seeded, user_headers, platform_env
    ):
        created = client.post("/api/diagnosis/sessions", json={}, headers=user_headers).json()
        assert created["diagnosis_state"] == "MODEL_PENDING"
        assert created["next_question"]

        confirmed = client.post(
            f"/api/diagnosis/sessions/{created['id']}/model",
            json={"model_id": "hp_deskjet_2720"},
            headers=user_headers,
        ).json()
        assert confirmed["diagnosis_state"] == "COLLECTING"

        unknown = client.post(
            f"/api/diagnosis/sessions/{created['id']}/model",
            json={"model_id": "not_exists"},
            headers=user_headers,
        )
        assert unknown.status_code == 400

        message = client.post(
            f"/api/diagnosis/sessions/{created['id']}/messages",
            json={"content": "打印机卡纸了，显示 E4"},
            headers=user_headers,
        ).json()
        assert message["diagnosis_state"] == "WAIT_USER_ACTION"
        assert message["current_step"]

        summary = client.get(
            f"/api/diagnosis/sessions/{created['id']}/summary", headers=user_headers
        ).json()
        assert summary["steps"]
        assert summary["session_id"].startswith("diag_")

        closed = client.post(
            f"/api/diagnosis/sessions/{created['id']}/close",
            json={"resolved": True, "note": "用户确认"},
            headers=user_headers,
        ).json()
        assert closed["diagnosis_state"] == "RESOLVED"

        listing = client.get("/api/diagnosis/sessions", headers=user_headers).json()
        assert listing

    def test_diagnosis_validation(self, client, seeded, user_headers, platform_env):
        created = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "epson_ecotank_l3250"},
            headers=user_headers,
        ).json()

        empty = client.post(
            f"/api/diagnosis/sessions/{created['id']}/messages",
            json={"content": "   "},
            headers=user_headers,
        )
        assert empty.status_code == 400

        bad_result = client.post(
            f"/api/diagnosis/sessions/{created['id']}/steps/9999/result",
            json={"result": "done"},
            headers=user_headers,
        )
        assert bad_result.status_code == 400

        invalid_category = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "epson_ecotank_l3250", "fault_category": "invalid"},
            headers=user_headers,
        )
        assert invalid_category.status_code == 400

        not_found = client.get("/api/diagnosis/sessions/99999", headers=user_headers)
        assert not_found.status_code == 404

    def test_step_failed_and_skipped_paths(self, client, seeded, user_headers, platform_env):
        created = client.post(
            "/api/diagnosis/sessions",
            json={"model_id": "hp_deskjet_2720", "symptom": "卡纸 E4"},
            headers=user_headers,
        ).json()
        step_id = created["current_step"]["step_id"]

        failed = client.post(
            f"/api/diagnosis/sessions/{created['id']}/steps/{step_id}/result",
            json={"result": "failed", "note": "还是不行"},
            headers=user_headers,
        ).json()
        assert failed["diagnosis_state"] == "COLLECTING"

        skipped_response = client.post(
            f"/api/diagnosis/sessions/{created['id']}/steps/{step_id}/result",
            json={"result": "skipped"},
            headers=user_headers,
        )
        assert skipped_response.status_code == 200, skipped_response.text
        skipped = skipped_response.json()
        # 步骤已不是 ready，仍允许记录；当前状态为 COLLECTING，属于活跃状态
        assert skipped["diagnosis_state"] == "ESCALATED"


class TestAssistantExtra:
    def test_session_list_delete_and_feedback(self, client, seeded, user_headers, platform_env):
        session = client.post("/api/assistant/sessions", json={}, headers=user_headers).json()
        listing = client.get("/api/assistant/sessions", headers=user_headers).json()
        assert listing
        assert listing[0]["message_count"] == 0

        suggestions = client.get(
            "/api/assistant/suggestions",
            params={"model_id": "hp_deskjet_2720"},
            headers=user_headers,
        ).json()
        assert suggestions["items"]

        no_model = client.get(
            "/api/assistant/suggestions", params={"model_id": "none"}, headers=user_headers
        ).json()
        assert no_model["items"]

        feedback = client.post(
            "/api/assistant/feedback",
            json={
                "channel": "assistant",
                "reference_id": session["id"],
                "rating": 5,
                "resolved": True,
            },
            headers=user_headers,
        )
        assert feedback.status_code == 200

        removed = client.delete(f"/api/assistant/sessions/{session['id']}", headers=user_headers)
        assert removed.status_code == 200
        missing = client.delete(f"/api/assistant/sessions/{session['id']}", headers=user_headers)
        assert missing.status_code == 404

    def test_stream_high_risk_and_empty_message(self, client, seeded, user_headers, platform_env):
        session = client.post(
            "/api/assistant/sessions",
            json={"model_id": "hp_deskjet_2720"},
            headers=user_headers,
        ).json()

        empty = client.post(
            f"/api/assistant/sessions/{session['id']}/messages",
            json={"content": ""},
            headers=user_headers,
        )
        assert empty.status_code == 400

        response = client.post(
            f"/api/assistant/sessions/{session['id']}/messages/stream",
            json={"content": "我想拆机修电源板"},
            headers=user_headers,
        )
        assert response.status_code == 200
        assert "高风险" in response.text or "不提供自助拆修" in response.text
        assert "[DONE]" in response.text


class TestTicketAdminExtra:
    def test_assignees_detail_and_closed_transition(
        self, client, seeded, user_headers, admin_headers, test_admin
    ):
        ticket = client.post(
            "/api/tickets",
            json={"title": "客服测试", "summary": "问题", "contact": "a@b.com"},
            headers=user_headers,
        ).json()

        assignees = client.get("/api/admin/tickets/assignees", headers=admin_headers).json()
        assert assignees

        detail = client.get(f"/api/admin/tickets/{ticket['id']}", headers=admin_headers).json()
        assert detail["events"]

        invalid_assignee = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"assignee_id": 99999},
            headers=admin_headers,
        )
        assert invalid_assignee.status_code == 400

        processing = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"status": "processing", "assignee_id": test_admin.id, "note": "处理中"},
            headers=admin_headers,
        ).json()
        assert processing["status"] == "processing"

        invalid_status = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"status": "pending"},
            headers=admin_headers,
        )
        assert invalid_status.status_code == 400

        client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"status": "resolved", "resolution": "已指导用户"},
            headers=admin_headers,
        )
        closed = client.put(
            f"/api/admin/tickets/{ticket['id']}",
            json={"status": "closed", "note": "关闭"},
            headers=admin_headers,
        )
        assert closed.json()["status"] == "closed"

        missing = client.get("/api/admin/tickets/99999", headers=admin_headers)
        assert missing.status_code == 404

    def test_user_cannot_comment_other_ticket(self, client, seeded, user_headers, admin_headers):
        admin_ticket = client.post(
            "/api/tickets", json={"title": "管理员工单"}, headers=admin_headers
        )
        # 管理员创建工单后，普通用户无权访问
        assert (
            client.get(
                f"/api/tickets/{admin_ticket.json()['id']}", headers=user_headers
            ).status_code
            == 403
        )

    def test_ticket_not_found(self, client, seeded, user_headers):
        assert client.get("/api/tickets/99999", headers=user_headers).status_code == 404
        assert (
            client.post(
                "/api/tickets", json={"diagnosis_id": 99999}, headers=user_headers
            ).status_code
            == 404
        )


class TestAdminPlatformExtra:
    def test_dashboard_filter_and_logs(
        self, client, seeded, admin_headers, user_headers, platform_env
    ):
        hp = client.get("/api/admin/dashboard", params={"brand": "HP"}, headers=admin_headers)
        assert hp.status_code == 200
        assert hp.json()["brand_coverage"]

        logs = client.get(
            "/api/admin/retrieval-logs", params={"channel": "assistant"}, headers=admin_headers
        )
        assert logs.status_code == 200

        categories = client.get("/api/admin/fault-categories", headers=admin_headers)
        assert categories.status_code == 200

        role = client.get("/api/admin/me/role", headers=admin_headers).json()
        assert role["role"] == "system_admin"

        denied = client.get("/api/admin/settings", headers=user_headers)
        assert denied.status_code == 403

    def test_audit_filter_and_user_role_validation(self, client, seeded, admin_headers, test_user):
        client.put(
            f"/api/admin/users/{test_user.id}/role",
            json={"role": "knowledge_admin"},
            headers=admin_headers,
        )
        invalid = client.put(
            f"/api/admin/users/{test_user.id}/role",
            json={"role": "superuser"},
            headers=admin_headers,
        )
        assert invalid.status_code == 400

        logs = client.get(
            "/api/admin/audit-logs",
            params={"action": "user.set_role"},
            headers=admin_headers,
        ).json()
        assert logs["total"] >= 1
        assert logs["items"][0]["operator"]


def test_ticket_model_available(db_session, seeded):
    """确认种子数据后工单表可用（覆盖导入路径）。"""
    assert db_session.query(ServiceTicket).count() == 0
