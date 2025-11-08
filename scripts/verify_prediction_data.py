"""
Data integrity verification script for prediction migration.

This script verifies:
1. All records have been migrated
2. sentiment_score values are within valid range (-1.0 to 1.0)
3. impact_level values are valid (low/medium/high/critical)
4. urgency_level values are valid (routine/notable/urgent/breaking)
5. relevance_score values are within valid range (0.0 to 1.0)
6. Data consistency between old and new fields

Run: python scripts/verify_prediction_data.py
"""
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, '/Users/winter.e/easy-work/craveny')

from backend.db.models.prediction import Prediction
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_session():
    """Create database session."""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def verify_record_count(db):
    """Verify total record count."""
    logger.info("=" * 80)
    logger.info("1. Verifying Record Count")
    logger.info("=" * 80)

    total = db.query(Prediction).count()
    logger.info(f"Total records: {total}")

    if total == 0:
        logger.error("❌ No records found in database!")
        return False

    logger.info("✅ Record count verification passed")
    return True


def verify_new_fields_coverage(db):
    """Verify all records have new fields populated."""
    logger.info("\n" + "=" * 80)
    logger.info("2. Verifying New Fields Coverage")
    logger.info("=" * 80)

    total = db.query(Prediction).count()

    fields = [
        'sentiment_direction',
        'sentiment_score',
        'impact_level',
        'relevance_score',
        'urgency_level',
        'impact_analysis'
    ]

    all_passed = True

    for field in fields:
        count = db.query(Prediction).filter(
            getattr(Prediction, field).isnot(None)
        ).count()

        coverage = (count / total * 100) if total > 0 else 0

        if coverage == 100:
            logger.info(f"✅ {field}: {count}/{total} ({coverage:.1f}%)")
        else:
            logger.error(f"❌ {field}: {count}/{total} ({coverage:.1f}%)")
            all_passed = False

    return all_passed


def verify_sentiment_score_range(db):
    """Verify sentiment_score is within -1.0 to 1.0."""
    logger.info("\n" + "=" * 80)
    logger.info("3. Verifying sentiment_score Range")
    logger.info("=" * 80)

    # Get min/max/avg
    result = db.execute(text("""
        SELECT
            MIN(sentiment_score) as min_score,
            MAX(sentiment_score) as max_score,
            AVG(sentiment_score) as avg_score
        FROM predictions
        WHERE sentiment_score IS NOT NULL
    """)).fetchone()

    logger.info(f"Min: {result[0]:.4f}, Max: {result[1]:.4f}, Avg: {result[2]:.4f}")

    # Check for invalid values
    invalid = db.query(Prediction).filter(
        (Prediction.sentiment_score < -1.0) | (Prediction.sentiment_score > 1.0)
    ).count()

    if invalid == 0:
        logger.info("✅ All sentiment_score values are within valid range")
        return True
    else:
        logger.error(f"❌ Found {invalid} records with invalid sentiment_score")
        return False


def verify_impact_level_values(db):
    """Verify impact_level has valid values."""
    logger.info("\n" + "=" * 80)
    logger.info("4. Verifying impact_level Values")
    logger.info("=" * 80)

    valid_levels = ['low', 'medium', 'high', 'critical']

    # Get distribution
    result = db.execute(text("""
        SELECT impact_level, COUNT(*) as count
        FROM predictions
        WHERE impact_level IS NOT NULL
        GROUP BY impact_level
        ORDER BY impact_level
    """))

    for row in result:
        logger.info(f"  {row[0]}: {row[1]} records")

    # Check for invalid values
    invalid = db.query(Prediction).filter(
        Prediction.impact_level.notin_(valid_levels),
        Prediction.impact_level.isnot(None)
    ).count()

    if invalid == 0:
        logger.info("✅ All impact_level values are valid")
        return True
    else:
        logger.error(f"❌ Found {invalid} records with invalid impact_level")
        return False


def verify_urgency_level_values(db):
    """Verify urgency_level has valid values."""
    logger.info("\n" + "=" * 80)
    logger.info("5. Verifying urgency_level Values")
    logger.info("=" * 80)

    valid_levels = ['routine', 'notable', 'urgent', 'breaking']

    # Get distribution
    result = db.execute(text("""
        SELECT urgency_level, COUNT(*) as count
        FROM predictions
        WHERE urgency_level IS NOT NULL
        GROUP BY urgency_level
        ORDER BY urgency_level
    """))

    for row in result:
        logger.info(f"  {row[0]}: {row[1]} records")

    # Check for invalid values
    invalid = db.query(Prediction).filter(
        Prediction.urgency_level.notin_(valid_levels),
        Prediction.urgency_level.isnot(None)
    ).count()

    if invalid == 0:
        logger.info("✅ All urgency_level values are valid")
        return True
    else:
        logger.error(f"❌ Found {invalid} records with invalid urgency_level")
        return False


