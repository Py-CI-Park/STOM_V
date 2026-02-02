"""
Output Adapter for CLI
======================

결과 출력 포맷터 (JSON/CSV/Table).
"""

import json
import csv
from enum import Enum
from typing import Any, List, Dict, Optional, Union
from io import StringIO
from pathlib import Path
import pandas as pd
from utility.static import get_logger

logger_ = get_logger('OutputAdapter')


class OutputFormat(Enum):
    """출력 포맷"""
    JSON = "json"
    CSV = "csv"
    TABLE = "table"
    TEXT = "text"
    MARKDOWN = "markdown"


class OutputAdapter:
    """
    CLI 결과 출력 어댑터.
    다양한 포맷으로 결과를 출력할 수 있음.
    """

    def __init__(self, format: OutputFormat = OutputFormat.TABLE,
                 output_file: Optional[str] = None):
        """
        Args:
            format: 출력 포맷 (default: TABLE)
            output_file: 출력 파일 경로 (None이면 stdout)
        """
        self.format = format
        self.output_file = output_file
        self.logger = logger_

    def output(self, data: Union[Dict, List, pd.DataFrame, str],
               title: Optional[str] = None) -> str:
        """
        데이터를 지정된 포맷으로 출력

        Args:
            data: 출력할 데이터
            title: 제목 (선택사항)

        Returns:
            포맷된 출력 문자열
        """
        try:
            if isinstance(data, pd.DataFrame):
                result = self._format_dataframe(data, title)
            elif isinstance(data, dict):
                result = self._format_dict(data, title)
            elif isinstance(data, list):
                result = self._format_list(data, title)
            elif isinstance(data, str):
                result = data
            else:
                result = str(data)

            # 파일에 쓸지 stdout에 쓸지 결정
            if self.output_file:
                self._write_to_file(result)
            else:
                print(result)

            return result

        except Exception as e:
            self.logger.error(f"Error formatting output: {e}")
            raise

    def _format_dataframe(self, df: pd.DataFrame, title: Optional[str] = None) -> str:
        """DataFrame을 포맷된 문자열로 변환"""
        output = StringIO()

        if title:
            output.write(f"\n{'='*80}\n")
            output.write(f"{title}\n")
            output.write(f"{'='*80}\n\n")

        if self.format == OutputFormat.JSON:
            result = df.to_json(orient='records', indent=2, force_ascii=False)
        elif self.format == OutputFormat.CSV:
            result = df.to_csv(index=False)
        elif self.format == OutputFormat.MARKDOWN:
            result = df.to_markdown(index=False)
        else:  # TABLE or TEXT
            result = self._table_format(df)

        output.write(result)
        return output.getvalue()

    def _format_dict(self, data: Dict, title: Optional[str] = None) -> str:
        """딕셔너리를 포맷된 문자열로 변환"""
        output = StringIO()

        if title:
            output.write(f"\n{'='*80}\n")
            output.write(f"{title}\n")
            output.write(f"{'='*80}\n\n")

        if self.format == OutputFormat.JSON:
            result = json.dumps(data, indent=2, ensure_ascii=False)
        elif self.format == OutputFormat.MARKDOWN:
            result = self._dict_to_markdown(data)
        elif self.format == OutputFormat.CSV:
            # 단순 CSV: key, value
            result = self._dict_to_csv(data)
        else:  # TABLE or TEXT
            result = self._dict_to_table(data)

        output.write(result)
        return output.getvalue()

    def _format_list(self, data: List, title: Optional[str] = None) -> str:
        """리스트를 포맷된 문자열로 변환"""
        output = StringIO()

        if title:
            output.write(f"\n{'='*80}\n")
            output.write(f"{title}\n")
            output.write(f"{'='*80}\n\n")

        if self.format == OutputFormat.JSON:
            result = json.dumps(data, indent=2, ensure_ascii=False)
        elif self.format == OutputFormat.MARKDOWN:
            result = self._list_to_markdown(data)
        elif self.format == OutputFormat.CSV and len(data) > 0 and isinstance(data[0], dict):
            # 딕셔너리 리스트인 경우 CSV로 변환
            result = self._list_dict_to_csv(data)
        else:  # TABLE or TEXT
            result = self._list_to_table(data)

        output.write(result)
        return output.getvalue()

    def _table_format(self, df: pd.DataFrame) -> str:
        """DataFrame을 테이블 형식으로 포맷"""
        # pandas의 기본 포맷 사용
        return df.to_string()

    def _dict_to_table(self, data: Dict) -> str:
        """딕셔너리를 테이블 형식으로 변환"""
        output = StringIO()
        max_key_len = max(len(str(k)) for k in data.keys()) if data else 0

        for key, value in data.items():
            output.write(f"{str(key):<{max_key_len}} : {value}\n")

        return output.getvalue()

    def _dict_to_csv(self, data: Dict) -> str:
        """딕셔너리를 CSV 형식으로 변환"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Key', 'Value'])

        for key, value in data.items():
            writer.writerow([str(key), str(value)])

        return output.getvalue()

    def _dict_to_markdown(self, data: Dict) -> str:
        """딕셔너리를 Markdown 형식으로 변환"""
        output = StringIO()
        output.write("| Key | Value |\n")
        output.write("|-----|-------|\n")

        for key, value in data.items():
            output.write(f"| {key} | {value} |\n")

        return output.getvalue()

    def _list_to_table(self, data: List) -> str:
        """리스트를 테이블 형식으로 변환"""
        output = StringIO()

        if len(data) == 0:
            return "[Empty list]\n"

        if isinstance(data[0], dict):
            # 딕셔너리 리스트
            df = pd.DataFrame(data)
            return self._table_format(df)
        else:
            # 단순 리스트
            for idx, item in enumerate(data, 1):
                output.write(f"{idx}. {item}\n")

        return output.getvalue()

    def _list_dict_to_csv(self, data: List[Dict]) -> str:
        """딕셔너리 리스트를 CSV로 변환"""
        output = StringIO()

        if len(data) == 0:
            return ""

        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()

    def _list_to_markdown(self, data: List) -> str:
        """리스트를 Markdown 형식으로 변환"""
        output = StringIO()

        if isinstance(data[0], dict) if data else False:
            # 딕셔너리 리스트
            df = pd.DataFrame(data)
            output.write(df.to_markdown(index=False))
        else:
            # 단순 리스트
            for item in data:
                output.write(f"- {item}\n")

        return output.getvalue()

    def _write_to_file(self, content: str) -> None:
        """파일에 내용 작성"""
        try:
            path = Path(self.output_file)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Output written to {self.output_file}")
        except Exception as e:
            self.logger.error(f"Error writing to file {self.output_file}: {e}")
            raise

    def set_format(self, format: OutputFormat) -> None:
        """출력 포맷 변경"""
        self.format = format
        self.logger.debug(f"Output format changed to {format.value}")

    def set_output_file(self, output_file: Optional[str]) -> None:
        """출력 파일 변경"""
        self.output_file = output_file
        if output_file:
            self.logger.debug(f"Output file set to {output_file}")
        else:
            self.logger.debug("Output to stdout")

    @staticmethod
    def format_error(error: Exception, title: str = "Error") -> str:
        """에러를 포맷된 문자열로 변환"""
        output = StringIO()
        output.write(f"\n{'='*80}\n")
        output.write(f"{title}\n")
        output.write(f"{'='*80}\n\n")
        output.write(f"Error Type: {type(error).__name__}\n")
        output.write(f"Message: {str(error)}\n")
        return output.getvalue()

    @staticmethod
    def format_success(message: str, title: str = "Success") -> str:
        """성공 메시지를 포맷된 문자열로 변환"""
        output = StringIO()
        output.write(f"\n{'='*80}\n")
        output.write(f"{title}\n")
        output.write(f"{'='*80}\n\n")
        output.write(f"{message}\n")
        return output.getvalue()

    @staticmethod
    def format_info(info: str, title: str = "Information") -> str:
        """정보 메시지를 포맷된 문자열로 변환"""
        output = StringIO()
        output.write(f"\n{'='*80}\n")
        output.write(f"{title}\n")
        output.write(f"{'='*80}\n\n")
        output.write(f"{info}\n")
        return output.getvalue()
