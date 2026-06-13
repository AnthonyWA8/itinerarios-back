from passlib.context import CryptContext


class PasswordHasher:
    def __init__(self):
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def _truncate(password: str) -> str:
        # bcrypt no soporta mas de 72 bytes; truncamos de forma segura por bytes UTF-8.
        return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

    def hash(self, password: str) -> str:
        return self._ctx.hash(self._truncate(password))

    def verify(self, password: str, password_hash: str) -> bool:
        return self._ctx.verify(self._truncate(password), password_hash)
    
    