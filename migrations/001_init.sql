CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'viewer',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE layers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  type TEXT NOT NULL,                -- 'geojson' | 'wms' | 'xyz'
  source_url TEXT,
  style JSONB DEFAULT '{}',
  feature_count INT DEFAULT 0,
  bbox GEOMETRY(Polygon, 4326),
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  is_public BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE features (
  id BIGSERIAL PRIMARY KEY,
  layer_id UUID REFERENCES layers(id) ON DELETE CASCADE,
  properties JSONB DEFAULT '{}',
  geom GEOMETRY(Geometry, 4326) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX features_geom_idx   ON features USING GIST (geom);
CREATE INDEX features_layer_idx  ON features (layer_id);
CREATE INDEX features_props_idx  ON features USING GIN (properties);
CREATE INDEX layers_bbox_idx     ON layers   USING GIST (bbox);
CREATE INDEX layers_owner_idx    ON layers   (owner_id);