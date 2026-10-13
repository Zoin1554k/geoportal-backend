import json
from shapely.geometry import shape
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Layer
from app.utils.logger import get_logger

log = get_logger("ingest")


async def ingest_geojson(session: AsyncSession, layer: Layer, geojson: dict) -> int:
    if geojson.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON deve ser um FeatureCollection")
    features = geojson.get("features", [])
    if not features:
        raise ValueError("FeatureCollection vazio")

    valid = []
    for f in features:
        geom = f.get("geometry")
        if not geom:
            continue
        try:
            shape(geom)
        except Exception:
            log.warning("Geometria invalida ignorada")
            continue
        valid.append(f)

    if not valid:
        raise ValueError("Nenhuma geometria valida")

    # IMPORTANTE: props vai como OBJETO (dict) dentro do payload,
    # nao como string. Assim o jsonb_to_recordset grava jsonb-object.
    payload = []
    for f in valid:
        props = f.get("properties") or {}
        if not isinstance(props, dict):
            props = {}
        payload.append({
            "props": props,
            "geom": json.dumps(f["geometry"]),
        })

    sql = text("""
        INSERT INTO features (layer_id, properties, geom)
        SELECT :layer_id, props, ST_SetSRID(ST_GeomFromGeoJSON(geom), 4326)
        FROM jsonb_to_recordset(CAST(:data AS jsonb)) AS t(props jsonb, geom text)
    """)

    await session.execute(sql, {
        "layer_id": str(layer.id),
        "data": json.dumps(payload),
    })

    await session.execute(
        text("""
            UPDATE layers
            SET feature_count = (SELECT COUNT(*) FROM features WHERE layer_id = :id),
                bbox = (SELECT ST_Envelope(ST_Collect(geom)) FROM features WHERE layer_id = :id),
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": str(layer.id)},
    )
    await session.commit()
    log.info("Ingestao concluida: %d feicoes", len(valid))
    return len(valid)