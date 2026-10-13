import json
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.deps import SessionDep
from app.redis_client import get_redis
from app.services import features_service, layers_service
from app.utils.bbox import parse_bbox

router = APIRouter(prefix="/api/v1/layers", tags=["features"])


@router.get("/{layer_id}/features")
async def get_features(
    layer_id: uuid.UUID,
    session: SessionDep,
    bbox: str = Query(..., description="oeste,sul,leste,norte (EPSG:4326)"),
    limit: int | None = None,
    simplify: float = 0.0,
):
    layer = await layers_service.get_layer(session, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camada não encontrada")

    try:
        parsed = parse_bbox(bbox)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    effective_limit = min(limit or settings.DEFAULT_FEATURES_LIMIT, settings.MAX_FEATURES_LIMIT)

    # Cache por (layer, bbox arredondada, limit, simplify)
    cache_key = f"feat:{layer_id}:{bbox}:{effective_limit}:{simplify}"
    r = get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    feats = await features_service.fetch_features_in_bbox(
        session, layer_id, parsed, effective_limit, simplify
    )
    payload = {"type": "FeatureCollection", "features": feats}

    await r.setex(cache_key, settings.CACHE_TTL_SECONDS, json.dumps(payload))
    return payload


@router.get("/{layer_id}/features.geojson")
async def download_features(layer_id: uuid.UUID, session: SessionDep):
    layer = await layers_service.get_layer(session, layer_id)
    if not layer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camada não encontrada")

    async def gen():
        yield '{"type":"FeatureCollection","features":['
        first = True
        async for feat in features_service.stream_all_features(session, layer_id):
            if not first:
                yield ","
            first = False
            yield json.dumps(feat)
        yield "]}"

    return StreamingResponse(
        gen(),
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="layer_{layer_id}.geojson"'},
    )