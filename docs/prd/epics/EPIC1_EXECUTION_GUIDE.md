# Epic 1 Execution Guide

**Epic**: Data Model Changes
**Status**: Stories 1.1, 1.2, 1.4 completed - Ready for Story 1.3 (Migration Execution)
**Date**: 2025-01-06

---

## Completed Stories

### Story 1.1: Prediction Model Schema Update ✅

**Files Modified**:
- `/Users/winter.e/easy-work/craveny/backend/db/models/prediction.py`

**Changes**:
1. Added new impact analysis fields:
   - `sentiment_direction` (VARCHAR(10), nullable)
   - `sentiment_score` (FLOAT, nullable)
   - `impact_level` (VARCHAR(20), nullable)
   - `relevance_score` (FLOAT, nullable)
   - `urgency_level` (VARCHAR(20), nullable)
   - `impact_analysis` (JSON, nullable)

2. Marked deprecated fields with comments:
   - `direction` → Use `sentiment_direction`
   - `confidence` → Use `sentiment_score` and `impact_level`
   - `short_term`, `medium_term`, `long_term` → Moved to Investment Report
   - `confidence_breakdown` → Use `impact_analysis`

3. Updated docstring and `__repr__` method

**Verification**: Model structure updated successfully

---

### Story 1.2: Migration Script Creation ✅

**Files Created**:
- `/Users/winter.e/easy-work/craveny/backend/db/migrations/add_impact_analysis_fields.py`
- `/Users/winter.e/easy-work/craveny/scripts/verify_migration.sql`
- `/Users/winter.e/easy-work/craveny/scripts/rollback_migration.sql`

**Migration Logic**:
1. Add new columns (all nullable)
2. Make deprecated columns nullable
3. Transform existing data:
   - `direction` → `sentiment_direction`:
     - "up" → "positive"
     - "down" → "negative"
     - "hold" → "neutral"

   - `confidence` → `sentiment_score`:
     - "up" direction: `confidence / 100.0` (0.0 to 1.0)
     - "down" direction: `-confidence / 100.0` (-1.0 to 0.0)
     - "hold" direction: `0.0`

   - `confidence` → `impact_level`:
     - confidence >= 70: "high"
     - confidence 50-70: "medium"
     - confidence < 50: "low"

   - Default values:
     - `relevance_score`: 0.8
     - `urgency_level`: "notable"
     - `impact_analysis`: `{"business_impact": "기존 예측 데이터", "market_sentiment": "마이그레이션됨"}`

4. Verify migration success
5. Commit transaction

**Rollback Support**: Yes - included in migration script and separate SQL file

---

### Story 1.4: Verification Script Creation ✅

**Files Created**:
- `/Users/winter.e/easy-work/craveny/scripts/verify_prediction_data.py`

**Verification Checks**:
1. Record count verification
2. New fields coverage (100% expected)
3. `sentiment_score` range (-1.0 to 1.0)
4. `impact_level` valid values (low/medium/high/critical)
5. `urgency_level` valid values (routine/notable/urgent/breaking)
6. `relevance_score` range (0.0 to 1.0)
7. Data consistency (direction ↔ sentiment_direction mapping)
8. Anomaly detection and reporting

**Output**:
- Console logs with detailed verification results
- Anomaly report file: `scripts/anomaly_report.md`

---

## Story 1.3: Migration Execution (PENDING - MANUAL STEP)

### Prerequisites

**CRITICAL - DO THIS FIRST**:

1. **Database Backup**:
   ```bash
   # PostgreSQL backup
   pg_dump -h <host> -U <user> -d craveny > backup_$(date +%Y%m%d_%H%M%S).sql

   # Verify backup file
   ls -lh backup_*.sql
   ```

2. **Staging Environment Test** (REQUIRED):
   - Test migration on staging database first
   - Verify all 1164 records migrate successfully
   - Check for any errors or warnings
   - Run verification script
   - Only proceed to production if staging succeeds

3. **Downtime Planning** (if needed):
   - Estimated migration time: < 1 minute for 1164 records
   - Consider running during off-peak hours
   - Notify stakeholders if downtime is required

### Execution Steps

#### Step 1: Pre-Migration Checks

```bash
# Navigate to project directory
cd /Users/winter.e/easy-work/craveny

# Activate virtual environment (if using uv)
source .venv/bin/activate

# Verify current database state
psql -h <host> -U <user> -d craveny -c "SELECT COUNT(*) FROM predictions;"
# Expected: 1164 records

# Check current schema
psql -h <host> -U <user> -d craveny -c "\d predictions"
```

#### Step 2: Run Migration (Staging First)

```bash
# Run migration script
python backend/db/migrations/add_impact_analysis_fields.py

# Check logs for:
# - "Migration completed successfully" message
# - Record count verification
# - Field coverage statistics
```

