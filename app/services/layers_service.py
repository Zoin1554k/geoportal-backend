import uuid
from typing import Sequence

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Feature, Layer, User
from app.schemas import LayerCreate, LayerUpdate


async def list_layers(session: AsyncSession, user: User | None) -> Sequence[Layer]:
    stmt = select(Layer).order_by(Layer.created_at.desc())
    if user is None:
        stmt = stmt.where(Layer.is_public.is_(True))
    elif user.role != "admin":
        stmt = stmt.where(or_(Layer.is_public.is_(True), Layer.owner_id == user.id))
    return (await session.scalars(stmt)).all()


async def get_layer(session: AsyncSession, layer_id: uuid.UUID) -> Layer | None:
    return await session.get(Layer, layer_id)


async def create_layer(session: AsyncSession, data: LayerCreate, owner: User) -> Layer:
    layer = Layer(
        name=data.name,
        description=data.description,
        type=data.type,
        source_url=data.source_url,
        style=data.style,
        owner_id=owner.id,
        is_public=data.is_public,
    )
    session.add(layer)
    await session.commit()
    await session.refresh(layer)
    return layer


async def update_layer(session: AsyncSession, layer: Layer, data: LayerUpdate) -> Layer:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(layer, field, value)
    await session.commit()
    await session.refresh(layer)
    return layer


async def delete_layer(session: AsyncSession, layer: Layer) -> None:
    await session.delete(layer)
    await session.commit()


async def layer_stats(session: AsyncSession, layer: Layer) -> dict:
    count = await session.scalar(
        select(func.count()).select_from(Feature).where(Feature.layer_id == layer.id)
    )

    # Usa SQL puro para extrair as chaves distintas dos properties (jsonb)
    result = await session.execute(
        text("""
            SELECT DISTINCT jsonb_object_keys(properties) AS key
            FROM features
            WHERE layer_id = :lid
              AND jsonb_typeof(properties) = 'object'
            ORDER BY key
        """),
        {"lid": str(layer.id)},
    )
    columns = [row.key for row in result]

    return {"feature_count": count or 0, "columns": columns}