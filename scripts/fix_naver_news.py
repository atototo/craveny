"""
NAVER 종목으로 잘못 분류된 뉴스를 수정하는 스크립트

문제: "NAVER" 키워드로 검색 시 출처가 "네이버(XX)"인 모든 뉴스가 검색되어
     실제 NAVER 회사와 관련 없는 기사도 NAVER 종목(035420)으로 분류됨

해결: 제목과 본문에 "네이버" 또는 "NAVER"가 없는 기사의 stock_code를 NULL로 변경
"""
import sys
import os

# 프로젝트 루트 디렉토리를 PYTHONPATH에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.prediction import Prediction
from backend.db.models.stock_analysis import StockAnalysisSummary


def fix_naver_news():
    """
    NAVER 종목으로 잘못 분류된 뉴스를 수정합니다.
    """
    db = SessionLocal()

    try:
        # NAVER 종목(035420)으로 분류된 모든 뉴스 조회
        naver_news = db.query(NewsArticle).filter(
            NewsArticle.stock_code == "035420"
        ).all()

        print(f"📊 NAVER 종목 뉴스: {len(naver_news)}건")

        fixed_count = 0
        kept_count = 0

        for news in naver_news:
            # 제목과 본문에 "네이버" 또는 "NAVER"가 있는지 확인
            title = news.title if news.title else ""
            content = news.content if news.content else ""

            # 전체 텍스트 합치기
            full_text = f"{title} {content}"

            # 플랫폼 관련 단어는 제외하고 NAVER 회사 관련 내용만 확인
            # 제외할 패턴: 네이버증권, 네이버메인, 네이버뉴스, 네이버에서 등
            exclude_patterns = [
                "네이버증권",
                "네이버메인",
                "네이버뉴스",
                "네이버에서",
                "네이버를",
                "MBC뉴스를네이버",
                "뉴스를네이버",
            ]

            # 제외 패턴을 임시로 제거
            text_for_check = full_text
            for pattern in exclude_patterns:
                text_for_check = text_for_check.replace(pattern, "")

            # NAVER 회사 관련 키워드가 있는지 확인
            company_keywords = [
                "네이버 주가",
                "네이버 실적",
                "네이버 매출",
                "네이버 영업이익",
                "네이버 투자",
                "네이버 사업",
                "네이버웹툰",
                "네이버페이",
                "네이버클라우드",
                "NAVER",  # 대문자 NAVER는 회사명
            ]

            has_naver = any(keyword in text_for_check for keyword in company_keywords)

            if not has_naver:
                # 네이버 관련 내용이 없으면 stock_code를 NULL로 변경
                print(f"❌ 수정: [{news.id}] {title[:60]}...")
                print(f"   출처: {news.source}")
                news.stock_code = None
                fixed_count += 1
            else:
                # 네이버 회사 관련 내용이 있으면 유지
                print(f"✅ 유지: [{news.id}] {title[:60]}...")
                # 매칭된 키워드 표시
                matched_keywords = [kw for kw in company_keywords if kw in text_for_check]
                print(f"   → 매칭된 키워드: {', '.join(matched_keywords)}")
                kept_count += 1

        # 변경사항 저장
        db.commit()

        print("\n" + "="*60)
        print(f"✅ 뉴스 데이터 수정 완료!")
        print(f"   - 수정됨: {fixed_count}건 (stock_code → NULL)")
        print(f"   - 유지됨: {kept_count}건 (실제 NAVER 뉴스)")
        print("="*60)

        # 2. 잘못된 예측 데이터 삭제
        print("\n🗑️  잘못된 예측 데이터 삭제 중...")

        # stock_code가 NULL로 변경된 뉴스의 예측 데이터 찾기
        deleted_predictions = 0
        for news in naver_news:
            if news.stock_code is None:  # stock_code가 NULL로 변경된 경우
                # 해당 뉴스의 예측 데이터 삭제
                predictions = db.query(Prediction).filter(
                    Prediction.news_id == news.id
                ).all()

                for pred in predictions:
                    db.delete(pred)
                    deleted_predictions += 1

        db.commit()
        print(f"✅ 예측 데이터 {deleted_predictions}건 삭제 완료")

        # 3. NAVER 종목 분석 리포트 삭제 (재생성 필요)
        print("\n🗑️  NAVER 종목 분석 리포트 삭제 중...")
        summary = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.stock_code == "035420"
        ).first()

        if summary:
            db.delete(summary)
            db.commit()
            print(f"✅ 분석 리포트 삭제 완료 (다음 조회 시 자동 재생성됨)")
        else:
            print(f"ℹ️  삭제할 분석 리포트 없음")

        print("\n" + "="*60)
        print(f"✅ 전체 수정 완료!")
        print(f"   - 뉴스 수정: {fixed_count}건")
        print(f"   - 예측 삭제: {deleted_predictions}건")
        print(f"   - 분석 리포트: 삭제됨 (자동 재생성 예정)")
        print("="*60)

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("🔧 NAVER 종목 뉴스 수정 시작")
    print("="*60)
    print()

    fix_naver_news()
