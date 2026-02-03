#!/bin/bash
# ==============================================================================
# STOM CLI Smoke Tests
# ==============================================================================
# 기본 CLI 명령이 정상 작동하는지 빠르게 확인하는 스모크 테스트
#
# 사용법:
#   ./scripts/run_smoke_tests.sh
#   bash scripts/run_smoke_tests.sh
#
# 요구사항:
#   - Python 3.9+
#   - STOM CLI 설치됨
# ==============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 카운터
PASSED=0
FAILED=0
SKIPPED=0

# 테스트 함수
run_test() {
    local description="$1"
    local command="$2"

    echo -n "Testing: $description... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
}

run_test_with_output() {
    local description="$1"
    local command="$2"
    local expected="$3"

    echo -n "Testing: $description... "

    output=$(eval "$command" 2>&1)
    if echo "$output" | grep -q "$expected"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC} (expected '$expected')"
        ((FAILED++))
    fi
}

# 헤더
echo "============================================================"
echo "           STOM CLI Smoke Tests"
echo "============================================================"
echo ""
echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "작업 디렉토리: $(pwd)"
echo ""

# ==============================================================================
# 1. 기본 명령 테스트
# ==============================================================================
echo "--- 1. 기본 명령 테스트 ---"

run_test "--version 명령" "python -m cli.main --version"
run_test "--help 명령" "python -m cli.main --help"

# ==============================================================================
# 2. Strategy 명령 테스트
# ==============================================================================
echo ""
echo "--- 2. Strategy 명령 테스트 ---"

run_test "strategy --help" "python -m cli.main strategy --help"
run_test "strategy stats" "python -m cli.main strategy stats"
run_test "strategy list" "python -m cli.main strategy list"
run_test "strategy list --format json" "python -m cli.main strategy list --format json"
run_test "strategy list --format csv" "python -m cli.main strategy list --format csv"
run_test "strategy list --type stock" "python -m cli.main strategy list --type stock"

# ==============================================================================
# 3. DB 명령 테스트
# ==============================================================================
echo ""
echo "--- 3. DB 명령 테스트 ---"

run_test "db --help" "python -m cli.main db --help"
run_test "db info --type strategy" "python -m cli.main db info --type strategy"
run_test "db info --type setting" "python -m cli.main db info --type setting"

# ==============================================================================
# 4. Backtest 명령 테스트
# ==============================================================================
echo ""
echo "--- 4. Backtest 명령 테스트 ---"

run_test "backtest --help" "python -m cli.main backtest --help"

# ==============================================================================
# 5. Data 명령 테스트
# ==============================================================================
echo ""
echo "--- 5. Data 명령 테스트 ---"

run_test "data --help" "python -m cli.main data --help"

# ==============================================================================
# 6. Trade 명령 테스트
# ==============================================================================
echo ""
echo "--- 6. Trade 명령 테스트 ---"

run_test "trade --help" "python -m cli.main trade --help"

# ==============================================================================
# 7. Monitor 명령 테스트
# ==============================================================================
echo ""
echo "--- 7. Monitor 명령 테스트 ---"

run_test "monitor --help" "python -m cli.main monitor --help"

# ==============================================================================
# 8. Optimize 명령 테스트
# ==============================================================================
echo ""
echo "--- 8. Optimize 명령 테스트 ---"

run_test "optimize --help" "python -m cli.main optimize --help"

# ==============================================================================
# 결과 요약
# ==============================================================================
echo ""
echo "============================================================"
echo "                    테스트 결과"
echo "============================================================"
echo ""
echo -e "통과: ${GREEN}$PASSED${NC}"
echo -e "실패: ${RED}$FAILED${NC}"
echo -e "스킵: ${YELLOW}$SKIPPED${NC}"
echo ""
echo "총 테스트: $((PASSED + FAILED + SKIPPED))"
echo "종료 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}모든 스모크 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}일부 테스트 실패!${NC}"
    exit 1
fi
