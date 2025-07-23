from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, func
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.utils.auth import get_current_user
from app.schemas.wallet import (
    WalletResponse, TransactionResponse, AddMoneyRequest,
    TransactionList, WalletBalanceResponse
)

router = APIRouter()

@router.get("/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's wallet balance."""
    # Get or create wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        # Create wallet if it doesn't exist
        wallet = Wallet(user_id=current_user.id, balance=0.0)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    
    return WalletBalanceResponse(balance=wallet.balance)

@router.post("/add-money", response_model=TransactionResponse)
async def add_money_to_wallet(
    request: AddMoneyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add money to user's wallet."""
    # Get or create wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0.0)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    
    # Create transaction record
    transaction = Transaction(
        wallet_id=wallet.id,
        amount=request.amount,
        type=TransactionType.CREDIT,
        status=TransactionStatus.PENDING,
        payment_method=request.payment_method,
        description=request.description or "Wallet recharge"
    )
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    # Update wallet balance
    wallet.balance += request.amount
    await db.commit()
    
    # Update transaction status to completed
    transaction.status = TransactionStatus.COMPLETED
    await db.commit()
    await db.refresh(transaction)
    
    return TransactionResponse.from_orm(transaction)

@router.get("/transactions", response_model=TransactionList)
async def get_wallet_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Get user's wallet transaction history."""
    # Get user's wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        return TransactionList(transactions=[], total=0, page=page, size=size)
    
    # Get total count
    total_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.wallet_id == wallet.id)
    )
    total = total_result.scalar()
    
    # Get transactions with pagination
    offset = (page - 1) * size
    result = await db.execute(
        select(Transaction)
        .where(Transaction.wallet_id == wallet.id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    transactions = result.scalars().all()
    
    return TransactionList(
        transactions=[TransactionResponse.from_orm(t) for t in transactions],
        total=total,
        page=page,
        size=size
    )

@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_details(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific transaction details."""
    # Get user's wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Get transaction
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id, Transaction.wallet_id == wallet.id)
    )
    transaction = result.scalars().first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return TransactionResponse.from_orm(transaction)

@router.post("/deduct", response_model=TransactionResponse)
async def deduct_from_wallet(
    amount: float,
    ride_id: Optional[int] = None,
    description: str = "Ride payment",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deduct money from user's wallet (for ride payments)."""
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )
    
    # Get user's wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    if wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient wallet balance"
        )
    
    # Create transaction record
    transaction = Transaction(
        wallet_id=wallet.id,
        ride_id=ride_id,
        amount=amount,
        type=TransactionType.DEBIT,
        status=TransactionStatus.COMPLETED,
        payment_method="wallet",
        description=description
    )
    
    db.add(transaction)
    
    # Update wallet balance
    wallet.balance -= amount
    
    await db.commit()
    await db.refresh(transaction)
    
    return TransactionResponse.from_orm(transaction) 