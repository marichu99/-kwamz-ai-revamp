from enum import Enum
class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALID = "INVALID"
    REVERSED = "REVERSED"