def verify_relevance_score_range(db):
    """Verify relevance_score is within 0.0 to 1.0."""
    logger.info("\n" + "=" * 80)
    logger.info("6. Verifying relevance_score Range")
    logger.info("=" * 80)

    # Get min/max/avg
    result = db.execute(text("""
        SELECT
            MIN(relevance_score) as min_score,
            MAX(relevance_score) as max_score,
            AVG(relevance_score) as avg_score
        FROM predictions
        WHERE relevance_score IS NOT NULL
    """)).fetchone()

    logger.info(f"Min: {result[0]:.4f}, Max: {result[1]:.4f}, Avg: {result[2]:.4f}")

    # Check for invalid values
    invalid = db.query(Prediction).filter(
        (Prediction.relevance_score < 0.0) | (Prediction.relevance_score > 1.0)
    ).count()

    if invalid == 0:
        logger.info("✅ All relevance_score values are within valid range")
        return True
    else:
        logger.error(f"❌ Found {invalid} records with invalid relevance_score")
        return False


def verify_data_consistency(db):
    """Verify consistency between old and new fields."""
    logger.info("\n" + "=" * 80)
    logger.info("7. Verifying Data Consistency")
    logger.info("=" * 80)

    # Check direction → sentiment_direction mapping
    result = db.execute(text("""
        SELECT
            direction,
            sentiment_direction,
            COUNT(*) as count
        FROM predictions
        WHERE direction IS NOT NULL AND sentiment_direction IS NOT NULL
        GROUP BY direction, sentiment_direction
    """))

    logger.info("Direction → Sentiment Direction mapping:")
    for row in result:
        logger.info(f"  {row[0]} → {row[1]}: {row[2]} records")

    # Check for inconsistencies
    inconsistent = db.execute(text("""
        SELECT COUNT(*) as count
        FROM predictions
        WHERE (
            (direction = 'up' AND sentiment_direction != 'positive') OR
            (direction = 'down' AND sentiment_direction != 'negative') OR
            (direction = 'hold' AND sentiment_direction != 'neutral')
        )
    """)).scalar()

    if inconsistent == 0:
        logger.info("✅ All direction mappings are consistent")
        return True
    else:
        logger.error(f"❌ Found {inconsistent} inconsistent mappings")
        return False


def generate_anomaly_report(db):
    """Generate report of anomalous data."""
    logger.info("\n" + "=" * 80)
    logger.info("8. Anomaly Report")
    logger.info("=" * 80)

    anomalies = []

    # Extreme sentiment scores
    extreme = db.query(Prediction).filter(
        (Prediction.sentiment_score < -0.9) | (Prediction.sentiment_score > 0.9)
    ).count()

    if extreme > 0:
        anomalies.append(f"Found {extreme} records with extreme sentiment_score (< -0.9 or > 0.9)")

    # Low relevance scores
    low_relevance = db.query(Prediction).filter(
        Prediction.relevance_score < 0.3
    ).count()

    if low_relevance > 0:
        anomalies.append(f"Found {low_relevance} records with low relevance_score (< 0.3)")

    # Impact level vs sentiment score mismatch
    mismatch = db.execute(text("""
        SELECT COUNT(*) as count
        FROM predictions
        WHERE (
            (impact_level = 'high' AND ABS(sentiment_score) < 0.5) OR
            (impact_level = 'low' AND ABS(sentiment_score) > 0.7)
        )
    """)).scalar()

    if mismatch > 0:
        anomalies.append(f"Found {mismatch} records with impact_level/sentiment_score mismatch")

    if anomalies:
        logger.warning("⚠️  Anomalies detected:")
        for anomaly in anomalies:
            logger.warning(f"  - {anomaly}")
    else:
        logger.info("✅ No anomalies detected")

    return len(anomalies) == 0


