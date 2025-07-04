#!/bin/bash

# セッション作成プロキシのテストスクリプト
# Azure OpenAI Realtime API プロキシサーバーをテストします

set -e

# 設定
BASE_URL="http://localhost:8000"
TEST_DATA='{"model": "gpt-4o-realtime-preview", "voice": "alloy"}'

# 色付きログ関数
log_info() {
    echo -e "\033[36m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

log_test() {
    echo -e "\033[33m[TEST]\033[0m $1"
}

# ヘルスチェックテスト
test_health_check() {
    log_test "🩺 Testing Health Check..."
    
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response.json "${BASE_URL}/health" || echo "000")
    http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        log_success "✅ Health check successful!"
        log_info "📊 Response: $(cat /tmp/health_response.json)"
    else
        log_error "❌ Health check failed with status $http_code"
        [ -f /tmp/health_response.json ] && log_error "Response: $(cat /tmp/health_response.json)"
        return 1
    fi
}

# セッション作成テスト
test_session_creation() {
    log_test "🧪 Testing Sessions Proxy API..."
    log_info "📡 Base URL: $BASE_URL"
    log_info "📤 Request data: $TEST_DATA"
    
    response=$(curl -s -w "%{http_code}" -o /tmp/session_response.json \
        -X POST \
        -H "Content-Type: application/json" \
        -H "api-key: dummy_key" \
        -d "$TEST_DATA" \
        "${BASE_URL}/sessions/" || echo "000")
    
    http_code="${response: -3}"
    
    log_info "📥 Response Status: $http_code"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log_success "✅ Session creation successful!"
        
        # JSONレスポンスから値を抽出
        if command -v jq >/dev/null 2>&1; then
            session_id=$(jq -r '.id' /tmp/session_response.json 2>/dev/null || echo "N/A")
            model=$(jq -r '.model' /tmp/session_response.json 2>/dev/null || echo "N/A")
            expires_at=$(jq -r '.expires_at' /tmp/session_response.json 2>/dev/null || echo "N/A")
            
            log_success "🆔 Session ID: $session_id"
            log_success "🤖 Model: $model"
            log_success "⏰ Expires At: $expires_at"
        else
            log_info "📄 Full Response: $(cat /tmp/session_response.json)"
            log_info "💡 Install 'jq' for better JSON parsing"
        fi
    else
        log_error "❌ Session creation failed with status $http_code"
        [ -f /tmp/session_response.json ] && log_error "💬 Error: $(cat /tmp/session_response.json)"
        return 1
    fi
}

# API スキーマテスト
test_api_schema() {
    log_test "📋 Testing API Schema..."
    
    response=$(curl -s -w "%{http_code}" -o /tmp/openapi_response.json "${BASE_URL}/openapi.json" || echo "000")
    http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        log_success "✅ OpenAPI schema accessible"
        
        if command -v jq >/dev/null 2>&1; then
            title=$(jq -r '.info.title' /tmp/openapi_response.json 2>/dev/null || echo "N/A")
            version=$(jq -r '.info.version' /tmp/openapi_response.json 2>/dev/null || echo "N/A")
            log_info "📖 API Title: $title"
            log_info "🔢 API Version: $version"
        fi
    else
        log_error "❌ OpenAPI schema not accessible (status: $http_code)"
    fi
}

# レート制限テスト
test_rate_limiting() {
    log_test "⚡ Testing Rate Limiting (5 rapid requests)..."
    
    success_count=0
    error_count=0
    
    for i in {1..5}; do
        response=$(curl -s -w "%{http_code}" -o /tmp/rate_test_${i}.json \
            -X POST \
            -H "Content-Type: application/json" \
            -H "api-key: dummy_key" \
            -d "$TEST_DATA" \
            "${BASE_URL}/sessions/" 2>/dev/null || echo "000")
        
        http_code="${response: -3}"
        
        if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
            ((success_count++))
            echo -n "✅"
        else
            ((error_count++))
            echo -n "❌($http_code)"
        fi
        
        # 短い間隔で送信
        sleep 0.1
    done
    
    echo ""
    log_info "📊 Rate limiting test results: $success_count success, $error_count errors"
}

# メイン実行
main() {
    echo "🚀 Starting Azure OpenAI Proxy Server Tests"
    echo "============================================="
    
    # サーバーが起動しているかチェック
    if ! curl -s "$BASE_URL/health" >/dev/null 2>&1; then
        log_error "❌ Server is not running at $BASE_URL"
        log_info "💡 Please start the server first: docker-compose up"
        exit 1
    fi
    
    echo ""
    
    # テスト実行
    test_health_check && echo ""
    test_session_creation && echo ""
    test_api_schema && echo ""
    test_rate_limiting && echo ""
    
    echo "============================================="
    echo "🏁 Test completed!"
    
    # 一時ファイルのクリーンアップ
    rm -f /tmp/health_response.json /tmp/session_response.json /tmp/openapi_response.json /tmp/rate_test_*.json
}

# スクリプト実行
main "$@"
