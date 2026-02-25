"""
Strategy Command for CLI
========================

전략 관리 CLI 명령 (list/show/export).
"""

import click
import sqlite3
import pandas as pd
import json
import builtins
from pathlib import Path
from typing import Optional, List
from utility.static import get_logger
from utility.safe_exec import safe_compile, UnsafeStrategyCodeError
from cli.adapters.output_adapter import OutputAdapter, OutputFormat

logger_ = get_logger('StrategyCommand')

# 데이터베이스 경로
DB_STRATEGY = './_database/strategy.db'


@click.group()
def strategy():
    """전략 관리 명령"""
    pass


@strategy.command(name='list')
@click.option('--type', 'type_filter', type=click.Choice(['stock', 'coin', 'future']),
              help='전략 타입 필터링')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def list_strategies(type_filter: Optional[str], format: str):
    """전략 목록 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        if not tables:
            output_adapter.output("등록된 전략이 없습니다.", title="전략 목록")
            con.close()
            return

        all_strategies = []

        for (table_name,) in tables:
            # 각 테이블에서 데이터 조회
            try:
                # Use identifier quoting to safely reference table name
                query = f'SELECT * FROM "{table_name}"'
                df = pd.read_sql(query, con)

                if len(df) > 0:
                    # 테이블명에 따른 타입 결정
                    if 'stock' in table_name.lower():
                        strategy_type = 'stock'
                    elif 'coin' in table_name.lower():
                        strategy_type = 'coin'
                    elif 'future' in table_name.lower():
                        strategy_type = 'future'
                    else:
                        strategy_type = 'unknown'

                    # 타입 필터링
                    if type_filter and strategy_type != type_filter:
                        continue

                    df['전략타입'] = strategy_type
                    df['테이블'] = table_name
                    all_strategies.append(df)

            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")
                continue

        con.close()

        if not all_strategies:
            output_adapter.output(f"'{type_filter}' 타입의 전략이 없습니다.", title="전략 목록")
            return

        # 모든 전략 합치기
        result_df = pd.concat(all_strategies, ignore_index=True)

        # 필요한 컬럼만 선택
        display_cols = []
        for col in ['전략타입', '테이블'] + builtins.list(result_df.columns):
            if col in result_df.columns and col not in display_cols:
                display_cols.append(col)
        result_df = result_df[display_cols]

        output_adapter.output(result_df, title="전략 목록")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "전략 목록 조회 실패"))
        logger_.error(f"Error listing strategies: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.argument('strategy_name')
@click.option('--type', 'strategy_type', type=click.Choice(['stock', 'coin', 'future']), required=False)
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def show(strategy_name: str, strategy_type: Optional[str], format: str):
    """특정 전략 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)

        # Validate strategy_name against existing tables to prevent SQL injection
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        valid_tables = [row[0] for row in cursor.fetchall()]

        if strategy_name not in valid_tables:
            click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 테이블에서 전략 조회
        query = f"SELECT * FROM {strategy_name}"
        df = pd.read_sql(query, con)
        con.close()

        if len(df) == 0:
            output_adapter.output(f"'{strategy_name}' 전략을 찾을 수 없습니다.",
                                title="전략 조회")
            return

        output_adapter.output(df, title=f"전략: {strategy_name}")

    except sqlite3.OperationalError:
        click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
        logger_.error(f"Strategy table {strategy_name} not found")
        raise click.ClickException(f"Strategy not found: {strategy_name}")
    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "전략 조회 실패"))
        logger_.error(f"Error showing strategy: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.argument('strategy_name')
@click.argument('output_file', type=click.Path())
@click.option('--format', type=click.Choice(['csv', 'json', 'excel']),
              default='csv', help='내보내기 포맷')
def export(strategy_name: str, output_file: str, format: str):
    """전략 내보내기"""
    try:
        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)

        # Validate strategy_name against existing tables to prevent SQL injection
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        valid_tables = [row[0] for row in cursor.fetchall()]

        if strategy_name not in valid_tables:
            click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 테이블에서 전략 조회
        query = f"SELECT * FROM {strategy_name}"
        df = pd.read_sql(query, con)
        con.close()

        if len(df) == 0:
            click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
            return

        # 출력 디렉토리 생성
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 포맷에 따라 내보내기
        if format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif format == 'json':
            df.to_json(output_path, orient='records', indent=2, force_ascii=False)
        elif format == 'excel':
            df.to_excel(output_path, index=False)

        click.echo(f"전략이 {output_path}로 내보내어졌습니다.")
        logger_.info(f"Strategy {strategy_name} exported to {output_path}")

    except sqlite3.OperationalError:
        click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
        logger_.error(f"Strategy table {strategy_name} not found")
        raise click.ClickException(f"Strategy not found: {strategy_name}")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 내보내기 실패"))
        logger_.error(f"Error exporting strategy: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def stats(format: str):
    """전략 통계"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        stats = {
            'Total Strategies': len(tables),
            'Strategies': {}
        }

        for (table_name,) in tables:
            try:
                # Use identifier quoting to safely reference table name
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]
                stats['Strategies'][table_name] = count
            except Exception as e:
                logger_.warning(f"Failed to count {table_name}: {e}")

        con.close()

        # 포맷에 따라 출력
        if format == 'json':
            output_adapter.output(stats, title="전략 통계")
        else:
            # 테이블 포맷
            lines = []
            lines.append("=" * 60)
            lines.append("전략 통계")
            lines.append("=" * 60)
            lines.append(f"\n총 전략 수: {stats['Total Strategies']}")
            lines.append("\n전략별 항목 수:")
            for name, count in stats['Strategies'].items():
                lines.append(f"  {name}: {count}")

            click.echo('\n'.join(lines))

        logger_.info("Strategy stats retrieved")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 통계 조회 실패"))
        logger_.error(f"Error getting strategy stats: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.option('--name', required=True, help='전략 이름')
@click.option('--type', 'strategy_type', required=True,
              type=click.Choice(['stock', 'coin', 'future']), help='전략 타입')
@click.option('--buy/--sell', 'is_buy', default=True, help='매수/매도 전략')
@click.option('--code', help='전략 코드 (문자열)')
@click.option('--file', 'code_file', type=click.Path(exists=True), help='전략 코드 파일 경로')
def save(name: str, strategy_type: str, is_buy: bool, code: Optional[str], code_file: Optional[str]):
    """전략 저장"""
    try:
        # 코드 또는 파일 중 하나는 필수
        if not code and not code_file:
            raise click.ClickException("--code 또는 --file 중 하나는 필수입니다.")

        if code and code_file:
            raise click.ClickException("--code와 --file을 동시에 사용할 수 없습니다.")

        # 파일에서 코드 읽기
        if code_file:
            code_path = Path(code_file)
            code = code_path.read_text(encoding='utf-8')
            click.echo(f"파일에서 전략 코드를 읽었습니다: {code_file}")

        # 테이블 이름 결정
        table_name = f"{strategy_type}{'buy' if is_buy else 'sell'}"

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            # 테이블 생성 (기본 스키마)
            cursor.execute(f"""
                CREATE TABLE {table_name} (
                    name TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            click.echo(f"테이블 '{table_name}'이 생성되었습니다.")

        # 전략 존재 여부 확인
        cursor.execute(f"SELECT name FROM {table_name} WHERE name=?", (name,))
        existing = cursor.fetchone()

        if existing:
            # 업데이트
            cursor.execute(f"""
                UPDATE {table_name}
                SET code=?, updated_at=CURRENT_TIMESTAMP
                WHERE name=?
            """, (code, name))
            click.echo(f"전략 '{name}'이 업데이트되었습니다.")
            logger_.info(f"Strategy {name} updated in {table_name}")
        else:
            # 삽입
            cursor.execute(f"""
                INSERT INTO {table_name} (name, code)
                VALUES (?, ?)
            """, (name, code))
            click.echo(f"전략 '{name}'이 저장되었습니다.")
            logger_.info(f"Strategy {name} saved to {table_name}")

        con.commit()
        con.close()

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 저장 실패"))
        logger_.error(f"Error saving strategy: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.option('--name', required=True, help='전략 이름')
@click.option('--type', 'strategy_type', required=True,
              type=click.Choice(['stock', 'coin', 'future']), help='전략 타입')
@click.option('--buy/--sell', 'is_buy', default=True, help='매수/매도 전략')
@click.confirmation_option(prompt='정말로 삭제하시겠습니까?')
def delete(name: str, strategy_type: str, is_buy: bool):
    """전략 삭제"""
    try:
        # 테이블 이름 결정
        table_name = f"{strategy_type}{'buy' if is_buy else 'sell'}"

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            click.echo(f"Error: 테이블 '{table_name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 전략 존재 여부 확인
        cursor.execute(f"SELECT name FROM {table_name} WHERE name=?", (name,))
        if not cursor.fetchone():
            click.echo(f"Error: 전략 '{name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 전략 삭제
        cursor.execute(f"DELETE FROM {table_name} WHERE name=?", (name,))
        con.commit()
        con.close()

        click.echo(f"전략 '{name}'이 삭제되었습니다.")
        logger_.info(f"Strategy {name} deleted from {table_name}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 삭제 실패"))
        logger_.error(f"Error deleting strategy: {e}")
        raise click.ClickException(str(e))


@strategy.command(name='import')
@click.option('--file', 'import_file', required=True, type=click.Path(exists=True), help='가져올 파일 경로')
@click.option('--type', 'strategy_type', required=True,
              type=click.Choice(['stock', 'coin', 'future']), help='전략 타입')
def import_cmd(import_file: str, strategy_type: str):
    """파일에서 전략 가져오기"""
    try:
        file_path = Path(import_file)

        # 파일 형식 확인
        if file_path.suffix.lower() == '.json':
            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # DataFrame으로 변환
            if isinstance(data, builtins.list):
                df = pd.DataFrame(data)
            elif isinstance(data, builtins.dict):
                df = pd.DataFrame([data])
            else:
                raise click.ClickException("지원되지 않는 JSON 형식입니다.")

        elif file_path.suffix.lower() == '.csv':
            # CSV 파일 읽기
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        else:
            raise click.ClickException("지원되지 않는 파일 형식입니다. (json, csv만 지원)")

        if len(df) == 0:
            click.echo("Error: 파일에 데이터가 없습니다.")
            return

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)

        # 테이블 이름은 파일의 메타데이터나 사용자 입력으로 결정
        # 간단하게 buy/sell을 파일에서 추론하거나 기본값 사용
        # 여기서는 'buy'와 'sell' 모두 가져올 수 있도록 처리

        imported_count = 0
        for _, row in df.iterrows():
            # 각 행의 테이블 정보 확인
            if 'table' in df.columns or '테이블' in df.columns:
                table_col = 'table' if 'table' in df.columns else '테이블'
                table_name = row[table_col]
            else:
                # 테이블 정보가 없으면 기본값 사용 (stockbuy 등)
                table_name = f"{strategy_type}buy"

            # 테이블이 존재하는지 확인하고 없으면 생성
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE TABLE {table_name} (
                        name TEXT PRIMARY KEY,
                        code TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            # 데이터 삽입 (중복 시 업데이트)
            # row를 dict로 변환하고 필요한 컬럼만 사용
            row_dict = row.to_dict()

            # 필수 컬럼 확인
            if 'name' not in row_dict or 'code' not in row_dict:
                logger_.warning(f"Skipping row without name or code: {row_dict}")
                continue

            name = row_dict['name']
            code = row_dict['code']

            # INSERT OR REPLACE
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name} (name, code)
                VALUES (?, ?)
            """, (name, code))
            imported_count += 1

        con.commit()
        con.close()

        click.echo(f"{imported_count}개의 전략이 가져와졌습니다.")
        logger_.info(f"Imported {imported_count} strategies from {import_file}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 가져오기 실패"))
        logger_.error(f"Error importing strategies: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.option('--name', required=True, help='전략 이름')
@click.option('--type', 'strategy_type', required=True,
              type=click.Choice(['stock', 'coin', 'future']), help='전략 타입')
@click.option('--buy/--sell', 'is_buy', default=True, help='매수/매도 전략')
def validate(name: str, strategy_type: str, is_buy: bool):
    """전략 코드 유효성 검사"""
    try:
        # 테이블 이름 결정
        table_name = f"{strategy_type}{'buy' if is_buy else 'sell'}"

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            click.echo(f"Error: 테이블 '{table_name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 전략 코드 가져오기
        cursor.execute(f"SELECT code FROM {table_name} WHERE name=?", (name,))
        result = cursor.fetchone()
        con.close()

        if not result:
            click.echo(f"Error: 전략 '{name}'을 찾을 수 없습니다.")
            return

        code = result[0]

        # 기본 구문 검사
        errors = []
        warnings = []

        # Python 구문/안전성 검사
        try:
            safe_compile(
                code,
                '<string>',
                'exec',
                context=f'CLI.strategy.validate.{table_name}.{name}'
            )
        except UnsafeStrategyCodeError as e:
            errors.append(f"안전성 검사 오류: {e}")
        except SyntaxError as e:
            errors.append(f"구문 오류 (줄 {e.lineno}): {e.msg}")

        # 기본 패턴 검사
        if 'def' not in code:
            warnings.append("함수 정의가 없습니다.")

        if len(code.strip()) < 10:
            warnings.append("전략 코드가 너무 짧습니다.")

        # 결과 출력
        click.echo("=" * 60)
        click.echo(f"전략 유효성 검사: {name}")
        click.echo("=" * 60)

        if errors:
            click.echo("\n오류:")
            for error in errors:
                click.echo(f"  - {error}")

        if warnings:
            click.echo("\n경고:")
            for warning in warnings:
                click.echo(f"  - {warning}")

        if not errors and not warnings:
            click.echo("\n전략 코드가 유효합니다.")
        elif not errors:
            click.echo("\n전략 코드는 유효하지만 경고가 있습니다.")
        else:
            click.echo("\n전략 코드에 오류가 있습니다.")

        logger_.info(f"Validated strategy {name} in {table_name}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 유효성 검사 실패"))
        logger_.error(f"Error validating strategy: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    strategy()
