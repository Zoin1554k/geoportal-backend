# GeoPortal Backend

Backend geoespacial em **FastAPI + PostGIS + Redis** para o GeoPortal.
Filtra feições por bounding box no servidor usando índice GiST (rápido mesmo com milhões de feições).

## Subir com Docker

```bash
cp .env.example .env
docker compose up --build
```

A API estará em `http://localhost:3000`. Docs automáticas em `/docs`.

O primeiro usuário registrado vira **admin** automaticamente.

## Endpoints principais

### Auth

```bash
# Registro (primeiro vira admin)
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@geo.dev","password":"senhaSegura123"}'

# Login
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@geo.dev","password":"senhaSegura123"}'
```

### Camadas

```bash
TOKEN="cole-o-accessToken-aqui"

# Listar
curl http://localhost:3000/api/v1/layers

# Criar camada WMS
curl -X POST http://localhost:3000/api/v1/layers \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Solos","type":"wms","source_url":"https://servidor/wms"}'
```

### Upload de GeoJSON

```bash
curl -X POST http://localhost:3000/api/v1/upload/geojson \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@dados.geojson" \
  -F "name=Capitais" \
  -F "is_public=true"
```

### **Consulta por bounding box (o endpoint crítico)**

```bash
# bbox = oeste,sul,leste,norte
curl "http://localhost:3000/api/v1/layers/$LAYER_ID/features?bbox=-50,-20,-40,-10&limit=500&simplify=0.001"
```

Retorna `FeatureCollection` com apenas as feições que intersectam a área.
O filtro é feito no PostGIS (`ST_MakeEnvelope` + operador `&&` + índice GiST).

## Integração com o frontend Leaflet

Substitua a função `computeRows()` do frontend por um `fetch`:

```js
async function computeRows() {
  const b = map.getBounds();
  const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
  const res = await fetch(
    `${API}/api/v1/layers/${layerId}/features?bbox=${bbox}&limit=500`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const geojson = await res.json();
  return geojson.features;
}
```

Chame em `map.on('moveend', debounce(computeRows, 180))`.

## Performance

- Índice **GiST** em `features.geom` → consultas por bbox em ms.
- Índice **GIN** em `properties` → filtros por atributo rápidos.
- Cache **Redis** por `(layer, bbox, limit, simplify)` com TTL de 60s.
- Limite máximo de feições por resposta: 5000 (configurável).
- `simplify` aplica `ST_SimplifyPreserveTopology` para reduzir payload em zoom baixo.

## Segurança

- Senhas com bcrypt (custo 12).
- JWT: access (15 min) + refresh (7 dias).
- Papéis: `admin` (tudo), `viewer` (leitura + suas camadas).
- Rate limit: recomendado adicionar `slowapi` (já nas deps) — configure conforme necessidade.
- CORS por whitelist em `CORS_ORIGINS`.
- Sem stack trace em produção (`ENV=production`).

## Estrutura

```
app/
  main.py            FastAPI app
  config.py          Settings via .env
  database.py        SQLAlchemy async engine
  redis_client.py    Cliente Redis
  models.py          User, Layer, Feature (GeoAlchemy2)
  schemas.py         Pydantic v2
  security.py        bcrypt + JWT
  deps.py            Dependências (auth, session)
  routers/           auth, layers, features, upload
  services/          regras de negócio
  utils/             bbox, logger
migrations/          SQL inicial (PostGIS)
```

## Próximos passos sugeridos

1. **Tiles vetoriais (MVT)** — `ST_AsMVT` para zoom alto.
2. **Clusterização server-side** — para zoom baixo com muitos pontos.
3. **Rate limiting com slowapi** — proteger endpoints de escrita.
4. **Alembic** — migrations versionadas.
5. **Testes** — `pytest` + `httpx.AsyncClient` + `testcontainers`.
6. **Audit log** — histórico de alterações.