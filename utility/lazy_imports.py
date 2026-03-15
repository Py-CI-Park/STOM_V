"""
중앙 집중식 지연 로딩 모듈
numpy, pandas, talib를 지연 로딩하여 중복 로딩 방지
"""

_np = None
_pd = None
_talib = None
_talib_stream = None


def get_np():
    """numpy를 지연 로딩하여 싱글톤으로 반환"""
    global _np
    if _np is None:
        # noinspection PyShadowingNames
        import numpy as np
        _np = np
    return _np


def get_pd():
    """pandas를 지연 로딩하여 싱글톤으로 반환"""
    global _pd
    if _pd is None:
        # noinspection PyShadowingNames
        import pandas as pd
        _pd = pd
    return _pd


def get_talib():
    """talib를 지연 로딩하여 싱글톤으로 반환"""
    global _talib
    if _talib is None:
        import talib
        _talib = talib
    return _talib


def get_talib_stream():
    """talib stream을 지연 로딩하여 싱글톤으로 반환"""
    global _talib_stream
    if _talib_stream is None:
        from talib import stream
        _talib_stream = stream
    return _talib_stream