**Expected Output**:
```
🚀 Starting migration: add_impact_analysis_fields
📊 Adding new impact analysis columns...
🔧 Making deprecated columns nullable...
🔄 Migrating existing data...
📈 Found 1164 records to migrate
  → Transforming direction to sentiment_direction...
  → Transforming confidence to sentiment_score...
  → Setting impact_level based on confidence...
  → Setting default relevance_score...
  → Setting default urgency_level...
  → Setting default impact_analysis...
✅ Verifying migration...
  Total records: 1164
  Has sentiment_direction: 1164
  Has sentiment_score: 1164
  Has impact_level: 1164
  Has relevance_score: 1164
  Has urgency_level: 1164
  Has impact_analysis: 1164
✅ All records migrated successfully!
✅ Migration completed successfully
```

#### Step 3: Verify Migration

```bash
# Run Python verification script
python scripts/verify_prediction_data.py

# Expected output: All 10 verification checks should pass
# Check anomaly report: scripts/anomaly_report.md
```

**Success Criteria**:
- All 1164 records have new fields populated
- All sentiment_score values between -1.0 and 1.0
- All impact_level values in (low, medium, high, critical)
- All urgency_level values in (routine, notable, urgent, breaking)
- All relevance_score values between 0.0 and 1.0
- Data consistency check passes
- 10/10 verification checks pass

#### Step 4: Manual SQL Verification (Optional)

```bash
# Run manual verification queries
psql -h <host> -U <user> -d craveny -f scripts/verify_migration.sql

# Review output for:
# - Correct record counts
# - Proper field mapping
# - Valid value distributions
```

#### Step 5: Production Migration (After Staging Success)

1. **Final Backup**:
   ```bash
   pg_dump -h <prod_host> -U <prod_user> -d craveny > backup_prod_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Run Migration**:
   ```bash
   # Switch to production environment
   export DATABASE_URL=<production_database_url>

   # Run migration
   python backend/db/migrations/add_impact_analysis_fields.py
   ```

3. **Verify Production**:
   ```bash
   python scripts/verify_prediction_data.py
   ```

### Rollback Procedure (If Needed)

If migration fails or issues are detected:

**Option 1: Using Python Script**:
```bash
python backend/db/migrations/add_impact_analysis_fields.py downgrade
```

**Option 2: Using SQL Script**:
```bash
psql -h <host> -U <user> -d craveny -f scripts/rollback_migration.sql
```

**Option 3: Restore from Backup**:
```bash
# Drop current database (CAREFUL!)
dropdb -h <host> -U <user> craveny

# Create new database
createdb -h <host> -U <user> craveny

# Restore from backup
psql -h <host> -U <user> -d craveny < backup_YYYYMMDD_HHMMSS.sql
```

---

## Post-Migration Checklist

After successful migration:

- [ ] Verify 1164/1164 records migrated successfully
- [ ] All verification checks pass (10/10)
- [ ] Anomaly report reviewed (< 1% anomalies acceptable)
- [ ] Staging migration successful
- [ ] Production migration successful
- [ ] Backup files saved and verified
- [ ] Application still functions correctly
- [ ] No errors in application logs

---

## Troubleshooting

### Issue: Migration Script Fails

**Symptoms**: Error during migration execution

**Solutions**:
1. Check database connection
2. Verify database user has ALTER TABLE permissions
3. Check for schema conflicts
4. Review error logs
5. Run rollback and retry

### Issue: Verification Fails

**Symptoms**: Some verification checks fail

**Solutions**:
1. Review anomaly report for details
2. Check specific failing records
3. Determine if anomalies are acceptable
4. If not acceptable, rollback and investigate

### Issue: Performance Degradation

**Symptoms**: Migration takes too long (> 5 minutes)

**Solutions**:
1. Check database load
2. Verify indexes are working
3. Consider running during off-peak hours
4. Run in smaller batches if needed

---

## Next Steps

After Epic 1 completion:

1. **Epic 2: Predictor Refactoring**
   - Update Predictor prompts to focus on impact analysis
   - Modify response parsing logic
   - Implement new field storage

2. **Epic 3: Investment Report Enhancement**
   - Aggregate news impact scores
   - Add price prediction logic
   - Generate comprehensive reports

3. **Epic 4: API Updates**
   - Update API response structures
   - Add new endpoints
   - Update API documentation

---

## Files Reference

### Modified Files
- `backend/db/models/prediction.py` - Model schema

### Created Files
- `backend/db/migrations/add_impact_analysis_fields.py` - Migration script
- `scripts/verify_migration.sql` - SQL verification queries
- `scripts/rollback_migration.sql` - Rollback script
- `scripts/verify_prediction_data.py` - Python verification script
- `docs/prd/epics/EPIC1_EXECUTION_GUIDE.md` - This guide

### Generated Files (After Migration)
- `scripts/anomaly_report.md` - Anomaly detection report
- `backup_*.sql` - Database backup files

---

## Contact

If you encounter issues during migration:
1. Check this guide for troubleshooting steps
2. Review error logs carefully
3. DO NOT proceed if staging migration fails
4. Keep all backup files until migration is verified successful

---

**Last Updated**: 2025-01-06
**Version**: 1.0
**Status**: Ready for Story 1.3 Execution
