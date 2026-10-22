from supabase_auth.errors import AuthApiError

from app.clients.auth_client import auth_client
from app.exceptions import (
    ConflictError,
    UnauthorizedError,
    ValidationError,
)
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
)


class AuthService:
    
    @staticmethod
    def register(data: RegisterRequest) -> AuthResponse:
        try:
            response = auth_client.auth.sign_up(
                {
                    "email": str(data.email),
                    "password": data.password,
                }
            )
        except AuthApiError as exc:
            message = getattr(exc, "message", "")
            normalized_message = message.lower()

            if (
                "already registered" in normalized_message
                or getattr(exc, "code", None) == "user_already_exists"
            ):
                raise ConflictError(
                    "An account with this email already exists."
                ) from exc

            raise ValidationError(
                "Registration failed. Check the submitted details."
            ) from exc

        user = response.user

        if user is None:
            raise ValidationError("Registration could not be completed.")

        session = response.session

        return AuthResponse(
            access_token=session.access_token if session else None,
            expires_in=session.expires_in if session else None,
            user_id=str(user.id),
            email=user.email,
            requires_email_confirmation=session is None,
        )


    @staticmethod
    def login(data: LoginRequest) -> AuthResponse:
        try:
            response = auth_client.auth.sign_in_with_password(
                {
                    "email": str(data.email),
                    "password": data.password,
                }
            )
        except AuthApiError as exc:
            raise UnauthorizedError(
                "Invalid email or password, or email confirmation is required."
            ) from exc

        user = response.user
        session = response.session

        if user is None or session is None:
            raise UnauthorizedError("Authentication failed.")

        return AuthResponse(
            access_token=session.access_token,
            expires_in=session.expires_in,
            user_id=str(user.id),
            email=user.email,
        )
