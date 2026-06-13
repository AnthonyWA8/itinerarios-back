from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.jwt_handler import JWTHandler


class LoginUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        jwt_handler: JWTHandler,
    ):
        self._users = user_repository
        self._hasher = password_hasher
        self._jwt = jwt_handler

    async def execute(self, email: str, password: str) -> tuple[User, str]:
        user = await self._users.get_by_email(email.lower())
        if not user or not self._hasher.verify(password, user.password_hash):
            raise ValueError("Correo o contraseña incorrectos.")

        token = self._jwt.create_access_token(str(user.id))
        return user, token
