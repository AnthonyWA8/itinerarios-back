import hashlib
from passlib.context import CryptContext


class PasswordHasher:
    def __init__(self):
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _prehash(self, password: str) -> str:
        # convierte cualquier tamaño de password en un hash fijo
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def hash(self, password: str) -> str:
        return self._ctx.hash(self._prehash(password))

    def verify(self, password: str, password_hash: str) -> bool:
        return self._ctx.verify(self._prehash(password), password_hash)
