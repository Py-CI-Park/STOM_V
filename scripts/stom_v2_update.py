#!/usr/bin/env python3
"""
STOM Version 2 자동 업데이트 스크립트
====================================
STOM_temp 폴더의 zip 파일을 순서대로 처리하여
STOM_Version_2 브랜치에 자동으로 커밋합니다.

사용법:
  python stom_v2_update.py           # 모든 미반영 버전 처리
  python stom_v2_update.py --dry-run # 실제 커밋 없이 시뮬레이션
  python stom_v2_update.py --from 2.40 # 특정 버전부터 처리
"""

import os
import re
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

# Windows 터미널 UTF-8 출력 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── 설정 ────────────────────────────────────────────────────────────────────
REPO_DIR   = Path("C:/System_Trading/STOM/STOM_V")
TEMP_DIR   = Path("C:/Users/parkc/Downloads/STOM_temp")
BRANCH     = "STOM_Version_2"
EXTRACT_DIR = Path("C:/tmp/stom_extract_temp")

DRY_RUN = "--dry-run" in sys.argv

# ─── 버전 파싱 ────────────────────────────────────────────────────────────────
def parse_version(version_str):
    """'2.37' → (2, 37)"""
    parts = version_str.strip().split(".")
    return tuple(int(p) for p in parts)

def format_version(major, minor):
    return f"{major}.{minor}"

# ─── zip 파일 목록 ────────────────────────────────────────────────────────────
def get_pending_zips(from_version=None):
    """STOM_temp 폴더의 zip 파일을 버전 순서대로 반환"""
    zips = []
    for f in TEMP_DIR.glob("STOM_V*.zip"):
        m = re.match(r"STOM_V(\d+)\.(\d+)\.zip", f.name)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            zips.append((major, minor, f))
    zips.sort()

    if from_version:
        from_tuple = parse_version(from_version)
        zips = [(maj, min_, f) for maj, min_, f in zips if (maj, min_) >= from_tuple]

    return zips

# ─── 현재 버전 확인 ───────────────────────────────────────────────────────────
def get_branch_version():
    """STOM_Version_2 브랜치의 최신 커밋 버전 반환"""
    r = subprocess.run(
        ["git", "log", BRANCH, "--oneline", "-1"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    m = re.search(r"STOM V(\d+)\.(\d+)", r.stdout)
    if m:
        return int(m.group(1)), int(m.group(2))
    return (0, 0)

# ─── _update.txt 섹션 추출 ────────────────────────────────────────────────────
def extract_update_section(update_txt_path, version_str):
    """
    _update.txt에서 해당 버전의 섹션만 추출.
    형식: YYYY-MM-DD V{version}\n1. ...\n2. ...
    """
    # 인코딩 자동 감지 (UTF-8 → CP949 순서로 시도)
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            content = update_txt_path.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        content = update_txt_path.read_bytes().decode("utf-8", errors="replace")

    # 버전 헤더 패턴: 'YYYY-MM-DD V2.37'
    date_ver_pattern = re.compile(r"^\d{4}-\d{2}-\d{2} V", re.MULTILINE)
    target_pattern   = re.compile(
        rf"^\d{{4}}-\d{{2}}-\d{{2}} V{re.escape(version_str)}\b",
        re.MULTILINE
    )

    target_m = target_pattern.search(content)
    if not target_m:
        print(f"  ⚠ _update.txt에서 V{version_str} 섹션을 찾지 못했습니다.")
        return f"STOM V{version_str} 업데이트"

    start = target_m.start()

    # 다음 날짜 헤더 위치 찾기
    next_m = date_ver_pattern.search(content, target_m.end())
    end = next_m.start() if next_m else len(content)

    section = content[start:end].rstrip()
    return section

# ─── zip 적용 및 커밋 ─────────────────────────────────────────────────────────
def apply_zip(zip_path, version_str):
    """zip 파일을 레포에 적용하고 커밋"""
    print(f"\n{'='*50}")
    print(f"  STOM V{version_str} 처리 중: {zip_path.name}")
    print(f"{'='*50}")

    # 임시 디렉터리 초기화
    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)
    EXTRACT_DIR.mkdir(parents=True)

    # zip 압축 해제
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(EXTRACT_DIR)
        zip_file_list = [
            info.filename for info in z.infolist()
            if not info.is_dir()
        ]

    print(f"  압축 해제 완료: {len(zip_file_list)}개 파일")

    # 레포 디렉터리로 파일 복사 (덮어쓰기)
    copied = 0
    for zip_file in zip_file_list:
        src = EXTRACT_DIR / zip_file
        dst = REPO_DIR / zip_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1

    print(f"  파일 복사 완료: {copied}개")

    # _update.txt에서 버전 섹션 추출
    update_txt = EXTRACT_DIR / "_update.txt"
    update_section = extract_update_section(update_txt, version_str)

    if DRY_RUN:
        print(f"\n  [DRY-RUN] 커밋 메시지 미리보기:")
        print(f"  제목: STOM V{version_str}")
        print(f"  본문:\n{update_section}")
        # 임시 디렉터리 정리 후 반환 (레포 디렉터리 오염 방지)
        shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
        return True

    # zip에 포함된 파일만 스테이징 (untracked 파일 오염 방지)
    staged_count = 0
    for zip_file in zip_file_list:
        r = subprocess.run(
            ["git", "add", zip_file],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        if r.returncode == 0:
            staged_count += 1

    print(f"  스테이징 완료: {staged_count}개 파일")

    # 스테이징된 변경사항 있는지 확인
    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_DIR
    )
    if diff_check.returncode == 0:
        print(f"  ℹ 실제 변경 없음 — 커밋 건너뜀")
        return True

    # 변경된 파일 목록 출력
    diff_stat = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=REPO_DIR, capture_output=True, text=True
    )
    print(f"\n  변경 내역:\n{diff_stat.stdout}")

    # 커밋
    commit_msg = f"STOM V{version_str}\n\n{update_section}"
    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=REPO_DIR, capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"  ✓ STOM V{version_str} 커밋 완료")
        print(f"    {result.stdout.strip()}")
        return True
    else:
        print(f"  ✗ 커밋 실패:\n{result.stderr}")
        return False

