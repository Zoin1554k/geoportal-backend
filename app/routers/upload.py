import json
import uuid
import zipfile
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.deps import CurrentUser, SessionDep
from app.models import Layer
from app.schemas import LayerOut
from app.services import ingest_service
from app.redis_client import get_redis

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


@router.post("/geojson", response_model=LayerOut, status_code=201)
async def upload_geojson(
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    is_public: bool = Form(False),
):
    if not file.filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo deve ser .geojson ou .json")

    raw = await file.read()
    try:
        geojson = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "JSON inválido")

    layer = Layer(
        name=name,
        description=description,
        type="geojson",
        owner_id=user.id,
        is_public=is_public,
    )
    session.add(layer)
    await session.commit()
    await session.refresh(layer)

    try:
        count = await ingest_service.ingest_geojson(session, layer, geojson)
    except ValueError as e:
        await session.delete(layer)
        await session.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    # Invalida cache
    await get_redis().delete(f"feat:{layer.id}:*")

    await session.refresh(layer)
    return layer


@router.post("/shapefile", response_model=LayerOut, status_code=201)
async def upload_shapefile(
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile = File(..., description="ZIP contendo .shp/.shx/.dbf/.prj"),
    name: str = Form(...),
    description: str | None = Form(None),
    is_public: bool = Form(False),
):
    """
    Converte Shapefile (ZIP) para GeoJSON e ingere.
    Requer `fiona` + `geopandas` (instale se necessário) OU fazemos parse manual via pyshp.
    Aqui usamos geopandas — adicione ao requirements se for usar.
    """
    try:
        import geopandas as gpd  # noqa
    except ImportError:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Ingestão de Shapefile requer geopandas. Instale: pip install geopandas",
        )

    raw = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(raw)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie um ZIP válido")

    tmpdir = f"/tmp/shp_{uuid.uuid4().hex}"
    import os
    os.makedirs(tmpdir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        z.extractall(tmpdir)

    try:
        gdf = gpd.read_file(tmpdir)
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
        geojson = json.loads(gdf.to_json())
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Falha ao ler Shapefile: {e}")
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    layer = Layer(name=name, description=description, type="geojson", owner_id=user.id, is_public=is_public)
    session.add(layer)
    await session.commit()
    await session.refresh(layer)

    await ingest_service.ingest_geojson(session, layer, geojson)
    await session.refresh(layer)
    return layer