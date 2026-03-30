"""
STOM 프로젝트 자동 수정 유틸리티
규칙: 코딩 중 빈줄 삽입 시에는 들여쓰기 되어 있는 빈칸을 모두 제거
"""

import os
from pathlib import Path


def fix_indentation_in_file(filepath):
    """파일 내의 들여쓰기된 빈 줄을 완전히 빈 줄로 수정"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 들여쓰기된 빈 줄을 완전히 빈 줄로 변경
        lines = content.split('\n')
        fixed_lines = []
        changes_made = False
        issue_count = 0

        for line in lines:
            if line.strip() == '' and line != '':
                # 들여쓰기된 빈 줄 발견
                fixed_lines.append('')
                changes_made = True
                issue_count += 1
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        # 변경사항이 있는 경우에만 파일 저장
        if changes_made:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, issue_count
        else:
            return False, 0

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False, 0


def find_python_files(root_dir):
    """프로젝트 내 모든 Python 파일 찾기"""
    python_files = []
    root_path = Path(root_dir)

    # 재귀적으로 모든 .py 파일 찾기
    for file_path in root_path.rglob("*.py"):
        # __pycache__ 디렉토리와 remove_space.py 파일은 제외
        if "__pycache__" not in str(file_path) and file_path.name != "remove_space.py":
            python_files.append(str(file_path))

    return sorted(python_files)


def fix_all_python_files():
    """프로젝트 내 모든 Python 파일의 5번 규칙 수정"""
    print("=" * 60)
    print("STOM 프로젝트 5번 코딩 규칙 자동 수정")
    print("=" * 60)
    print("규칙: 코딩 중 빈줄 삽입 시에는 들여쓰기 되어 있는 빈칸을 모두 제거")
    print()

    # 프로젝트 루트 디렉토리
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 모든 Python 파일 찾기
    python_files = find_python_files(project_root)

    print(f"총 {len(python_files)}개의 Python 파일 발견")
    print()

    # 파일 수정
    fixed_count = 0
    error_count = 0
    total_issues = 0

    for i, filepath in enumerate(python_files, 1):
        try:
            fixed, issue_count = fix_indentation_in_file(filepath)
            if fixed:
                # 상대 경로로 표시
                rel_path = os.path.relpath(filepath, project_root)
                print(f"[수정 완료] {rel_path} ({issue_count}개 수정)")
                fixed_count += 1
                total_issues += issue_count
            else:
                # 진행 상황 표시
                if i % 10 == 0 or i == len(python_files):
                    print(f"진행률: {i}/{len(python_files)}")
        except Exception as e:
            rel_path = os.path.relpath(filepath, project_root)
            print(f"[오류 발생] {rel_path} - {e}")
            error_count += 1

    print()
    print("=" * 60)
    print("수정 결과 요약")
    print("=" * 60)
    print(f"총 파일 수: {len(python_files)}")
    print(f"수정된 파일: {fixed_count}")
    print(f"총 수정된 빈 줄: {total_issues}")
    print(f"오류 발생: {error_count}")
    print(f"이미 정상된 파일: {len(python_files) - fixed_count - error_count}")
    print()

    if fixed_count > 0:
        print(f"[완료] 5번 규칙 수정 완료! 총 {total_issues}개의 빈 줄을 수정했습니다.")
    else:
        print("[정보] 모든 파일이 이미 5번 규칙을 준수하고 있습니다.")


def check_specific_file(filepath):
    """특정 파일의 5번 규칙 준수 여부 확인"""
    if not os.path.exists(filepath):
        print(f"파일을 찾을 수 없습니다: {filepath}")
        return

    print(f"파일 확인: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    issues = []
    for i, line in enumerate(lines, 1):
        if line.strip() == '' and line != '':
            issues.append(f"라인 {i}: 들여쓰기된 빈 줄 발견")

    if issues:
        print(f"[오류] {len(issues)}개의 규칙 위반 발견:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("[정상] 5번 규칙을 준수하고 있습니다.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 특정 파일 확인
        if sys.argv[1] == "check":
            if len(sys.argv) > 2:
                check_specific_file(sys.argv[2])
            else:
                print("사용법: python remove_space.py check <파일경로>")
        else:
            print("알 수 없는 명령어입니다.")
            print("사용법:")
            print("  python remove_space.py                    # 모든 파일 수정")
            print("  python remove_space.py check <파일경로>     # 특정 파일 확인")
    else:
        # 모든 파일 수정
        fix_all_python_files()
