"""TMAP — 경향성 지도(Tendency Map) 기반 조건식 발굴 서브시스템 (2026-06-11).

설계 문서: docs/update_log/2026-06-11_tmap_process_redesign.md
핵심: 조건식을 '점'이 아닌 '모수화 패밀리(템플릿×θ)'로 다루고, 대량 백테스트로
θ-공간의 경향성 지도를 그려 피크가 아닌 고원(plateau)을 고른다.

모듈:
  - template : 템플릿 규격(θ 슬롯)·렌더러·좌표 스윕 포인트 (G1)
  - tendency : 응답 곡선·plateau score·절벽 감지 (G3)
  - portfolio: 저상관 고원 결합(일별손익 합산 근사) (G5)
러너(스크립트):
  - scripts/tmap_sweep.py       : 지형 스윕 배치 평가 (G2)
  - scripts/tmap_walkforward.py : 전진분석 정책 드라이버 (G4)

전 모듈 분석/연구 전용 — 엔진·하드게이트·선택 규율 무수정.
"""
