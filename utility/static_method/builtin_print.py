
def set_builtin_print(q):
    """내장 print 함수를 설정합니다.
    UI 큐를 통해 로그를 출력합니다.
    Args:
        q: UI 큐
    """
    import re
    import inspect
    import builtins
    from utility.settings.setting_base import UI_NUM

    # noinspection PyUnusedLocal
    def ui_print(*args, sep=' ', end='\n', file=None):
        try:
            is_direct_print = False
            frame = inspect.currentframe()
            # noinspection PyUnresolvedReferences
            caller_frame = frame.f_back.f_back
            if caller_frame:
                caller_filename = caller_frame.f_code.co_filename
                caller_function = caller_frame.f_code.co_name
                excluded_paths  = ['site-packages', 'numba', 'numpy', 'pandas', 'talib']
                is_excluded     = any(path in caller_filename for path in excluded_paths)
                if not is_excluded and caller_function != '<module>':
                    is_direct_print = True
                elif '__main__' in caller_filename:
                    is_direct_print = True

            if not is_direct_print:
                return

            processed_args = []
            for arg in args:
                if callable(arg):
                    processed_args.append(str(arg()))
                else:
                    processed_args.append(str(arg))

            message = sep.join(processed_args)
            message = message.lstrip()
            message = message.rstrip()
            message = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', message)
            q.put((UI_NUM['시스템로그'], message))
        except Exception:
            pass

    builtins.print = ui_print
