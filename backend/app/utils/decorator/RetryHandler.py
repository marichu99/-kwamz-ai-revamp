import time
import functools
import logging
from typing import Callable, Any, Optional, Tuple, Type

class RetryHandler:
    """Utility class for handling retries with various strategies"""
    
    @staticmethod
    def retry(max_attempts: int = 3, 
              delay: float = 2, 
              exceptions: Tuple[Type[Exception], ...] = (Exception,),
              backoff_factor: float = 1,
              logger: Optional[logging.Logger] = None):
        """
        Retry decorator with configurable options
        
        Args:
            max_attempts: Maximum number of attempts
            delay: Initial delay between attempts in seconds
            exceptions: Tuple of exceptions to catch and retry on
            backoff_factor: Multiplier for delay after each failed attempt
            logger: Logger instance for logging retry attempts
        """
        if logger is None:
            logger = logging.getLogger(__name__)
            
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        result = func(*args, **kwargs)
                        if attempt > 0:  # Log success after retry
                            logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                        return result
                        
                    except exceptions as e:
                        last_exception = e
                        logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}")
                    
                    # Don't sleep after the last attempt
                    if attempt < max_attempts - 1:
                        logger.info(f"Retrying {func.__name__} in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor  # Exponential backoff
                
                # If all attempts failed, raise the last exception
                logger.error(f"{func.__name__} failed after {max_attempts} attempts")
                if last_exception:
                    raise last_exception
                
                return None
            
            return wrapper
        return decorator
    
    @staticmethod
    def retry_with_condition(max_attempts: int = 3,
                           delay: float = 2,
                           success_condition: Optional[Callable[[Any], bool]] = None,
                           logger: Optional[logging.Logger] = None):
        """
        Retry decorator that checks a success condition
        
        Args:
            max_attempts: Maximum number of attempts
            delay: Delay between attempts in seconds
            success_condition: Function to check if result is successful
            logger: Logger instance
        """
        if logger is None:
            logger = logging.getLogger(__name__)
            
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                for attempt in range(max_attempts):
                    try:
                        result = func(*args, **kwargs)
                        
                        # Check success condition
                        if success_condition is None or success_condition(result):
                            if attempt > 0:
                                logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                            return result
                        else:
                            logger.warning(f"{func.__name__} attempt {attempt + 1} failed condition check")
                            
                    except Exception as e:
                        logger.error(f"{func.__name__} attempt {attempt + 1} raised exception: {e}")
                    
                    # Don't sleep after the last attempt
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                
                logger.error(f"{func.__name__} failed after {max_attempts} attempts")
                raise RuntimeError(f"Function {func.__name__} failed after {max_attempts} attempts")
            
            return wrapper
        return decorator