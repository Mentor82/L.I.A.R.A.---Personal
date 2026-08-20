#!/usr/bin/env python3
"""
🗑️ Privacy Data Cleanup Script
Auto-delete old location and search data based on user privacy settings

Usage:
    python cleanup_privacy_data.py [--dry-run]

Cron Job (täglich um 3 Uhr):
    0 3 * * * /opt/liara/venv/bin/python /opt/liara/app/scripts/cleanup_privacy_data.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import logging

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://liara:liaras_own@localhost/liara_db')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_old_data(dry_run=False):
    """
    Delete old location and search data based on user privacy settings
    
    Args:
        dry_run: If True, only log what would be deleted without actually deleting
    """
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        logger.info("Starting privacy data cleanup...")
        
        # ==============================================================
        # 1. Cleanup old location data
        # ==============================================================
        
        # Get users with auto-delete settings for location
        location_cleanup_sql = text("""
        SELECT 
            ups.user_id,
            ups.auto_delete_location_after_days,
            ulp.detected_at
        FROM user_privacy_settings ups
        JOIN user_location_preferences ulp ON ups.user_id = ulp.user_id
        WHERE 
            ups.auto_delete_location_after_days > 0
            AND ulp.detected_at < CURRENT_TIMESTAMP - (ups.auto_delete_location_after_days || ' days')::INTERVAL
        """)
        
        location_records = db.execute(location_cleanup_sql).fetchall()
        
        if location_records:
            logger.info(f"Found {len(location_records)} location records to delete")
            
            for record in location_records:
                user_id = record.user_id
                days = record.auto_delete_location_after_days
                detected_at = record.detected_at
                
                logger.info(f"User {user_id}: Location from {detected_at} (older than {days} days)")
                
                if not dry_run:
                    db.execute(
                        text("DELETE FROM user_location_preferences WHERE user_id = :user_id"),
                        {'user_id': user_id}
                    )
        else:
            logger.info("No old location data to delete")
        
        # ==============================================================
        # 2. Cleanup old search history
        # ==============================================================
        
        # Get users with auto-delete settings for searches
        search_cleanup_sql = text("""
        SELECT 
            ups.user_id,
            ups.auto_delete_searches_after_days,
            COUNT(ush.id) as search_count
        FROM user_privacy_settings ups
        JOIN user_search_history ush ON ups.user_id = ush.user_id
        WHERE 
            ups.auto_delete_searches_after_days > 0
            AND ush.searched_at < CURRENT_TIMESTAMP - (ups.auto_delete_searches_after_days || ' days')::INTERVAL
        GROUP BY ups.user_id, ups.auto_delete_searches_after_days
        """)
        
        search_records = db.execute(search_cleanup_sql).fetchall()
        
        if search_records:
            total_searches = sum(record.search_count for record in search_records)
            logger.info(f"Found {total_searches} search records from {len(search_records)} users to delete")
            
            for record in search_records:
                user_id = record.user_id
                days = record.auto_delete_searches_after_days
                count = record.search_count
                
                logger.info(f"User {user_id}: {count} searches older than {days} days")
                
                if not dry_run:
                    db.execute(text("""
                        DELETE FROM user_search_history 
                        WHERE user_id = :user_id 
                        AND searched_at < CURRENT_TIMESTAMP - (:days || ' days')::INTERVAL
                    """), {'user_id': user_id, 'days': days})
        else:
            logger.info("No old search history to delete")
        
        # ==============================================================
        # Commit changes
        # ==============================================================
        
        if not dry_run:
            db.commit()
            logger.info("✅ Privacy data cleanup completed successfully")
        else:
            logger.info("🔍 Dry-run completed (no data deleted)")
        
        # ==============================================================
        # Statistics
        # ==============================================================
        
        total_locations = db.execute(text("SELECT COUNT(*) FROM user_location_preferences")).scalar()
        total_searches = db.execute(text("SELECT COUNT(*) FROM user_search_history")).scalar()
        
        logger.info(f"📊 Current stats: {total_locations} locations, {total_searches} searches")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Privacy data cleanup script")
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    try:
        cleanup_old_data(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(1)
