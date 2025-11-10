"""
DB 테이블 확인 스크립트
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect
from backend.db.session import engine

inspector = inspect(engine)
tables = inspector.get_table_names()

print("📋 현재 데이터베이스 테이블:")
print("=" * 60)
for table in sorted(tables):
    print(f"  ✓ {table}")

print("=" * 60)
print(f"총 {len(tables)}개 테이블")

# 시장 데이터 관련 테이블 확인
market_tables = [t for t in tables if any(x in t for x in ['stock', 'investor', 'sector', 'orderbook', 'current'])]
print("\n📊 시장 데이터 관련 테이블:")
print("=" * 60)
for table in market_tables:
    # 레코드 수 확인
    from backend.db.session import SessionLocal
    db = SessionLocal()
    from sqlalchemy import text
    result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
    count = result.scalar()
    db.close()
    print(f"  {table}: {count:,}건")
