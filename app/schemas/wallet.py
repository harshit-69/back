from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class WalletResponse(BaseModel):
    id: int
    user_id: int
    balance: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    wallet_id: int
    ride_id: Optional[int] = None
    amount: float
    type: TransactionType
    status: TransactionStatus
    payment_method: Optional[str] = None
    payment_id: Optional[str] = None
    description: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AddMoneyRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to add to wallet")
    payment_method: str = Field(..., description="Payment method (card, bank_transfer, etc.)")
    description: Optional[str] = "Wallet recharge"

class TransactionList(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    size: int

class WalletBalanceResponse(BaseModel):
    balance: float
    currency: str = "INR" 