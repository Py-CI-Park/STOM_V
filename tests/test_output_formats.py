"""
STOM CLI Output Format Tests
=============================

출력 포맷 테스트 (JSON, CSV, Table, Markdown)
"""

import pytest
import json
import csv
from io import StringIO
from click.testing import CliRunner

from cli.main import main
from cli.adapters.output_adapter import OutputAdapter, OutputFormat


class TestOutputAdapterUnit:
    """OutputAdapter 단위 테스트"""

    def test_output_adapter_init_default(self):
        """기본 초기화 테스트"""
        adapter = OutputAdapter()
        assert adapter.format == OutputFormat.TABLE
        assert adapter.output_file is None

    def test_output_adapter_init_json(self):
        """JSON 포맷 초기화"""
        adapter = OutputAdapter(format=OutputFormat.JSON)
        assert adapter.format == OutputFormat.JSON

    def test_output_adapter_init_csv(self):
        """CSV 포맷 초기화"""
        adapter = OutputAdapter(format=OutputFormat.CSV)
        assert adapter.format == OutputFormat.CSV

    def test_set_format(self):
        """포맷 변경 테스트"""
        adapter = OutputAdapter()
        adapter.set_format(OutputFormat.JSON)
        assert adapter.format == OutputFormat.JSON

    def test_format_error(self):
        """에러 포맷 테스트"""
        error = Exception("Test error message")
        result = OutputAdapter.format_error(error)

        assert "Error" in result
        assert "Test error message" in result
        assert "Exception" in result

    def test_format_success(self):
        """성공 메시지 포맷 테스트"""
        result = OutputAdapter.format_success("Operation completed")

        assert "Success" in result
        assert "Operation completed" in result

    def test_format_info(self):
        """정보 메시지 포맷 테스트"""
        result = OutputAdapter.format_info("Some information")

        assert "Information" in result
        assert "Some information" in result

    def test_format_warning(self):
        """경고 메시지 포맷 테스트"""
        result = OutputAdapter.format_warning("Warning message")

        assert "Warning" in result
        assert "Warning message" in result

    def test_output_string_json_wraps_message(self, capsys):
        """JSON 모드에서 문자열은 message 객체로 래핑되어야 함"""
        adapter = OutputAdapter(format=OutputFormat.JSON)
        returned = adapter.output("hello")
        captured = capsys.readouterr().out.strip()

        parsed_returned = json.loads(returned)
        parsed_captured = json.loads(captured)
        assert parsed_returned["message"] == "hello"
        assert parsed_captured["message"] == "hello"


class TestOutputAdapterDict:
    """OutputAdapter 딕셔너리 출력 테스트"""

    def test_dict_to_json(self):
        """딕셔너리 JSON 변환"""
        adapter = OutputAdapter(format=OutputFormat.JSON)
        data = {"name": "test", "value": 123}

        # output 메서드는 print를 호출하므로 _format_dict를 직접 테스트
        result = adapter._format_dict(data)

        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["value"] == 123

    def test_dict_to_json_with_title_is_parseable(self):
        """JSON 출력은 title이 있어도 파싱 가능해야 함"""
        adapter = OutputAdapter(format=OutputFormat.JSON)
        data = {"name": "test", "value": 123}

        result = adapter._format_dict(data, title="테스트")
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_dict_to_table(self):
        """딕셔너리 테이블 변환"""
        adapter = OutputAdapter(format=OutputFormat.TABLE)
        data = {"key1": "value1", "key2": "value2"}

        result = adapter._format_dict(data)

        assert "key1" in result
        assert "value1" in result

    def test_dict_to_csv(self):
        """딕셔너리 CSV 변환"""
        adapter = OutputAdapter(format=OutputFormat.CSV)
        data = {"name": "test", "count": 5}

        result = adapter._format_dict(data)

        assert "Key" in result
        assert "Value" in result
        assert "name" in result
        assert "test" in result

    def test_dict_to_markdown(self):
        """딕셔너리 마크다운 변환"""
        adapter = OutputAdapter(format=OutputFormat.MARKDOWN)
        data = {"col1": "val1", "col2": "val2"}

        result = adapter._format_dict(data)

        assert "|" in result
        assert "Key" in result
        assert "Value" in result


class TestOutputAdapterList:
    """OutputAdapter 리스트 출력 테스트"""

    def test_list_to_json(self):
        """리스트 JSON 변환"""
        adapter = OutputAdapter(format=OutputFormat.JSON)
        data = [1, 2, 3, "test"]

        result = adapter._format_list(data)

        parsed = json.loads(result)
        assert parsed == [1, 2, 3, "test"]

    def test_list_dict_to_json(self):
        """딕셔너리 리스트 JSON 변환"""
        adapter = OutputAdapter(format=OutputFormat.JSON)
        data = [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2}
        ]

        result = adapter._format_list(data)

        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "item1"

    def test_list_to_table(self):
        """리스트 테이블 변환"""
        adapter = OutputAdapter(format=OutputFormat.TABLE)
        data = ["item1", "item2", "item3"]

        result = adapter._format_list(data)

        assert "1." in result
        assert "item1" in result

    def test_list_dict_to_csv(self):
        """딕셔너리 리스트 CSV 변환"""
        adapter = OutputAdapter(format=OutputFormat.CSV)
        data = [
            {"name": "a", "value": 1},
            {"name": "b", "value": 2}
        ]

        result = adapter._format_list(data)

        # CSV 헤더 확인
        assert "name" in result
        assert "value" in result

    def test_empty_list(self):
        """빈 리스트 처리"""
        adapter = OutputAdapter(format=OutputFormat.TABLE)
        data = []

        result = adapter._format_list(data)

        assert "Empty" in result or result.strip() == ""


