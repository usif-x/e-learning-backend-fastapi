from functools import wraps

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class DBException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def db_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError:
            # غالباً duplicate entry
            raise DBException("Duplicate entry: already exists", 409)
        except SQLAlchemyError as e:
            raise DBException("Database error occurred", 500)

    return wrapper
