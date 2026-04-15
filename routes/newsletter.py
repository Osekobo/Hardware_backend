from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from database import get_db
from models import NewsletterSubscriber
from auth.dependencies import get_current_user

router = APIRouter()

class NewsletterSubscribe(BaseModel):
    email: EmailStr

class NewsletterUnsubscribe(BaseModel):
    email: EmailStr

@router.post("/subscribe")
def subscribe_to_newsletter(
    data: NewsletterSubscribe,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.email == data.email
    ).first()
    
    if existing:
        if existing.is_active == 0:
            # Reactivate subscription
            existing.is_active = 1
            existing.subscribed_at = datetime.utcnow()
            db.commit()
            return {"message": "Successfully resubscribed to newsletter!"}
        else:
            return {"message": "Email already subscribed to newsletter"}
    
    # Create new subscriber
    subscriber = NewsletterSubscriber(
        email=data.email,
        subscribed_at=datetime.utcnow(),
        is_active=1
    )
    
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)
    
    return {"message": "Successfully subscribed to newsletter!"}

@router.post("/unsubscribe")
def unsubscribe_from_newsletter(
    data: NewsletterUnsubscribe,
    db: Session = Depends(get_db)
):
    subscriber = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.email == data.email
    ).first()
    
    if not subscriber:
        raise HTTPException(404, "Email not found in subscribers")
    
    subscriber.is_active = 0
    db.commit()
    
    return {"message": "Successfully unsubscribed from newsletter"}

@router.get("/subscribers")
def get_subscribers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Only admin can view subscribers
    # You can add admin check here
    subscribers = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.is_active == 1
    ).all()
    return subscribers

@router.get("/count")
def get_subscriber_count(db: Session = Depends(get_db)):
    count = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.is_active == 1
    ).count()
    return {"count": count}