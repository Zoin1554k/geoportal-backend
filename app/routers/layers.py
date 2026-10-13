import uuid

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, OptionalUser, SessionDep
from app.schemas import LayerCreate, LayerOut, LayerUpdate
from app.services import layers_service

router = APIRouter(prefix="/api/v1/layers", tags=["layers"])


def _check_can_write(user, layer):
    if user.role == "admin":
        return
    if layer.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta camada")


@router.get("", response_model=list[LayerOut])
async def list_layers(session: SessionDep, user: OptionalUser):
    return await layers_service.list_layers(session, user)


@router.post("", response_model=LayerOut, status_code=201)
async def create_layer(data: LayerCreate, session: SessionDep, user: CurrentUser):
    return await layers_service.create_layer(session, data, user)


@router.get("/{layer_id}", response_model=LayerOut)
async def get_layer(layer_id: uuid.UUID, session: SessionDep):
    layer = await layers_service.get_layer(session, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camada não encontrada")
    return layer


@router.patch("/{layer_id}", response_model=LayerOut)
async def update_layer(layer_id: uuid.UUID, data: LayerUpdate, session: SessionDep, user: CurrentUser):
    layer = await layers_service.get_layer(session, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camada não encontrada")
    _check_can_write(user, layer)
    return await layers_service.update_layer(session, layer, data)


@router.delete("/{layer_id}", status_code=204)
async def delete_layer(layer_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    layer = await layers_service.get_layer(session, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camada não encontrada")
    _check_can_write(user, layer)
    await layers_service.delete_layer(session, layer)


@router.get("/{layer_id}/stats")
async def layer_stats(layer_id: uuid.UUID, session: SessionDep):
    layer = await layers_service.get_layer(session, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camada não encontrada")
    return await layers_service.layer_stats(session, layer)