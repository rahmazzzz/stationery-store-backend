
from fastapi import APIRouter, Depends, status

from app.container.dependencies import CurrentUser, Dependencies
from app.schemas.auth import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(data: RegisterRequest) -> AuthResponse:
    return AuthService.register(data)


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(data: LoginRequest) -> AuthResponse:
    return AuthService.login(data)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_me(
    current_user: CurrentUser = Depends(Dependencies.get_current_user),
) -> CurrentUserResponse:
    return CurrentUserResponse(**current_user)
