# STOM (System Trade Operating Machine)

- STOM은 1초스냅샷 또는 1분봉 데이터를 기반으로 하는 단타전용 시스템트레이딩툴입니다.
- 단순한 자동매매를 넘어 강력한 백테스트, 최적화, 전진분석, 주문관리시스템(OMS)이 적용되어 있습니다.
- 키움증권 국내주식, 해외선물, 업비트, 바이낸스선물 거래소의 API가 연동되어 있습니다.
- 기본 230여개의 전략모듈이 있으며 사용자 팩터를 만들 수 있는 수식관리자가 포함되어 있습니다.
- 수식관리자는 단순한 차트 표시용이 아니라 작성한 수식명으로 전략 및 백테에서 바로 사용이 가능합니다.
- 최적화 알고리즘은 그리드, 유전, 교차검증, 베이지안을 지원하며 OPTUNA의 각종 샘플러까지 포함되어 있습니다.
- 조건최적화는 여러가지 조건을 무작위로 조합하여 백테스트하면서 전략을 자동으로 생성합니다.
- 전략 텍스트의 버전관리(버전번호 자동넘버링 및 텍스트 비교) 시스템을 통해 전략을 쉽게 관리할 수 있습니다. 
- STOM LIVE 탭에서는 사용자들의 당일실현손익 및 백테결과를 확인할 수 있습니다.
- 소스코드가 5만줄이 넘지만, 파이썬 기본 문법 정도만 배우면 누구나 쉽게 사용할 수 있도록 설계되었습니다.
- 설치 및 사용방법을 포함한 STOM에 대한 모든 강의는 아래 유튜브에 공개되어 있습니다.
- [**STOM YouTube**](https://www.youtube.com/@stomlive)
- [**STOM Community**](https://cafe.naver.com/stom)

## 라이선스 및 시리얼키

- STOM은 시스템트레이딩을 위한 도구일뿐이며 전략을 제공하거나 판매하지 않습니다.
- 소스코드의 원본 또는 수정본을 상업적으로 이용할 수 없습니다.
- 위반 시 모든 권한이 박탈되며 저작권 위반에 대한 법적 책임이 따를 수 있습니다.
- 국내주식 데이터를 타인에게 공유할 경우 코스콤과 법적 다툼이 생길 수 있습니다.
- 업데이트는 부가적으로 제공되는 것이며 영구 지속되지 않을 수 있습니다.
- 사용상 발생한 불이익은 사용자 본인의 책임입니다.

|   버전   |    시리얼키     |    주요기능    |   실행제한   |       기능제한       | 변조감지 |
|:------:|:-----------:|:----------:|:--------:|:----------------:|:----:|
| **무료** | STOM_PUBLIC | 백테스트, 백파인더 |  IP당 1개  | 최적화 및 전진분석 사용불가능 |  O   |
| **유료** |  구독결재 발급키   | 최적화, 전진분석  | 실행 제한 없음 |  모든 기능 사용 제한 없음  |  X   |

- **무료버전 사용방법**: 설정탭 시리얼키 입력란에 STOM_PUBLIC이라고 입력 후 저장
- 무료버전은 파일편집 후 제한 기능 우회 실행 시 변조를 감지하여 프로그램이 종료됩니다.
- 유료버전은 사용자편의에 맞게 소스코드를 자유롭게 수정하여 사용할 수 있습니다.
- [**구독결재문의**](https://cafe.naver.com/stom)
- [**비지니스문의**](mailto:youseonho@naver.com)

## 프로젝트 구조

```
STOM/
├── stom.py                             # 메인 실행 파일
├── stom_stock.bat                      # 국내주식 모드 실행
├── stom_coin.bat                       # 코인 모드 실행
├── stom_future.bat                     # 해외선물 모드 실행
├── pip_install_32.bat                  # 32비트 라이브러리 설치
├── pip_install_64.bat                  # 64비트 라이브러리 설치
│
├── backtest/                           # 백테스트 및 최적화
│   ├── backengine_*.py                 # 백테스트 엔진
│   ├── backfinder.py                   # 백파인더
│   ├── backtest.py                     # 백테스트
│   ├── optimiz*.py                     # 최적화, 교차검증, GA, OPTUNA, 
│   ├── rolling_walk_forward_test.py    # 전진분석
│   └── graph/                          # 백테스트 결과 그래프 저장
│
├── trade/                              # 실시간 트레이딩 모듈
│   ├── strategy_base.py                # 전략 기반 클래스 (230개+ 템플릿)
│   ├── formula_manager.py              # 사용자 팩터, 수식관리자
│   ├── risk_analyzer.py                # 리스크 분석
│   ├── microstructure_analyzer.py      # 시장미시구조 분석
│   ├── stock_korea/                    # 국내주식 API 연동
│   ├── future_oversea/                 # 해외선물 API 연동
│   ├── upbit/                          # 업비트 API 연동
│   └── binance/                        # 바이낸스 API 연동
│
├── ui/                                 # PyQt5 기반 GUI
│   ├── set_*.py                        # UI 설정 및 레이아웃
│   ├── ui_*.py                         # UI 이벤트 및 동작 처리
│   └── icon/                           # 아이콘 리소스
│
├── utility/                            # 공통 유틸리티
│   ├── chart_hoga_query_sound.py       # 차트, 호가, 쿼리, 사운드
│   ├── telegram_bot.py                 # 텔레그램봇
│   ├── webcrawling.py                  # 웹크롤링
│   └── ai_agent/                       # AI 에이전트용 전략 설명
│   └── imagefiles/                     # 주요 화면 스크린샷
│   └── pycharm/                        # 파이참 규칙 및 테마
│
├── _database/                          # 데이터베이스
└── _log/                               # 로그
```

## 기술 스택

|     분야     | 라이브러리                                  |
|:----------:|:---------------------------------------|
| **데이터 처리** | numpy, pandas, numba, talib            |
| **UI/시각화** | PyQt5, pyqtgraph, matplotlib, squarify |
| **거래소 연동** | python-binance, pyupbit, websockets    |
|  **최적화**   | optuna, cmaes                          |
| **통신/알림**  | zmq, pyttsx3, python-telegram-bot      |
|   **기타**   | cryptography, pillow,                  |

## 시스템 요구사항

### 트레이딩 용도
|   항목    | 최소 사양              | 권장 사양                 |
|:-------:|:-------------------|:----------------------|
| **CPU** | Intel i5 / Ryzen 5 | Intel i7 / Ryzen 7 이상 |
| **RAM** | 8GB                | 16GB 이상               |
| **인터넷** | 10Mbps             | 50Mbps 이상             |

### 백테스트 용도
|    항목    | 최소 사양                    | 권장 사양                         |
|:--------:|:-------------------------|:------------------------------|
| **CPU**  | Intel i7 / Ryzen 7 (8코어) | Intel i9 / Ryzen 9 이상 (16코어+) |
| **RAM**  | 32GB                     | 64GB                          |
| **저장공간** | NVMe 500GB               | NVMe 1TB 이상                   |

## STOM 주요 화면 및 기능 설명

### 홈 화면: 주요 지수 및 시장 지표
![홈화면](./utility/imagefiles/00_홈화면.png)

### 메인 트레이딩 화면: 관심종목, 체결목록, 잔고목록, 잔고평가, 거래목록, 실현손익
![기본창](./utility/imagefiles/01_기본창.png)

### 거래집계: 일별, 월별, 연도별 집계
![집계창](./utility/imagefiles/02_집계창.png)

### 전략편집기: 매수/매도 전략 조건 설정 및 편집
![전략편집기](./utility/imagefiles/03_전략편집기.png)

### 백파인더: 전략에 사용할 팩터의 데이터 탐색
![백파인더](./utility/imagefiles/04_백파인더.png)

### 최적화편집기: 그리드 최적화, 검증 최적화, 교차검증 최적화, 옵튜나 최적화
![최적화편집기](./utility/imagefiles/05_최적화편집기.png)

### 테스트편집기: 각종 최적화 테스트
![테스트편집기](./utility/imagefiles/06_테스트편집기.png)

### 전진분석: 최적화 테스트를 반복하는 전진분석
![전진분석](./utility/imagefiles/07_전진분석.png)

### 변수편집기: 최적화 파라미터 설정
![변수편집기](./utility/imagefiles/08_변수편집기.png)

### 범위편집기: 최적화 파라미터의 범위 설정
![범위편집기](./utility/imagefiles/09_범위편집기.png)

### 조건편집기: 조건 조합 최적화로 전략 탐색
![조건편집기](./utility/imagefiles/10_조건편집기.png)

### GA편집기: 유전 알고리즘 최적화
![GA편집기](./utility/imagefiles/11_GA편집기.png)

### 백테스트로그: 백테스트 진행 상황 및 로그
![백테로그](./utility/imagefiles/12_백테로그.png)

### 상세기록: 백테스트 결과 기록 및 관리
![백테기록](./utility/imagefiles/13_백테기록.png)

### 백테스트 그래프 비교: 여러 전략의 백테 그래프 비교
![백테기록_그래프비교](./utility/imagefiles/14_백테기록_그래프비교.png)

### 백테스트 스케줄러: 여러개의 백테스트 및 최적화를 스케줄링하여 실행
![백테스케쥴러](./utility/imagefiles/15_백테스케쥴러.png)

### 로그: 시스템 로그 및 오류 메시지
![로그창](./utility/imagefiles/16_로그창.png)

### 설정: 기본 설정, 전략 설정, 백테 설정, 기타 설정
![설정창](./utility/imagefiles/17_설정창.png)

### 주문관리: 주문 관리 설정 및 위험 관리 설정
![주문관리](./utility/imagefiles/18_주문관리.png)

### STOM Live: 사용자들의 실시간 매매 및 백테 정보
![스톰라이브](./utility/imagefiles/19_스톰라이브.png)

### 데이터베이스 관리
![디비관리](./utility/imagefiles/20_디비관리.png)

### 김프
![김프창](./utility/imagefiles/21_김프창.png)

### 차트: 실시간 및 DB 차트 표시
![차트창](./utility/imagefiles/22_차트창.png)

### 수식관리자: 사용자 팩터 추가, 수식명으로 전략 및 백테에서 바로 사용 가능
![수식관리자](./utility/imagefiles/23_수식관리자.png)

### 전략모듈: Ctrl+클릭으로 버튼명 및 내용 편집 가능
![전략모듈](./utility/imagefiles/24_전략모듈.png)

### 호가창: 실시간 호가 정보 및 차트 부가 정보 표시
![호가창](./utility/imagefiles/25_호가창.png)

### 기업정보: 기업개요, 공시, 뉴스, 재무재표
![기업정보](./utility/imagefiles/26_기업정보.png)

### 백테스트엔진: 엔진 설정 및 실행
![백테엔진창](./utility/imagefiles/27_백테엔진창.png)

### 업종별/테마별 트리맵
![업종별테마별트리맵](./utility/imagefiles/28_업종별테마별트리맵.png)

### 백테스트 결과 그래프
![백테결과그래프](./utility/imagefiles/29_백테결과그래프.png)

### 백테스트 결과 부가정보
![백테결과부가정보](./utility/imagefiles/30_백테결과부가정보.png)

### 텔레그램
![텔레그램 사용자버튼](./utility/imagefiles/31_텔레그램_사용자버튼.png)

### 시스템 다이어그램 I
![시스템 구조도](./utility/imagefiles/diagram_01.png)

### 시스템 다이어그램 II
![데이터 흐름도](./utility/imagefiles/diagram_02.png)
