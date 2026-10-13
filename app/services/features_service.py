import json
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

log = get_logger("features")


async def fetch_features_in_bbox(
    session: AsyncSession,
    layer_id: uuid.UUID,
    bbox: tuple[float, float, float, float],
    limit: int,
    simplify: float = 0.0,
) -> list[dict]:
    """Consulta espacial usando índice GiST. Retorna lista de Features GeoJSON."""
    w, s, e, n = bbox

    if simplify and simplify > 0:
        geom_expr = "ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, :tol), 6)"
        params = {"layer_id": str(layer_id), "w": w, "s": s, "e": e, "n": n, "lim": limit, "tol": simplify}
    else:
        geom_expr = "ST_AsGeoJSON(geom, 6)"
        params = {"layer_id": str(layer_id), "w": w, "s": s, "e": e, "n": n, "lim": limit}

    sql = text(f"""
        SELECT id, properties, {geom_expr} AS geometry
        FROM features
        WHERE layer_id = :layer_id
          AND geom && ST_MakeEnvelope(:w, :s, :e, :n, 4326)
        LIMIT :lim
    """)

    rows = (await session.execute(sql, params)).all()
    return [
        {
            "type": "Feature",
            "id": r.id,
            "properties": r.properties,
            "geometry": json.loads(r.geometry),
        }
        for r in rows
    ]


async def stream_all_features(session: AsyncSession, layer_id: uuid.UUID):
    """Gera GeoJSON completo em streaming (usado para download)."""
    sql = text("""
        SELECT id, properties, ST_AsGeoJSON(geom, 6) AS geometry
        FROM features WHERE layer_id = :layer_id
    """)
    async for r in await session.stream(sql, {"layer_id": str(layer_id)}):
        yield {
            "type": "Feature",
            "id": r.id,
            "properties": r.properties,
            "geometry": json.loads(r.geometry),
        }