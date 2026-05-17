#!/usr/bin/env bash
# =============================================================================
# 部署验证脚本
# 用途：部署后自动验证核心 API 是否正常工作
# 用法：./scripts/verify-deploy.sh [BASE_URL]
# 示例：./scripts/verify-deploy.sh http://localhost:8000
# =============================================================================

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0
TIMESTAMP=$(date +%s)
USERNAME="verify_user_${TIMESTAMP}"
PASSWORD="verify123"

# 颜色输出
green() { echo -e "\033[32m✓ $1\033[0m"; }
red()   { echo -e "\033[31m✗ $1\033[0m"; }

# 通用请求函数：检查 HTTP 状态码
check_status() {
    local desc="$1"
    local method="$2"
    local url="$3"
    local expected="$4"
    local data="${5:-}"
    local auth="${6:-}"

    local curl_args=(-s -o /dev/null -w "%{http_code}" -X "$method")
    if [ -n "$auth" ]; then
        curl_args+=(-H "Authorization: Bearer $auth")
    fi
    if [ -n "$data" ]; then
        curl_args+=(-H "Content-Type: application/json" -d "$data")
    fi

    local code
    code=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "000")

    if [ "$code" = "$expected" ]; then
        green "$desc (HTTP $code)"
        ((PASS++))
    else
        red "$desc (期望 $expected, 实际 $code)"
        ((FAIL++))
    fi
}

# 通用请求函数：获取 JSON 响应体
get_body() {
    local method="$1"
    local url="$2"
    local data="${3:-}"
    local auth="${4:-}"

    local curl_args=(-s -X "$method" -H "Content-Type: application/json")
    if [ -n "$auth" ]; then
        curl_args+=(-H "Authorization: Bearer $auth")
    fi
    if [ -n "$data" ]; then
        curl_args+=(-d "$data")
    fi

    curl "${curl_args[@]}" "$url" 2>/dev/null
}

echo "=========================================="
echo "IntraAI 部署验证"
echo "目标: $BASE_URL"
echo "=========================================="
echo ""

# ---- 1. 健康检查 ----
echo "[1/5] 健康检查"
check_status "GET /health" "GET" "$BASE_URL/health" "200"

# ---- 2. 注册 ----
echo ""
echo "[2/5] 用户注册"
REG_BODY=$(get_body "POST" "$BASE_URL/api/auth/register" \
    "{\"username\":\"$USERNAME\",\"email\":\"${USERNAME}@test.com\",\"password\":\"$PASSWORD\"}")

if echo "$REG_BODY" | grep -q "access_token\|id\|username"; then
    green "POST /api/auth/register"
    ((PASS++))
else
    red "POST /api/auth/register: $REG_BODY"
    ((FAIL++))
fi

# ---- 3. 登录 ----
echo ""
echo "[3/5] 用户登录"
LOGIN_BODY=$(get_body "POST" "$BASE_URL/api/auth/login" \
    "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    green "POST /api/auth/login (获取到 token)"
    ((PASS++))
else
    red "POST /api/auth/login: 未获取到 token"
    ((FAIL++))
    echo "登录失败，跳过后续需要认证的测试"
    echo ""
    echo "=========================================="
    echo "结果: $PASS 通过, $FAIL 失败"
    echo "=========================================="
    exit 1
fi

# ---- 4. 知识库 CRUD ----
echo ""
echo "[4/5] 知识库 CRUD"

# 创建知识库
KB_BODY=$(get_body "POST" "$BASE_URL/api/knowledge-bases/" \
    '{"name":"验证测试知识库","description":"部署验证自动创建"}' "$TOKEN")
KB_ID=$(echo "$KB_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$KB_ID" ] && [ "$KB_ID" != "" ]; then
    green "POST /api/knowledge-bases/ (KB ID=$KB_ID)"
    ((PASS++))

    # 查询知识库列表
    check_status "GET /api/knowledge-bases/" "GET" "$BASE_URL/api/knowledge-bases/" "200" "" "$TOKEN"

    # 删除测试知识库
    check_status "DELETE /api/knowledge-bases/$KB_ID" "DELETE" "$BASE_URL/api/knowledge-bases/$KB_ID" "200" "" "$TOKEN"
else
    red "POST /api/knowledge-bases/: $KB_BODY"
    ((FAIL++))
fi

# ---- 5. 会话管理 ----
echo ""
echo "[5/5] 会话管理"

# 创建会话
SESSION_BODY=$(get_body "POST" "$BASE_URL/api/sessions/" '{}' "$TOKEN")
SESSION_ID=$(echo "$SESSION_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "" ]; then
    green "POST /api/sessions/ (Session ID=$SESSION_ID)"
    ((PASS++))

    # 查询会话列表
    check_status "GET /api/sessions/" "GET" "$BASE_URL/api/sessions/" "200" "" "$TOKEN"

    # 删除测试会话
    check_status "DELETE /api/sessions/$SESSION_ID" "DELETE" "$BASE_URL/api/sessions/$SESSION_ID" "200" "" "$TOKEN"
else
    red "POST /api/sessions/: $SESSION_BODY"
    ((FAIL++))
fi

# ---- 结果汇总 ----
echo ""
echo "=========================================="
echo "结果: $PASS 通过, $FAIL 失败"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
