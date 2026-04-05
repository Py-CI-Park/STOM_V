"""US-401: 수식관리자 CLI 테스트 — formula list/add/test/delete."""
import json
import os
import sqlite3
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def formula_db(tmp_path):
    """테스트용 formula 테이블이 있는 임시 DB를 생성."""
    db_path = str(tmp_path / 'strategy.db')
    con = sqlite3.connect(db_path)
    con.execute('''CREATE TABLE formula (
        수식명 TEXT,
        체크유무 INTEGER,
        팩터명 TEXT,
        표시형태 TEXT,
        색상 TEXT,
        크기 REAL,
        라인타입 INTEGER,
        수식코드 TEXT
    )''')
    # 샘플 수식 2개 삽입
    con.execute("INSERT INTO formula VALUES ('테스트수식1', 1, '현재가', '선:일반', 'red', 1.0, 1, 'self.line = self.현재가')")
    con.execute("INSERT INTO formula VALUES ('테스트수식2', 0, 'RSI', '화살표:매매', 'blue', 20.0, 6, 'self.check = self.RSI > 70')")
    con.commit()
    con.close()
    return db_path


# ============================================================
# US-401: formula list
# ============================================================

class TestFormulaList:
    """formula list → 수식 목록 출력."""

    def test_list_returns_list(self, formula_db):
        from cli.formula import list_formulas
        result = list_formulas(formula_db)
        assert isinstance(result, list)

    def test_list_contains_formula_names(self, formula_db):
        from cli.formula import list_formulas
        result = list_formulas(formula_db)
        names = [f['name'] for f in result]
        assert '테스트수식1' in names
        assert '테스트수식2' in names

    def test_list_formula_has_required_fields(self, formula_db):
        from cli.formula import list_formulas
        result = list_formulas(formula_db)
        assert len(result) >= 1
        f = result[0]
        assert 'name' in f
        assert 'display_type' in f
        assert 'factor' in f
        assert 'color' in f

    def test_list_empty_db(self, tmp_path):
        """빈 formula 테이블 → 빈 리스트."""
        db_path = str(tmp_path / 'empty.db')
        con = sqlite3.connect(db_path)
        con.execute('''CREATE TABLE formula (
            수식명 TEXT, 체크유무 INTEGER, 팩터명 TEXT, 표시형태 TEXT,
            색상 TEXT, 크기 REAL, 라인타입 INTEGER, 수식코드 TEXT
        )''')
        con.commit()
        con.close()
        from cli.formula import list_formulas
        result = list_formulas(db_path)
        assert result == []


# ============================================================
# US-401: formula add
# ============================================================

class TestFormulaAdd:
    """formula add → DB 삽입 성공."""

    def test_add_formula_inserts_row(self, formula_db):
        from cli.formula import add_formula
        result = add_formula(
            db_path=formula_db,
            name='새수식',
            code='self.line = self.현재가 * 2',
            factor='현재가',
            display_type='선:일반',
            color='green',
            size=2.0,
            line_type=1,
        )
        assert result['status'] == 'ok'

        # DB에서 확인
        con = sqlite3.connect(formula_db)
        cursor = con.cursor()
        cursor.execute("SELECT * FROM formula WHERE 수식명 = '새수식'")
        row = cursor.fetchone()
        con.close()
        assert row is not None
        assert row[0] == '새수식'

    def test_add_formula_replaces_existing(self, formula_db):
        """같은 이름의 수식이 있으면 교체한다."""
        from cli.formula import add_formula
        add_formula(
            db_path=formula_db,
            name='테스트수식1',
            code='self.line = self.현재가 * 100',
            factor='현재가',
            display_type='선:일반',
            color='yellow',
            size=3.0,
            line_type=2,
        )
        con = sqlite3.connect(formula_db)
        cursor = con.cursor()
        cursor.execute("SELECT COUNT(*) FROM formula WHERE 수식명 = '테스트수식1'")
        count = cursor.fetchone()[0]
        con.close()
        assert count == 1

    def test_add_formula_empty_name_fails(self, formula_db):
        """빈 이름 → 에러."""
        from cli.formula import add_formula
        result = add_formula(
            db_path=formula_db,
            name='',
            code='self.line = 1',
            factor='현재가',
            display_type='선:일반',
        )
        assert result['status'] == 'error'

    def test_add_formula_empty_code_fails(self, formula_db):
        """빈 코드 → 에러."""
        from cli.formula import add_formula
        result = add_formula(
            db_path=formula_db,
            name='빈코드수식',
            code='',
            factor='현재가',
            display_type='선:일반',
        )
        assert result['status'] == 'error'


# ============================================================
# US-401: formula test (구문 검증)
# ============================================================

class TestFormulaTest:
    """formula test → 구문 검증 결과."""

    def test_valid_code_passes(self):
        from cli.formula import test_formula
        result = test_formula('self.line = self.현재가')
        assert result['status'] == 'ok'

    def test_syntax_error_fails(self):
        from cli.formula import test_formula
        result = test_formula('if True print("x")')  # syntax error
        assert result['status'] == 'error'
        assert 'error' in result.get('message', '').lower() or 'syntax' in result.get('message', '').lower()

    def test_empty_code_fails(self):
        from cli.formula import test_formula
        result = test_formula('')
        assert result['status'] == 'error'


# ============================================================
# US-401: formula delete
# ============================================================

class TestFormulaDelete:
    """formula delete → DB 삭제 성공."""

    def test_delete_existing_formula(self, formula_db):
        from cli.formula import delete_formula
        result = delete_formula(formula_db, '테스트수식1')
        assert result['status'] == 'ok'

        con = sqlite3.connect(formula_db)
        cursor = con.cursor()
        cursor.execute("SELECT COUNT(*) FROM formula WHERE 수식명 = '테스트수식1'")
        count = cursor.fetchone()[0]
        con.close()
        assert count == 0

    def test_delete_nonexistent_formula(self, formula_db):
        """존재하지 않는 수식 삭제 → 경고 또는 정상 처리."""
        from cli.formula import delete_formula
        result = delete_formula(formula_db, '없는수식')
        # 존재하지 않아도 에러가 아닌 경고 처리
        assert result['status'] in ('ok', 'warning')

    def test_delete_empty_name_fails(self, formula_db):
        """빈 이름으로 삭제 → 에러."""
        from cli.formula import delete_formula
        result = delete_formula(formula_db, '')
        assert result['status'] == 'error'
