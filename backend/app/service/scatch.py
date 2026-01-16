# test_query.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import psycopg2
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_query_directly():
    """Test the SQL query directly against the database."""
    load_dotenv()
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return
    
    logger.info(f"Connecting to database...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test parameters
        shortcode = '2811249'  # From your logs
        days = 30
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                id, receipt_no, completion_time, initiation_time,
                details, transaction_status, paid_in, withdrawn,
                balance, balance_confirmed, reason_type, other_party_info,
                linked_transaction_id, account_number, currency,
                transaction_type, business_shortcode, company_id, agent_id,
                created_at, updated_at
            FROM transactions
            WHERE business_shortcode = %s
            AND transaction_status = 'Completed'
            AND completion_time >= %s
            ORDER BY completion_time DESC
            LIMIT 10  -- Just get a few for testing
        """
        
        logger.info(f"\n=== Testing Query ===")
        logger.info(f"Query: {query}")
        logger.info(f"Parameters: shortcode='{shortcode}', cutoff_date='{cutoff_date}'")
        
        cursor.execute(query, (shortcode, cutoff_date))
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        logger.info(f"Columns: {columns}")
        
        results = cursor.fetchall()
        logger.info(f"\nGot {len(results)} results")
        
        for i, row in enumerate(results):
            logger.info(f"\n--- Row {i} ---")
            for j, col in enumerate(columns):
                value = row[j]
                logger.info(f"  {col}: {repr(value)} (type: {type(value).__name__})")
                
                # Special check for completion_time
                if col == 'completion_time':
                    if isinstance(value, str):
                        logger.info(f"    WARNING: completion_time is a string!")
                        if value.lower() == 'completion_time':
                            logger.info(f"    ERROR: Got column name as value!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)

def check_for_corrupted_data():
    """Check if there's really corrupted data in the database."""
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        return
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check for literal 'completion_time' strings
        query = """
            SELECT COUNT(*)
            FROM transactions
            WHERE completion_time::text = 'completion_time'
        """
        
        cursor.execute(query)
        count = cursor.fetchone()[0]
        logger.info(f"\n=== Checking for corrupted data ===")
        logger.info(f"Rows where completion_time = 'completion_time': {count}")
        
        if count > 0:
            # Get some samples
            query = """
                SELECT id, receipt_no, completion_time::text, created_at
                FROM transactions
                WHERE completion_time::text = 'completion_time'
                LIMIT 5
            """
            cursor.execute(query)
            samples = cursor.fetchall()
            logger.info("Sample corrupted rows:")
            for row in samples:
                logger.info(f"  ID: {row[0]}, Receipt: {row[1]}, completion_time: {row[2]}, created_at: {row[3]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error checking corrupted data: {e}")

if __name__ == '__main__':
    print("Testing database query...")
    test_query_directly()
    print("\n" + "="*50 + "\n")
    check_for_corrupted_data()