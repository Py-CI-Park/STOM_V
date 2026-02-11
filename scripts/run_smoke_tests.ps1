# ==============================================================================
# STOM CLI Smoke Tests (PowerShell)
# ==============================================================================
# 기본 CLI 명령이 정상 작동하는지 빠르게 확인하는 스모크 테스트
#
# 사용법:
#   .\scripts\run_smoke_tests.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run_smoke_tests.ps1
#
# 요구사항:
#   - Python 3.9+
#   - STOM CLI 설치됨
# ==============================================================================

$ErrorActionPreference = "Continue"

# 카운터
$script:Passed = 0
$script:Failed = 0
$script:Skipped = 0

# 테스트 함수
function Test-Command {
    param(
        [string]$Description,
        [string]$Command
    )

    Write-Host -NoNewline "Testing: $Description... "

    try {
        $null = Invoke-Expression $Command 2>&1
        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-Host "PASS" -ForegroundColor Green
            $script:Passed++
        } else {
            Write-Host "FAIL (exit code: $LASTEXITCODE)" -ForegroundColor Red
            $script:Failed++
        }
    }
    catch {
        Write-Host "FAIL (exception)" -ForegroundColor Red
        $script:Failed++
    }
}

# 헤더
Write-Host "============================================================"
Write-Host "           STOM CLI Smoke Tests"
Write-Host "============================================================"
Write-Host ""
Write-Host "시작 시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

# 프로젝트 루트로 이동
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\.."

Write-Host "작업 디렉토리: $(Get-Location)"
Write-Host ""

# ==============================================================================
# 1. 기본 명령 테스트
# ==============================================================================
Write-Host "--- 1. 기본 명령 테스트 ---"

Test-Command "--version 명령" "python -m cli.main --version"
Test-Command "--help 명령" "python -m cli.main --help"

# ==============================================================================
# 2. Strategy 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 2. Strategy 명령 테스트 ---"

Test-Command "strategy --help" "python -m cli.main strategy --help"
Test-Command "strategy stats" "python -m cli.main strategy stats"
Test-Command "strategy list" "python -m cli.main strategy list"
Test-Command "strategy list --format json" "python -m cli.main strategy list --format json"
Test-Command "strategy list --format csv" "python -m cli.main strategy list --format csv"
Test-Command "strategy list --type stock" "python -m cli.main strategy list --type stock"

# ==============================================================================
# 3. DB 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 3. DB 명령 테스트 ---"

Test-Command "db --help" "python -m cli.main db --help"
Test-Command "db info --type strategy" "python -m cli.main db info --type strategy"
Test-Command "db info --type setting" "python -m cli.main db info --type setting"

# ==============================================================================
# 4. Backtest 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 4. Backtest 명령 테스트 ---"

Test-Command "backtest --help" "python -m cli.main backtest --help"

# ==============================================================================
# 5. Data 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 5. Data 명령 테스트 ---"

Test-Command "data --help" "python -m cli.main data --help"

# ==============================================================================
# 6. Trade 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 6. Trade 명령 테스트 ---"

Test-Command "trade --help" "python -m cli.main trade --help"

# ==============================================================================
# 7. Monitor 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 7. Monitor 명령 테스트 ---"

Test-Command "monitor --help" "python -m cli.main monitor --help"

# ==============================================================================
# 8. Optimize 명령 테스트
# ==============================================================================
Write-Host ""
Write-Host "--- 8. Optimize 명령 테스트 ---"

Test-Command "optimize --help" "python -m cli.main optimize --help"

# ==============================================================================
# 결과 요약
# ==============================================================================
Write-Host ""
Write-Host "============================================================"
Write-Host "                    테스트 결과"
Write-Host "============================================================"
Write-Host ""
Write-Host "통과: " -NoNewline
Write-Host "$script:Passed" -ForegroundColor Green
Write-Host "실패: " -NoNewline
Write-Host "$script:Failed" -ForegroundColor Red
Write-Host "스킵: " -NoNewline
Write-Host "$script:Skipped" -ForegroundColor Yellow
Write-Host ""
$Total = $script:Passed + $script:Failed + $script:Skipped
Write-Host "총 테스트: $Total"
Write-Host "종료 시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

if ($script:Failed -eq 0) {
    Write-Host "모든 스모크 테스트 통과!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "일부 테스트 실패!" -ForegroundColor Red
    exit 1
}
