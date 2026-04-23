from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)
    image_url = Column(String)
    stock = Column(Integer, default=0)


class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)


# models.py
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)

    total = Column(Float)

    status = Column(String, default="pending")  # pending, paid, failed

    mpesa_receipt = Column(String, unique=True, nullable=True)
    checkout_request_id = Column(String, unique=True, nullable=True)

    paid_at = Column(DateTime, nullable=True)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    price = Column(Float)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    event = Column(String)
    data = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for unsubscribed


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String)
    phone_number = Column(String)
    address_line1 = Column(String)
    address_line2 = Column(String, nullable=True)
    city = Column(String)
    county = Column(String)
    postal_code = Column(String, nullable=True)
    landmark = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)  # Add this
    longitude = Column(Float, nullable=True)  # Add this
    google_place_id = Column(String, nullable=True)  # Add this
    is_default = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True)
    email = Column(String, index=True)
    otp = Column(String, index=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)