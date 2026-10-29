import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, JSON, Text, Integer, Float, ForeignKey, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
settings.data_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True)
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA busy_timeout=30000')
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(24), default='Traveller')
class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[str] = mapped_column(String(40))
class Route(Base):
    __tablename__ = 'routes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    payload: Mapped[dict] = mapped_column(JSON)
class Segment(Base):
    __tablename__ = 'segments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    route_id: Mapped[str] = mapped_column(ForeignKey('routes.id'), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    route_id: Mapped[str] = mapped_column(ForeignKey('routes.id'))
    state: Mapped[str] = mapped_column(String(24), default='queued', index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    request: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
class Scene(Base):
    __tablename__ = 'scenes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
class Candidate(Base):
    __tablename__ = 'candidates'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    segment_id: Mapped[str] = mapped_column(ForeignKey('segments.id'))
    payload: Mapped[dict] = mapped_column(JSON)
class Incident(Base):
    __tablename__ = 'incidents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(String(36), unique=True)
    submitted_at: Mapped[str] = mapped_column(String(40), default=now)
    observed_at: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    kind: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    direction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route_id: Mapped[str | None] = mapped_column(ForeignKey('routes.id'), nullable=True)
    segment_id: Mapped[str | None] = mapped_column(ForeignKey('segments.id'), nullable=True)
    moderation: Mapped[str] = mapped_column(String(24), default='UNVERIFIED')
    status: Mapped[str] = mapped_column(String(24), default='ACTIVE')
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    flags: Mapped[int] = mapped_column(Integer, default=0)
class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(ForeignKey('incidents.id'), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    payload: Mapped[dict] = mapped_column(JSON)
class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
