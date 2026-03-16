
import pstats
from io import StringIO


def extract_profile_text(profile_obj, sort_by='cumulative', limit=None):
    """
    프로파일링 결과를 텍스트로 추출

    Args:
        profile_obj: cProfile.Profile 객체
        sort_by: 정렬 기준 ('cumulative', 'time', 'calls')
        limit: 출력할 함수 개수 제한

    Returns:
        str: 프로파일링 결과 텍스트
    """
    s = StringIO()
    ps = pstats.Stats(profile_obj, stream=s).sort_stats(sort_by)

    if limit:
        ps.print_stats(limit)
    else:
        ps.print_stats()

    return s.getvalue()
