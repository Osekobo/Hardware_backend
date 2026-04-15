from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Address
from auth.dependencies import get_current_user

router = APIRouter()

class AddressCreate(BaseModel):
    full_name: str
    phone_number: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    county: str
    postal_code: Optional[str] = None
    landmark: Optional[str] = None
    is_default: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None

class AddressUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    landmark: Optional[str] = None
    is_default: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None

@router.post("/")
def create_address(
    address: AddressCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    # If this is default, remove default from other addresses
    if address.is_default:
        db.query(Address).filter(Address.user_id == user.id).update({"is_default": 0})
    
    new_address = Address(
        user_id=user.id,
        full_name=address.full_name,
        phone_number=address.phone_number,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        city=address.city,
        county=address.county,
        postal_code=address.postal_code,
        landmark=address.landmark,
        is_default=1 if address.is_default else 0,
        latitude=address.latitude,
        longitude=address.longitude,
        google_place_id=address.google_place_id
    )
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return new_address

@router.get("/")
def get_addresses(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    addresses = db.query(Address).filter(Address.user_id == user.id).all()
    return addresses

@router.get("/default")
def get_default_address(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    address = db.query(Address).filter(
        Address.user_id == user.id,
        Address.is_default == 1
    ).first()
    return address

@router.put("/{address_id}")
def update_address(
    address_id: int,
    address_update: AddressUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == user.id
    ).first()
    
    if not address:
        raise HTTPException(404, "Address not found")
    
    # If setting as default, remove default from others
    if address_update.is_default:
        db.query(Address).filter(Address.user_id == user.id).update({"is_default": 0})
        address.is_default = 1
    
    # Update fields
    if address_update.full_name is not None:
        address.full_name = address_update.full_name
    if address_update.phone_number is not None:
        address.phone_number = address_update.phone_number
    if address_update.address_line1 is not None:
        address.address_line1 = address_update.address_line1
    if address_update.address_line2 is not None:
        address.address_line2 = address_update.address_line2
    if address_update.city is not None:
        address.city = address_update.city
    if address_update.county is not None:
        address.county = address_update.county
    if address_update.postal_code is not None:
        address.postal_code = address_update.postal_code
    if address_update.landmark is not None:
        address.landmark = address_update.landmark
    if address_update.latitude is not None:
        address.latitude = address_update.latitude
    if address_update.longitude is not None:
        address.longitude = address_update.longitude
    if address_update.google_place_id is not None:
        address.google_place_id = address_update.google_place_id
    
    db.commit()
    db.refresh(address)
    return address

@router.delete("/{address_id}")
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == user.id
    ).first()
    
    if not address:
        raise HTTPException(404, "Address not found")
    
    db.delete(address)
    db.commit()
    return {"message": "Address deleted successfully"}