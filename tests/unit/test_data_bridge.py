"""Stage 1: 데이터 브릿지 단위 테스트."""
import os
import sqlite3
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from cli.data_bridge import check_tick_db, find_v1_tick_db, ensure_tick_db, restore_empty_db


class TestCheckTickDb:
    """check_tick_db() — DB 상태 진단."""

    def test_missing_db(self, tmp_path):
        result = check_tick_db(str(tmp_path / 'nonexistent.db'))
        assert result['status'] == 'missing'
        assert result['table_count'] == 0

    def test_empty_db(self, tmp_path):
        db = str(tmp_path / 'empty.db')
        con = sqlite3.connect(db)
        con.close()
        result = check_tick_db(db)
        assert result['status'] == 'empty'

    def test_valid_db(self, tmp_path):
        db = str(tmp_path / 'tick.db')
        con = sqlite3.connect(db)
        for i in range(10):
            con.execute(f'CREATE TABLE t{i} (x INTEGER)')
        con.commit()
        con.close()
        # 파일이 1MB 미만이므로 empty 판정
        result = check_tick_db(db)
        assert result['table_count'] == 10

    def test_returns_required_fields(self, tmp_path):
        db = str(tmp_path / 'test.db')
        sqlite3.connect(db).close()
        result = check_tick_db(db)
        assert 'status' in result
        assert 'path' in result
        assert 'size_bytes' in result
        assert 'table_count' in result
        assert 'is_symlink' in result


class TestEnsureTickDb:
    """ensure_tick_db() — 자동 연결."""

    def test_already_ok_db(self, tmp_path):
        """충분히 큰 DB → 그대로 사용."""
        db = str(tmp_path / 'big.db')
        con = sqlite3.connect(db)
        con.execute('CREATE TABLE test (data BLOB)')
        con.execute('INSERT INTO test VALUES (?)', (b'x' * 2_000_000,))
        con.commit()
        con.close()
        result = ensure_tick_db(db)
        assert result['status'] == 'ok'

    def test_empty_db_no_v1(self, tmp_path, monkeypatch):
        """빈 DB + V1 없음 → 에러."""
        db = str(tmp_path / 'empty.db')
        sqlite3.connect(db).close()
        monkeypatch.setattr('cli.data_bridge._V1_DB_CANDIDATES', [str(tmp_path / 'fake.db')])
        result = ensure_tick_db(db)
        assert result['status'] == 'error'

    def test_returns_status_dict(self, tmp_path):
        db = str(tmp_path / 'test.db')
        sqlite3.connect(db).close()
        result = ensure_tick_db(db)
        assert 'status' in result
        assert 'message' in result
        assert 'path' in result


class TestRestoreEmptyDb:
    """restore_empty_db() — 심볼릭 링크 제거 + 원복."""

    def test_non_symlink_returns_error(self, tmp_path):
        db = str(tmp_path / 'regular.db')
        sqlite3.connect(db).close()
        result = restore_empty_db(db)
        assert result['status'] == 'error'

    def test_symlink_restore(self, tmp_path):
        """심볼릭 링크 + 백업 → 원복 성공."""
        target = str(tmp_path / 'target.db')
        link = str(tmp_path / 'link.db')
        backup = link + '.empty_backup'
        # 타겟 생성
        sqlite3.connect(target).close()
        # 백업 생성
        with open(backup, 'w') as f:
            f.write('empty')
        # 심볼릭 링크 생성
        try:
            os.symlink(target, link)
        except OSError:
            pytest.skip('symlink not available')
        result = restore_empty_db(link)
        assert result['status'] == 'ok'
        assert os.path.exists(link)
        assert not os.path.islink(link)


class TestFindV1TickDb:
    """find_v1_tick_db() — V1 경로 탐색."""

    def test_returns_none_if_no_candidates(self, monkeypatch):
        monkeypatch.setattr('cli.data_bridge._V1_DB_CANDIDATES', ['/nonexistent/path.db'])
        assert find_v1_tick_db() is None

    def test_returns_path_if_exists(self, tmp_path, monkeypatch):
        db = str(tmp_path / 'v1_tick.db')
        con = sqlite3.connect(db)
        con.execute('CREATE TABLE t (x BLOB)')
        con.execute('INSERT INTO t VALUES (?)', (b'x' * 2_000_000,))
        con.commit()
        con.close()
        monkeypatch.setattr('cli.data_bridge._V1_DB_CANDIDATES', [db])
        result = find_v1_tick_db()
        assert result is not None
