from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db_session
from app.infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.infrastructure.database.repositories.sqlalchemy_itinerary_repository import SQLAlchemyItineraryRepository
from app.infrastructure.database.repositories.sqlalchemy_feedback_repository import SQLAlchemyFeedbackRepository
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.jwt_handler import JWTHandler
from app.infrastructure.llm.groq_client import GroqLLMService
from app.infrastructure.rag.lightweight_retriever import LightweightRAGService

from app.application.use_cases.auth.register_user import RegisterUserUseCase
from app.application.use_cases.auth.login_user import LoginUserUseCase
from app.application.use_cases.itinerary.generate_itinerary import GenerateItineraryUseCase
from app.application.use_cases.itinerary.regenerate_itinerary import RegenerateItineraryUseCase
from app.application.use_cases.itinerary.refine_itinerary import RefineItineraryUseCase
from app.application.use_cases.itinerary.save_itinerary import SaveItineraryUseCase
from app.application.use_cases.itinerary.get_user_itineraries import (
    GetUserItinerariesUseCase,
    DeleteItineraryUseCase,
)
from app.application.use_cases.itinerary.validate_itinerary import ItineraryValidator
from app.application.use_cases.itinerary.reward_model import ItineraryRewardModel
from app.application.use_cases.feedback.submit_feedback import SubmitFeedbackUseCase

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Singletons (sin estado por request)
_password_hasher = PasswordHasher()
_jwt_handler = JWTHandler()
_itinerary_validator = ItineraryValidator()
_reward_model = ItineraryRewardModel()
_llm_service = GroqLLMService()


def get_jwt_handler() -> JWTHandler:
    return _jwt_handler


# ---------- Repositories ----------

def get_user_repository(session: DbSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


def get_itinerary_repository(session: DbSession) -> SQLAlchemyItineraryRepository:
    return SQLAlchemyItineraryRepository(session)


def get_feedback_repository(session: DbSession) -> SQLAlchemyFeedbackRepository:
    return SQLAlchemyFeedbackRepository(session)


def get_rag_service() -> LightweightRAGService:
    return LightweightRAGService()


# ---------- Use cases: Auth ----------

def get_register_use_case(
    user_repo: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repo, _password_hasher, _jwt_handler)


def get_login_use_case(
    user_repo: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> LoginUserUseCase:
    return LoginUserUseCase(user_repo, _password_hasher, _jwt_handler)


# ---------- Use cases: Itinerary ----------

def get_generate_itinerary_use_case(
    rag: Annotated[LightweightRAGService, Depends(get_rag_service)],
    feedback_repo: Annotated[SQLAlchemyFeedbackRepository, Depends(get_feedback_repository)],
) -> GenerateItineraryUseCase:
    return GenerateItineraryUseCase(_llm_service, rag, _itinerary_validator, _reward_model, feedback_repo)


def get_regenerate_itinerary_use_case(
    generate_uc: Annotated[GenerateItineraryUseCase, Depends(get_generate_itinerary_use_case)],
) -> RegenerateItineraryUseCase:
    return RegenerateItineraryUseCase(generate_uc)


def get_refine_itinerary_use_case(
    itinerary_repo: Annotated[SQLAlchemyItineraryRepository, Depends(get_itinerary_repository)],
) -> RefineItineraryUseCase:
    return RefineItineraryUseCase(_llm_service, itinerary_repo, _itinerary_validator)


def get_save_itinerary_use_case(
    itinerary_repo: Annotated[SQLAlchemyItineraryRepository, Depends(get_itinerary_repository)],
) -> SaveItineraryUseCase:
    return SaveItineraryUseCase(itinerary_repo)


def get_user_itineraries_use_case(
    itinerary_repo: Annotated[SQLAlchemyItineraryRepository, Depends(get_itinerary_repository)],
) -> GetUserItinerariesUseCase:
    return GetUserItinerariesUseCase(itinerary_repo)


def get_delete_itinerary_use_case(
    itinerary_repo: Annotated[SQLAlchemyItineraryRepository, Depends(get_itinerary_repository)],
) -> DeleteItineraryUseCase:
    return DeleteItineraryUseCase(itinerary_repo)


# ---------- Use cases: Feedback ----------

def get_submit_feedback_use_case(
    feedback_repo: Annotated[SQLAlchemyFeedbackRepository, Depends(get_feedback_repository)],
) -> SubmitFeedbackUseCase:
    return SubmitFeedbackUseCase(feedback_repo)


# ---------- Auth guard ----------

async def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> UUID:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user_id = jwt_handler.decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    return UUID(user_id)


async def get_optional_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> UUID | None:
    if token is None:
        return None
    user_id = jwt_handler.decode_token(token)
    return UUID(user_id) if user_id else None
