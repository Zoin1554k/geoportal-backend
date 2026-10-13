from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, SessionDep
from app.models import User
from app.schemas import RefreshIn, TokenPair, UserLogin, UserOut, UserRegister
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        accessToken=create_access_token(str(user.id)),
        refreshToken=create_refresh_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(data: UserRegister, session: SessionDep):
    exists = await session.scalar(select(User).where(User.email == data.email))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")

    # Primeiro usuário vira admin
    total = await session.scalar(select(User))
    role = "admin" if total is None else "viewer"

    user = User(email=data.email, password_hash=hash_password(data.password), role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return _tokens(user)


@router.post("/login", response_model=TokenPair)
async def login(data: UserLogin, session: SessionDep):
    user = await session.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshIn, session: SessionDep):
    try:
        payload = decode_token(data.refreshToken, expected_kind="refresh")
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    user = await session.scalar(select(User).where(User.id == payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user