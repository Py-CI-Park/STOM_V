"""STOM AI strategy loop package.

Newsletter_AI의 AI provider 메커니즘(gpt auth / openrouter / codex_proxy)을
STOM 내부에 standalone으로 이식한 패키지.

IMPORTANT (env isolation contract):
    루프 엔트리포인트는 반드시 `import ai_strategy_loop.bootstrap` 을
    cli.* / utility.* import 보다 먼저 수행해야 한다. bootstrap이 import
    시점에 STOM_CLI_DB_STRATEGY 등을 격리 DB 경로로 설정한다.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
