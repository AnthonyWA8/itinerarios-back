from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.jwt_handler import JWTHandler


class RegisterUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        jwt_handler: JWTHandler,
    ):
        self._users = user_repository
        self._hasher = password_hasher
        self._jwt = jwt_handler

    async def execute(self, name: str, email: str, password: str) -> tuple[User, str]:
        existing = await self._users.get_by_email(email.lower())
        if existing:
            raise ValueError("Ya existe una cuenta con ese correo.")

        user = User(
            id=uuid4(),
            name=name,
            email=email.lower(),
            password_hash=self._hasher.hash(password),
            created_at=datetime.now(timezone.utc),
        )
        created = await self._users.create(user)
        token = self._jwt.create_access_token(str(created.id))
        return created, token
