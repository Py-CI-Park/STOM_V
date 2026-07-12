from pathlib import Path
from playwright.sync_api import sync_playwright
import json, time, html

project = Path('/mnt/data/stom-ai-dashboard-run/stom-ai-dashboard-frontend')
css = (project/'styles/theme.css').read_text(encoding='utf-8')
data_js = (project/'src/data.js').read_text(encoding='utf-8')
app_js = (project/'src/app.js').read_text(encoding='utf-8')
content = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>STOM AI · 조건식 AI 연구 대시보드</title><style>{css}</style></head><body><div id="app" class="app-shell"></div><div id="modal-root"></div><script>{data_js}</script><script>{app_js}</script></body></html>'''

out_dir = Path('/mnt/data/stom-dashboard-captures')
out_dir.mkdir(parents=True, exist_ok=True)

cases = [
    {'id':'01_condition_ai_overview','label':'조건식 AI / 조건식 AI', 'primary':'condition', 'sub':'overview', 'required':['현재 세대 라이브 상태','세대 테이블','BEST / WINNER','Human Approval','Strategy Inspector']},
    {'id':'02_process','label':'조건식 AI / 프로세스', 'primary':'condition', 'sub':'process', 'required':['프로세스 맵','Generation','Backtest','Scoring','Autopsy','Repeat','라이브 로그']},
    {'id':'03_history','label':'조건식 AI / 히스토리', 'primary':'condition', 'sub':'history', 'required':['실행/생성 히스토리','Research Records','ResultDetail','Compare','Lineage']},
    {'id':'04_lab','label':'조건식 AI / 연구실', 'primary':'condition', 'sub':'lab', 'required':['Edge Ratio','변수 중요도','상관관계','변수 조합','검증 요약']},
    {'id':'05_workbench','label':'조건식 AI / 분석 워크벤치', 'primary':'condition', 'sub':'workbench', 'required':['Hall of Fame 워크벤치','History Compare','Backtest Result Review','후보 상세 분석','리뷰 큐']},
    {'id':'06_decision_audit','label':'조건식 AI / 결정 감사', 'primary':'condition', 'sub':'audit', 'required':['결정 감사','Append-Only','PROMOTE','OOS 성과 차이','결정 히스토리']},
    {'id':'07_backtest','label':'백테스트', 'primary':'backtest', 'sub':None, 'required':['DEMO MODE','실행 파라미터','최적화','WFO','스윕','조건식 편집','결과 분석','독립 HTML 보고서']},
    {'id':'08_chart_replay','label':'차트 리플레이', 'primary':'replay', 'sub':None, 'required':['데이터 소스','재생 컨트롤','실시간 리플레이 차트','WebSocket 리플레이 상태','전략 신호 로그']},
]

results = []
console_events = []
page_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage','--disable-web-security'])
    page = browser.new_page(viewport={'width':1920,'height':1080}, device_scale_factor=1)
    page.on('console', lambda msg: console_events.append({'type':msg.type, 'text':msg.text}))
    page.on('pageerror', lambda err: page_errors.append(str(err)))
    page.set_content(content, wait_until='load')
    page.wait_for_selector('#page', timeout=10000)

    for case in cases:
        if case['primary']:
            page.click(f'button[data-primary="{case["primary"]}"]')
            page.wait_for_timeout(250)
        if case.get('sub'):
            page.click(f'button[data-sub="{case["sub"]}"]')
            page.wait_for_timeout(350)
        page.wait_for_timeout(400)
        text = page.locator('body').inner_text(timeout=5000)
        missing = [needle for needle in case['required'] if needle not in text]
        dims = page.evaluate('''() => ({w: window.innerWidth, h: window.innerHeight, sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, title: document.title})''')
        path = out_dir / f"{case['id']}.png"
        full_path = out_dir / f"{case['id']}_full.png"
        page.screenshot(path=str(path), full_page=False)
        page.screenshot(path=str(full_path), full_page=True)
        results.append({
            'id': case['id'],
            'label': case['label'],
            'screenshot': str(path),
            'full_screenshot': str(full_path),
            'missing_required_text': missing,
            'dimensions': dims,
            'status': 'PASS' if not missing else 'WARN'
        })
    browser.close()

report = {'render_mode':'inline set_content, chromium headless', 'captured_at':time.strftime('%Y-%m-%d %H:%M:%S'), 'viewport':'1920x1080', 'results':results, 'console_events':console_events, 'page_errors':page_errors}
(out_dir / 'capture-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
