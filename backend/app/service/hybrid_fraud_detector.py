# app/services/hybrid_fraud_detection.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from app.service.fraud_detector import FraudDetectionService
from app.service.transaction_service import TransactionService

logger = logging.getLogger(__name__)

# Create thread pool executor
executor = ThreadPoolExecutor(max_workers=5)

class HybridFraudDetection:
    """Hybrid approach for fraud detection."""
    
    @staticmethod
    async def run_for_user_async(user):
        """Run fraud detection asynchronously."""
        logger.info(f"Starting hybrid fraud detection for {user.email}")
        
        # Initialize services
        fraud_service = FraudDetectionService(user=user)
        transaction_service = TransactionService()
        
        loop = asyncio.get_event_loop()
        
        # Get all shortcodes
        logger.info("Fetching shortcodes...")
        shortcodes = await loop.run_in_executor(
            executor, 
            transaction_service.get_all_shortcodes_in_txn_tbl
        )
        
        logger.info(f"Found {len(shortcodes)} shortcodes")
        
        # Historical Analysis
        logger.info("Running historical analysis...")
        historical_result = await HybridFraudDetection._run_historical_analysis(
            loop, fraud_service, transaction_service, shortcodes
        )
        
        # Recent Transactions Check
        logger.info("Checking recent transactions...")
        recent_detections = await HybridFraudDetection._check_recent_transactions(
            loop, fraud_service, transaction_service, shortcodes
        )
        
        logger.info(f"Completed fraud detection for {user.email}")
        
        return {
            'historical_report': historical_result,
            'recent_detections': recent_detections,
            'total_shortcodes': len(shortcodes)
        }
    
    @staticmethod
    async def _run_historical_analysis(loop, fraud_service, transaction_service, shortcodes):
        """Run historical fraud analysis."""
        all_transactions = []
        
        # Fetch transactions for all shortcodes concurrently
        fetch_tasks = []
        for shortcode in shortcodes:
            task = loop.run_in_executor(
                executor,
                lambda s=shortcode: transaction_service.get_historical_transactions_for_shortcode(
                    s, 
                    days=fraud_service.config['analysis_period_days']
                )
            )
            fetch_tasks.append(task)
        
        # Wait for all fetches to complete
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching transactions for {shortcodes[idx]}: {result}")
            else:
                all_transactions.extend(result)
        
        if all_transactions:
            # Run detection
            historical_result = await loop.run_in_executor(
                executor,
                fraud_service.run_detection,
                all_transactions
            )
            
            # Send report
            await loop.run_in_executor(
                executor,
                fraud_service.send_historical_report,
                historical_result['summary']
            )
            
            return historical_result
        
        return {'summary': {}, 'detections': []}
    
    @staticmethod
    async def _check_recent_transactions(loop, fraud_service, transaction_service, shortcodes):
        """Check recent transactions for fraud."""
        all_detections = []
        
        # Process shortcodes in batches
        batch_size = 3  # Process 3 shortcodes at a time
        for i in range(0, len(shortcodes), batch_size):
            batch = shortcodes[i:i + batch_size]
            
            # Create tasks for this batch
            batch_tasks = []
            for shortcode in batch:
                task = loop.run_in_executor(
                    executor,
                    lambda s=shortcode: HybridFraudDetection._process_single_shortcode(
                        fraud_service, transaction_service, s
                    )
                )
                batch_tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing shortcode: {result}")
                elif result:
                    all_detections.extend(result)
        
        return all_detections
    
    @staticmethod
    def _process_single_shortcode(fraud_service, transaction_service, shortcode):
        """Process a single shortcode (runs in thread pool)."""
        # Get recent transactions
        transactions = transaction_service.get_recent_transactions_for_shortcode(
            shortcode,
            limit=fraud_service.config['recent_transactions_limit']
        )
        
        if not transactions:
            return []
        
        # Run detection
        result = fraud_service.run_detection(transactions)
        
        # Send notifications for high-risk detections
        for detection in result.get('detections', []):
            if detection.get('risk_level') == 'HIGH':
                fraud_service.send_fraud_notification(
                    detection, 
                    detection.get('fraud_type')
                )
        
        return result.get('detections', [])