"""
전략 코드 정적 가드 유틸.

중요:
- 이 모듈은 완전한 보안 샌드박스가 아니다.
- 신뢰 가능한(로컬/관리자 통제) 전략 코드에 대해
  치명적인 실수/명백한 위험 구문을 조기에 차단하기 위한 1차 방어선이다.
"""

import ast
import dis
import types
import weakref


class UnsafeStrategyCodeError(ValueError):
    """전략 코드 안전 검증 실패."""


_BANNED_NAME_TOKENS = {
    '__import__', '__builtins__', 'eval', 'exec', 'open', 'compile',
    'globals', 'locals', 'vars', 'getattr', 'setattr', 'delattr',
    'os', 'subprocess', 'ctypes', 'socket', 'shutil', 'pathlib'
}

_BANNED_IMPORT_OPS = {'IMPORT_NAME', 'IMPORT_FROM', 'IMPORT_STAR'}
_BANNED_TEXT_TOKENS = {'__builtins__', '__globals__', '__subclasses__', '__mro__', '__class__'}
_VALIDATED_CODE_OBJS = weakref.WeakSet()


def _is_dunder_name(value):
    return isinstance(value, str) and value.startswith('__') and value.endswith('__')


def _ctx(context):
    return f' [{context}]' if context else ''


def _raise(reason, context=''):
    raise UnsafeStrategyCodeError(f'Unsafe strategy code{_ctx(context)}: {reason}')


def _assert_safe_ast(source, context=''):
    compact = source.replace(' ', '').replace('\t', '')
    for token in _BANNED_TEXT_TOKENS:
        if token in compact:
            _raise(f"use of '{token}' is not allowed", context)

    try:
        tree = ast.parse(source, mode='exec')
    except SyntaxError as e:
        _raise(f'syntax error: {e.msg}', context)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _raise('import statements are not allowed', context)

        if isinstance(node, ast.Name) and node.id in _BANNED_NAME_TOKENS:
            _raise(f"use of '{node.id}' is not allowed", context)
        if isinstance(node, ast.Name) and _is_dunder_name(node.id):
            _raise(f"use of '{node.id}' is not allowed", context)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BANNED_NAME_TOKENS:
                _raise(f"call to '{node.func.id}' is not allowed", context)
            if isinstance(node.func, ast.Attribute):
                root = node.func
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name) and root.id in _BANNED_NAME_TOKENS:
                    _raise(f"use of '{root.id}' is not allowed", context)

        if isinstance(node, ast.Attribute):
            if _is_dunder_name(node.attr):
                _raise(f"use of '{node.attr}' is not allowed", context)
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id in _BANNED_NAME_TOKENS:
                _raise(f"use of '{root.id}' is not allowed", context)


def _contains_banned_text(value):
    if isinstance(value, str):
        return value in _BANNED_TEXT_TOKENS or _is_dunder_name(value)
    if isinstance(value, (tuple, list, set, frozenset)):
        return any(_contains_banned_text(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_banned_text(k) or _contains_banned_text(v) for k, v in value.items())
    return False


def _assert_safe_code_obj(code_obj, context=''):
    for name in code_obj.co_names:
        if name in _BANNED_TEXT_TOKENS or _is_dunder_name(name):
            _raise(f"use of '{name}' is not allowed", context)

    for ins in dis.get_instructions(code_obj):
        if ins.opname in _BANNED_IMPORT_OPS:
            _raise('import opcodes are not allowed', context)
        if ins.opname in {'LOAD_NAME', 'LOAD_GLOBAL', 'LOAD_DEREF'}:
            if isinstance(ins.argval, str) and (ins.argval in _BANNED_NAME_TOKENS or _is_dunder_name(ins.argval)):
                _raise(f"use of '{ins.argval}' is not allowed", context)
        if ins.opname in {'LOAD_ATTR', 'LOAD_METHOD'}:
            if isinstance(ins.argval, str) and (
                ins.argval in _BANNED_TEXT_TOKENS or
                _is_dunder_name(ins.argval)
            ):
                _raise(f"use of '{ins.argval}' is not allowed", context)
        if ins.opname == 'LOAD_CONST' and _contains_banned_text(ins.argval):
            _raise(f"use of '{ins.argval}' is not allowed", context)

    for const in code_obj.co_consts:
        if isinstance(const, types.CodeType):
            _assert_safe_code_obj(const, context)
        elif _contains_banned_text(const):
            _raise(f"use of '{const}' is not allowed", context)


def assert_safe_code(code, context=''):
    """
    문자열 또는 compile된 code object를 정적 검증한다.
    """
    if isinstance(code, str):
        _assert_safe_ast(code, context)
    elif isinstance(code, types.CodeType):
        _assert_safe_code_obj(code, context)
    else:
        _raise(f'unsupported code type: {type(code)!r}', context)


def guard_exec_code(code, context=''):
    """
    exec 직전 사용: 코드 검증 후 원본 코드 반환.
    """
    if isinstance(code, types.CodeType):
        if code not in _VALIDATED_CODE_OBJS:
            assert_safe_code(code, context)
            _VALIDATED_CODE_OBJS.add(code)
    else:
        assert_safe_code(code, context)
    return code


def safe_compile(source, filename='<string>', mode='exec', context=''):
    """
    compile 전에 소스 검증 후 code object 반환.
    """
    assert_safe_code(source, context)
    code_obj = compile(source, filename, mode)
    assert_safe_code(code_obj, context)
    return code_obj
