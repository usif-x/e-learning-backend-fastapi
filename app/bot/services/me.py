from sqlalchemy.orm import Session

from app.core.database import SessionLocal  # Import SessionLocal to create a session
from app.core.dependencies import get_user_by_tg_id


# This is the synchronous function the bot will call.
# It manages its own database session.
def get_me_sync(chat_id: int):
    db: Session = SessionLocal()
    try:
        # Call the synchronous dependency function with the created session
        user = get_user_by_tg_id(chat_id, db)
        return user
    finally:
        db.close()
