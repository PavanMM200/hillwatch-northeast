"""Initial tables and optional PostGIS expression indexes on stored GeoJSON."""
from alembic import op
from app.database import Base
revision='0001'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind();Base.metadata.create_all(bind)
    if bind.dialect.name=='postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
        op.execute("CREATE INDEX routes_geometry_gist ON routes USING gist (ST_SetSRID(ST_GeomFromGeoJSON(payload->>'geometry'),4326))")
        op.execute("CREATE INDEX incidents_point_gist ON incidents USING gist (ST_SetSRID(ST_MakePoint(longitude,latitude),4326))")
def downgrade():Base.metadata.drop_all(op.get_bind())
