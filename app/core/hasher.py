import bcrypt


class PasswordHelper:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def check_password(password: str, hashed_password: str) -> bool:
        """Check if a password matches the hashed version."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
