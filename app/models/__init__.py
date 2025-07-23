from app.models.user import User
from app.models.ride import Ride, RideStatus
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.models.location import Location, DriverLocation
from app.models.payment import Payment, PaymentStatus, PaymentProvider, PaymentMethodEnum
from app.models.kyc import KYCDocument, KYCApplication, KYCStatus, DocumentType

# This file imports all models to make them available when importing from app.models
# It also ensures that all models are registered with SQLAlchemy
from app.models.payment import Payment, PaymentStatus, PaymentProvider, PaymentMethodEnum, UserPaymentMethod