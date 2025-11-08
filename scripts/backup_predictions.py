"""
Backup script for predictions table before migration.
"""
import json
from datetime import datetime
from sqlalchemy import text
from backend.db.session import engine

def backup_predictions():
    """Create a JSON backup of predictions table."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'/tmp/predictions_backup_{timestamp}.json'

    with engine.connect() as conn:
        # Get all data from predictions table (only old fields)
        result = conn.execute(text('''
            SELECT id, news_id, model_id, stock_code, direction, confidence,
                   short_term, medium_term, long_term, confidence_breakdown,
                   reasoning, current_price, target_period, pattern_analysis, created_at
            FROM predictions
            ORDER BY id
        '''))

        rows = result.fetchall()
        columns = result.keys()

        # Convert to list of dictionaries
        backup_data = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Convert datetime to string
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                row_dict[col] = val
            backup_data.append(row_dict)

        # Write to JSON file
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        print(f'✅ Backup created: {backup_file}')
        print(f'📊 Total records backed up: {len(backup_data)}')
        print(f'')
        print(f'To restore from this backup:')
        print(f'  psql -h localhost -U postgres -d craveny -c "TRUNCATE TABLE predictions CASCADE;"')
        print(f'  python scripts/restore_predictions.py {backup_file}')

        return backup_file, len(backup_data)

if __name__ == "__main__":
    backup_predictions()
