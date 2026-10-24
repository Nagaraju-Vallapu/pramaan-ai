from fastapi import APIRouter, HTTPException, status

from app.core.security import authenticate, issue_token
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    principal = authenticate(payload.username, payload.password)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(access_token=issue_token(principal), role=principal.role)
