# S9 Chrome Keyboard Accessibility 검증 결과

> 검증일: 2026-08-29
>
> 검증 브랜치: `codex/process-research-s9-keyboard-accessibility`
>
> 대상 bundle: `app.js v=9175e0f9`, `v4.css v=0e9ac4af`
>
> 검증 Surface: 외부 Chrome 확장 연결
>
> 결론: **Mission Control·Failure Autopsy·후보 근거·History Authority의 Tab·Shift+Tab·Enter·Space·focus-visible이 실제 Chrome 키 이벤트에서 동작했다. 코드 변경은 필요하지 않았다.**

---

## 1. Status Dashboard

```text
┌─────────────────────────────────────────────────────────────┐
│ S9 KEYBOARD ACCESSIBILITY                                  │
├────────────────────────┬────────────────────────────────────┤
│ Chrome Connection      │ PASS                               │
│ Tab / Shift+Tab        │ PASS                               │
│ Enter                  │ PASS                               │
│ Space                  │ PASS                               │
│ focus-visible          │ 2px solid teal · PASS             │
│ 1280                   │ PASS                               │
│ 620                    │ PASS                               │
│ Console                │ warn/error 0                       │
│ Product Code Change    │ NONE                               │
└────────────────────────┴────────────────────────────────────┘
```

---

## 2. 실제 키보드 Flow

```text
Mission Control button
  ├── Enter → evidence open / aria-expanded=true
  └── Space → evidence close / aria-expanded=false

Failure Autopsy summary
  ├── Enter → Family·Exit·후보 상세 open
  └── Space → 상세 close

Candidate evidence button
  └── Enter → Compression 후보 선택 + UX-03 근거 open

History Authority button
  ├── Shift+Tab → 이전 High theme 버튼
  ├── Tab → Authority 버튼 복귀
  ├── focus-visible → 2px solid teal
  └── Enter → ?tab=research + Mission Control visible
```

---

## 3. 1280 검증

| 대상 | 키 | 결과 |
|---|---|---|
| Mission 판정 근거 | Enter | closed→open, `aria-expanded=true` |
| Mission 판정 근거 | Space | open→closed, `aria-expanded=false` |
| Autopsy 상세 | Enter | open |
| Autopsy 상세 | Space | closed |
| Compression 후보 | Enter | 후보 선택·raw evidence open |
| History Authority | Enter | Mission Control 이동 |
| Authority focus | Shift+Tab→Tab | `High`→`최신 Mission Control 열기` |
| focus-visible | Tab | outline 2px solid `rgb(76,214,179)` |

---

## 4. 620 검증

```text
History Authority
  ├── Shift+Tab / Tab ........ PASS
  ├── focus outline 2px ...... PASS
  ├── Enter → Mission ........ PASS
  └── page overflow .......... NONE (610 = 610)

Mission Control
  ├── Enter → evidence open .. PASS
  ├── aria-expanded=true ..... PASS
  └── page overflow .......... NONE
```

console warn/error는 0이다.

---

## 5. 인앱 브라우저와 Chrome 차이

```text
Codex In-app Browser synthetic key
└── 포커스 이동, 기본 click 미발생 → INCONCLUSIVE

External Chrome extension key
└── Enter/Space 기본 동작 발생 → PASS
```

따라서 이전 제한은 제품의 native button 결함으로 확인되지 않았다. Chrome 실제 이벤트가 동작하므로 별도 onKeyDown을 추가하지 않았다. native button에 중복 key handler를 넣으면 이중 활성화 위험이 생기므로 코드 무변경이 올바른 결론이다.

---

## 6. Safety

```text
Research execution   NONE
DB write             NONE
G2                   NOT RUN
Holdout              SEALED_NOT_TOUCHED
Historical promotion NONE
Code change          NONE
```

---

## 7. 다음 단계

```text
[S9 COMPLETE]
       │
       ▼
[SYS-02 TEST ISOLATION]
  ├── seed DB 테스트 read-only
  ├── 보호 DB 0-byte 생성 방지
  ├── pytest plugin 충돌 식별
  └── full suite 의미 있는 Gate 복구
```
