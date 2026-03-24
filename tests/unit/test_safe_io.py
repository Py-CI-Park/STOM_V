"""US-001: UTF-8 안전 출력 레이어 테스트."""
import io
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli._safe_io import configure_safe_output


class TestConfigureSafeOutput:
    def test_does_not_raise(self):
        """configure_safe_output()이 예외 없이 실행된다."""
        configure_safe_output()

    def test_replace_mode_prevents_encode_error(self):
        """errors='replace' 적용 후 em-dash 출력 시 crash 없음."""
        buf = io.TextIOWrapper(io.BytesIO(), encoding='cp949', errors='strict')
        # strict 모드에서는 em-dash가 실패해야 함
        with pytest.raises(UnicodeEncodeError):
            buf.write('\u2014')
            buf.flush()

        # replace 모드에서는 성공
        buf2 = io.TextIOWrapper(io.BytesIO(), encoding='cp949', errors='replace')
        buf2.write('\u2014')
        buf2.flush()
        buf2.seek(0)
        content = buf2.buffer.getvalue()
        assert len(content) > 0  # 대체 문자가 기록됨

    def test_korean_output_preserved(self):
        """한글은 CP949에서 정상 인코딩된다."""
        buf = io.TextIOWrapper(io.BytesIO(), encoding='cp949', errors='replace')
        test_str = '승격될 때까지 파라미터 자동 변이'
        buf.write(test_str)
        buf.flush()
        buf.seek(0)
        content = buf.buffer.getvalue()
        decoded = content.decode('cp949')
        assert decoded == test_str

    def test_reconfigure_missing_graceful(self):
        """reconfigure 메서드가 없는 스트림에서도 에러 없이 동작."""
        original = sys.stdout
        try:
            sys.stdout = object()  # reconfigure 없는 객체
            configure_safe_output()  # 에러 없이 통과해야 함
        finally:
            sys.stdout = original

    def test_none_stream_graceful(self):
        """stdout이 None인 환경에서도 에러 없이 동작."""
        original = sys.stdout
        try:
            sys.stdout = None
            configure_safe_output()
        finally:
            sys.stdout = original