def generate_summary(db):
    """Generate migration summary."""
    logger.info("\n" + "=" * 80)
    logger.info("9. Migration Summary")
    logger.info("=" * 80)

    result = db.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN sentiment_direction = 'positive' THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN sentiment_direction = 'negative' THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN sentiment_direction = 'neutral' THEN 1 ELSE 0 END) as neutral,
            SUM(CASE WHEN impact_level = 'high' THEN 1 ELSE 0 END) as high_impact,
            SUM(CASE WHEN impact_level = 'medium' THEN 1 ELSE 0 END) as medium_impact,
            SUM(CASE WHEN impact_level = 'low' THEN 1 ELSE 0 END) as low_impact,
            SUM(CASE WHEN impact_level = 'critical' THEN 1 ELSE 0 END) as critical_impact
        FROM predictions
    """)).fetchone()

    total = result[0]
    logger.info(f"Total records: {total}")
    logger.info(f"\nSentiment Distribution:")
    logger.info(f"  Positive: {result[1]} ({result[1]/total*100:.1f}%)")
    logger.info(f"  Negative: {result[2]} ({result[2]/total*100:.1f}%)")
    logger.info(f"  Neutral: {result[3]} ({result[3]/total*100:.1f}%)")
    logger.info(f"\nImpact Level Distribution:")
    logger.info(f"  Critical: {result[7]} ({result[7]/total*100:.1f}%)")
    logger.info(f"  High: {result[4]} ({result[4]/total*100:.1f}%)")
    logger.info(f"  Medium: {result[5]} ({result[5]/total*100:.1f}%)")
    logger.info(f"  Low: {result[6]} ({result[6]/total*100:.1f}%)")


def save_anomaly_report(db):
    """Save anomaly report to file."""
    logger.info("\n" + "=" * 80)
    logger.info("10. Saving Anomaly Report")
    logger.info("=" * 80)

    report_path = '/Users/winter.e/easy-work/craveny/scripts/anomaly_report.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Prediction Migration Anomaly Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Extreme sentiment scores
        f.write("## 1. Extreme Sentiment Scores\n\n")
        extreme = db.query(Prediction).filter(
            (Prediction.sentiment_score < -0.9) | (Prediction.sentiment_score > 0.9)
        ).all()

        if extreme:
            f.write(f"Found {len(extreme)} records with extreme sentiment scores:\n\n")
            f.write("| ID | Stock Code | Sentiment Direction | Sentiment Score |\n")
            f.write("|---|---|---|---|\n")
            for p in extreme[:20]:  # Limit to 20 records
                f.write(f"| {p.id} | {p.stock_code} | {p.sentiment_direction} | {p.sentiment_score:.4f} |\n")
        else:
            f.write("No extreme sentiment scores found.\n")

        # Low relevance scores
        f.write("\n## 2. Low Relevance Scores\n\n")
        low_relevance = db.query(Prediction).filter(
            Prediction.relevance_score < 0.3
        ).all()

        if low_relevance:
            f.write(f"Found {len(low_relevance)} records with low relevance scores:\n\n")
            f.write("| ID | Stock Code | Relevance Score | Impact Level |\n")
            f.write("|---|---|---|---|\n")
            for p in low_relevance[:20]:
                f.write(f"| {p.id} | {p.stock_code} | {p.relevance_score:.4f} | {p.impact_level} |\n")
        else:
            f.write("No low relevance scores found.\n")

        # Impact level mismatches
        f.write("\n## 3. Impact Level / Sentiment Score Mismatches\n\n")
        mismatch = db.execute(text("""
            SELECT id, stock_code, sentiment_score, impact_level
            FROM predictions
            WHERE (
                (impact_level = 'high' AND ABS(sentiment_score) < 0.5) OR
                (impact_level = 'low' AND ABS(sentiment_score) > 0.7)
            )
            LIMIT 20
        """))

        mismatch_list = list(mismatch)
        if mismatch_list:
            f.write(f"Found mismatches between impact_level and sentiment_score:\n\n")
            f.write("| ID | Stock Code | Sentiment Score | Impact Level |\n")
            f.write("|---|---|---|---|\n")
            for row in mismatch_list:
                f.write(f"| {row[0]} | {row[1]} | {row[2]:.4f} | {row[3]} |\n")
        else:
            f.write("No mismatches found.\n")

    logger.info(f"✅ Anomaly report saved to {report_path}")


def main():
    """Main verification function."""
    logger.info("🚀 Starting Prediction Data Verification")
    logger.info("=" * 80)

    db = get_db_session()

    try:
        # Run all verifications
        results = []

        results.append(("Record Count", verify_record_count(db)))
        results.append(("New Fields Coverage", verify_new_fields_coverage(db)))
        results.append(("Sentiment Score Range", verify_sentiment_score_range(db)))
        results.append(("Impact Level Values", verify_impact_level_values(db)))
        results.append(("Urgency Level Values", verify_urgency_level_values(db)))
        results.append(("Relevance Score Range", verify_relevance_score_range(db)))
        results.append(("Data Consistency", verify_data_consistency(db)))
        results.append(("Anomaly Detection", generate_anomaly_report(db)))

        # Generate summary
        generate_summary(db)

        # Save anomaly report
        save_anomaly_report(db)

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("Verification Summary")
        logger.info("=" * 80)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for check, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {check}")

        logger.info("=" * 80)
        logger.info(f"Total: {passed}/{total} checks passed")

        if passed == total:
            logger.info("🎉 All verification checks passed!")
            return 0
        else:
            logger.error(f"⚠️  {total - passed} verification checks failed")
            return 1

    except Exception as e:
        logger.error(f"❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
