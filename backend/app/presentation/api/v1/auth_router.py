from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.auth_dto import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.application.use_cases.auth.login_user import LoginUserUseCase
from app.application.use_cases.auth.register_user import RegisterUserUseCase
from app.presentation.api.dependencies import get_login_use_case, get_register_use_case

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(get_register_use_case)],
):
    try:
        user, token = await use_case.execute(payload.name, payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return AuthResponse(
        user=UserResponse(id=str(user.id), name=user.name, email=user.email),
        access_token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    use_case: Annotated[LoginUserUseCase, Depends(get_login_use_case)],
):
    try:
        user, token = await use_case.execute(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return AuthResponse(
        user=UserResponse(id=str(user.id), name=user.name, email=user.email),
        access_token=token,
    )