# ─── 메인 ────────────────────────────────────────────────────────────────────
def main():
    # --from 인수 처리
    from_ver = None
    for arg in sys.argv[1:]:
        if arg.startswith("--from"):
            parts = arg.split("=", 1)
            from_ver = parts[1] if len(parts) > 1 else None
            if not from_ver and sys.argv.index(arg) + 1 < len(sys.argv):
                from_ver = sys.argv[sys.argv.index(arg) + 1]

    print("=" * 60)
    print("STOM Version 2 자동 업데이트 스크립트")
    print("=" * 60)

    if DRY_RUN:
        print("  ⚠ DRY-RUN 모드: 실제 커밋 없이 시뮬레이션")

    # STOM_Version_2 브랜치 체크아웃
    print(f"\n[1] {BRANCH} 브랜치 체크아웃...")
    if not DRY_RUN:
        r = subprocess.run(
            ["git", "checkout", BRANCH],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"  ✗ 브랜치 체크아웃 실패:\n{r.stderr}")
            sys.exit(1)
        print(f"  ✓ {BRANCH} 브랜치 활성화")

    # 현재 버전 확인
    cur_major, cur_minor = get_branch_version()
    print(f"\n[2] 현재 버전: V{cur_major}.{cur_minor}")

    # 대기 중인 zip 파일 목록
    all_zips = get_pending_zips(from_ver)
    if not from_ver:
        pending = [(maj, min_, f) for maj, min_, f in all_zips
                   if (maj, min_) > (cur_major, cur_minor)]
    else:
        pending = all_zips

    print(f"\n[3] 처리 대기 중인 버전: {len(pending)}개")
    for maj, min_, f in pending:
        print(f"  - V{format_version(maj, min_)}: {f.name}")

    if not pending:
        print("\n✓ 모든 버전이 최신 상태입니다.")
        return

    # 순서대로 처리
    print(f"\n[4] 업데이트 처리 시작...")
    success = 0
    for maj, min_, zip_path in pending:
        ver_str = format_version(maj, min_)
        ok = apply_zip(zip_path, ver_str)
        if ok:
            success += 1
        else:
            print(f"\n✗ V{ver_str} 처리 실패. 중단합니다.")
            break

    # 임시 디렉터리 정리
    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)

    print(f"\n{'='*60}")
    print(f"완료: {success}/{len(pending)}개 버전 처리됨")
    if not DRY_RUN and success == len(pending):
        print(f"✓ {BRANCH} 브랜치가 V{format_version(*get_branch_version())}으로 업데이트되었습니다.")
    print("=" * 60)


if __name__ == "__main__":
    main()
