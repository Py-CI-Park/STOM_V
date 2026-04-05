"""UTF-8 안전 stdout/stderr 래퍼.

Windows CP949 환경에서 UnicodeEncodeError를 방지한다.
인코딩 불가 문자는 '?' 로 대체된다 (errors='replace').
"""
import sys


def configure_safe_output():
    """stdout/stderr를 errors='replace' 모드로 재설정.

    Python 3.7+ 의 reconfigure()를 사용한다.
    reconfigure 미지원 환경에서는 조용히 무시한다.
    """
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors='replace')
        except Exception:
            pass