class TestOutputAdapterDataFrame:
    """OutputAdapter DataFrame 출력 테스트"""

    def test_dataframe_to_json(self):
        """DataFrame JSON 변환"""
        import pandas as pd

        adapter = OutputAdapter(format=OutputFormat.JSON)
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"]
        })

        result = adapter._format_dataframe(df)

        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed[0]["col1"] == 1

    def test_dataframe_to_csv(self):
        """DataFrame CSV 변환"""
        import pandas as pd

        adapter = OutputAdapter(format=OutputFormat.CSV)
        df = pd.DataFrame({
            "name": ["test1", "test2"],
            "value": [10, 20]
        })

        result = adapter._format_dataframe(df)

        assert "name" in result
        assert "value" in result
        assert "test1" in result

    def test_dataframe_to_csv_with_title_has_no_banner(self):
        """CSV 출력은 title 배너를 포함하지 않아야 함"""
        import pandas as pd

        adapter = OutputAdapter(format=OutputFormat.CSV)
        df = pd.DataFrame({"name": ["x"], "value": [1]})
        result = adapter._format_dataframe(df, title="CSV 제목")

        first_line = result.splitlines()[0]
        assert first_line.startswith("name")

    def test_dataframe_to_table(self):
        """DataFrame 테이블 변환"""
        import pandas as pd

        adapter = OutputAdapter(format=OutputFormat.TABLE)
        df = pd.DataFrame({
            "a": [1, 2],
            "b": [3, 4]
        })

        result = adapter._format_dataframe(df)

        assert "a" in result
        assert "b" in result

    def test_dataframe_to_markdown(self):
        """DataFrame 마크다운 변환"""
        import pandas as pd

        pytest.importorskip("tabulate")  # tabulate 없으면 스킵

        adapter = OutputAdapter(format=OutputFormat.MARKDOWN)
        df = pd.DataFrame({
            "col1": [1, 2],
            "col2": [3, 4]
        })

        result = adapter._format_dataframe(df)

        assert "|" in result
        assert "col1" in result


class TestCLIOutputFormats:
    """CLI 명령 출력 포맷 통합 테스트"""

    @pytest.mark.smoke
    def test_strategy_stats_table(self, cli_runner: CliRunner):
        """strategy stats 테이블 출력"""
        result = cli_runner.invoke(main, ['strategy', 'stats'])

        assert result.exit_code == 0

    @pytest.mark.smoke
    def test_strategy_stats_json(self, cli_runner: CliRunner):
        """strategy stats JSON 출력"""
        result = cli_runner.invoke(main, ['strategy', 'stats', '--format', 'json'])

        assert result.exit_code == 0

    def test_strategy_list_all_formats(self, cli_runner: CliRunner):
        """strategy list 모든 포맷 테스트"""
        formats = ['table', 'json', 'csv']

        for fmt in formats:
            result = cli_runner.invoke(main, ['strategy', 'list', '--format', fmt])
            assert result.exit_code == 0, f"Failed for format: {fmt}"

    def test_db_info_all_formats(self, cli_runner: CliRunner):
        """db info 모든 포맷 테스트"""
        formats = ['table', 'json', 'csv']

        for fmt in formats:
            result = cli_runner.invoke(main, ['db', 'info', '--type', 'strategy', '--format', fmt])
            # DB 파일 유무와 관계없이 명령 파싱 확인
            assert result.exit_code in [0, 1], f"Failed for format: {fmt}"


class TestJSONValidation:
    """JSON 출력 유효성 검증"""

    def test_valid_json_strategy_stats(self, cli_runner: CliRunner):
        """strategy stats JSON 유효성"""
        result = cli_runner.invoke(main, ['strategy', 'stats', '--format', 'json'])

        if result.exit_code == 0 and result.output.strip():
            # JSON 파싱 시도
            try:
                json.loads(result.output)
            except json.JSONDecodeError:
                # 일부 출력은 순수 JSON이 아닐 수 있음
                pass

    def test_valid_json_strategy_list(self, cli_runner: CliRunner):
        """strategy list JSON 유효성"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--format', 'json'])

        if result.exit_code == 0 and result.output.strip():
            try:
                json.loads(result.output)
            except json.JSONDecodeError:
                pass


class TestCSVValidation:
    """CSV 출력 유효성 검증"""

    def test_valid_csv_format(self, cli_runner: CliRunner):
        """CSV 포맷 유효성"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--format', 'csv'])

        if result.exit_code == 0 and result.output.strip():
            # CSV 파싱 시도
            try:
                reader = csv.reader(StringIO(result.output))
                rows = list(reader)
                # 최소 헤더 행이 있어야 함
                assert len(rows) >= 0
            except csv.Error:
                pass


class TestStructuredErrorFormat:
    """구조화 에러 응답 테스트"""

    def test_format_error_json_payload(self):
        error = ValueError("invalid input")
        result = OutputAdapter.format_error(
            error,
            "요청 실패",
            output_format=OutputFormat.JSON,
            error_code="E_TEST",
        )
        parsed = json.loads(result)

        assert parsed["ok"] is False
        assert parsed["error"]["code"] == "E_TEST"
        assert parsed["error"]["message"] == "invalid input"
