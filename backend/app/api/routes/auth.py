from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    ADMIN_USERNAME,
    REVIEWER_USERNAME,
    Principal,
    authenticate,
    hash_password,
    issue_token,
    require_roles,
)
from app.models import ManagedUser, UserAuditEvent
from app.schemas import (
    LoginRequest,
    LoginResponse,
    ManagedUserCreate,
    ManagedUserResponse,
    UserAuditResponse,
    UserStatusUpdate,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    principal = authenticate(payload.username, payload.password, db)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(access_token=issue_token(principal), role=principal.role)


def _record_user_event(db: Session, actor: str, username: str, action: str) -> None:
    db.add(UserAuditEvent(actor=actor, username=username, action=action))


def _configured_users() -> list[ManagedUserResponse]:
    configured = (
        (ADMIN_USERNAME, "admin"),
        (REVIEWER_USERNAME, "reviewer"),
    )
    seen: set[str] = set()
    results = []
    for username, role in configured:
        normalized = username.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(
            ManagedUserResponse(
                id=f"env:{normalized}",
                username=username,
                role=role,
                active=True,
                source="environment",
            )
        )
    return results


@router.get("/users", response_model=list[ManagedUserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> list[ManagedUserResponse]:
    users = db.scalars(select(ManagedUser).order_by(ManagedUser.created_at.desc())).all()
    return _configured_users() + [
        ManagedUserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            active=user.active,
            source="managed",
            created_by=user.created_by,
            created_at=user.created_at,
        )
        for user in users
    ]


@router.post("/users", response_model=ManagedUserResponse, status_code=201)
def create_user(
    payload: ManagedUserCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin")),
) -> ManagedUserResponse:
    username = payload.username.strip()
    reserved_names = {ADMIN_USERNAME.casefold(), REVIEWER_USERNAME.casefold()}
    existing = db.scalar(
        select(ManagedUser.id).where(func.lower(ManagedUser.username) == username.casefold())
    )
    if username.casefold() in reserved_names or existing is not None:
        raise HTTPException(status_code=409, detail="That username is already in use.")

    user = ManagedUser(
        username=username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=True,
        created_by=principal.username,
    )
    db.add(user)
    _record_user_event(db, principal.username, username, "USER_CREATED")
    db.commit()
    db.refresh(user)
    return ManagedUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        active=user.active,
        source="managed",
        created_by=user.created_by,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}/status", response_model=ManagedUserResponse)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin")),
) -> ManagedUserResponse:
    user = db.get(ManagedUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Managed user not found.")
    if user.username == principal.username and not payload.active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account.")
    if user.active != payload.active:
        user.active = payload.active
        _record_user_event(
            db,
            principal.username,
            user.username,
            "USER_ACTIVATED" if payload.active else "USER_DEACTIVATED",
        )
        db.commit()
        db.refresh(user)
    return ManagedUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        active=user.active,
        source="managed",
        created_by=user.created_by,
        created_at=user.created_at,
    )


@router.get("/users/audit", response_model=list[UserAuditResponse])
def list_user_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> list[UserAuditResponse]:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="Limit must be between 1 and 500.")
    events = db.scalars(
        select(UserAuditEvent)
        .order_by(UserAuditEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        UserAuditResponse(
            id=event.id,
            actor=event.actor,
            username=event.username,
            action=event.action,
            created_at=event.created_at,
        )
        for event in events
    ]
