from fastapi import APIRouter
from app.api.v1.endpoints import rides, payments, users, locations, admin, wallet, kyc
from app.routes import auth

api_router = APIRouter()

# Include all API endpoints
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(locations.router, prefix="/locations", tags=["Locations"])
api_router.include_router(rides.router, prefix="/rides", tags=["Rides"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(kyc.router, prefix="/kyc", tags=["KYC"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])