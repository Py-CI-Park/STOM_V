
def error_decorator(func):
    """에러 처리 데코레이터입니다.
    Returns:
        래퍼 함수
    """
    from traceback import format_exc
    from utility.settings.setting_base import UI_NUM

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            if args:
                if hasattr(args[0], 'windowQ'):
                    args[0].windowQ.put((UI_NUM['시스템로그'], format_exc()))
                elif hasattr(args[0], 'ui'):
                    args[0].ui.windowQ.put((UI_NUM['시스템로그'], format_exc()))
                elif hasattr(args[0], 'wq'):
                    args[0].wq.put((UI_NUM['시스템로그'], format_exc()))
            return None
    return wrapper


def thread_decorator(func):
    """스레드 데코레이터입니다.
    Args:
        func: 데코레이터를 적용할 함수
    Returns:
        래퍼 함수
    """
    from threading import Thread

    def wrapper(*args):
        Thread(target=func, args=args, daemon=True).start()
    return wrapper
