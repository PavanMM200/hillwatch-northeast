"""All fixtures are simulated. No test uses paid APIs or live satellite observations."""
import os,sys,tempfile
from pathlib import Path
test_root=Path(tempfile.mkdtemp(prefix='hillwatch-tests-'))
os.environ['DATABASE_URL']='sqlite:///'+(test_root/'tests.sqlite').as_posix()
os.environ['DATA_DIR']=str(test_root)
os.environ['MAPS_ROUTES_KEY']=''
os.environ['MAPS_BROWSER_KEY']=''
os.environ['EE_PROJECT']=''
os.environ['MATLAB_EXECUTABLE']=''
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app.main import app,limits
from app.database import Base,engine,Session,User
from app.auth import hash_password
@pytest.fixture(autouse=True)
def reset():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);limits.clear()
    yield
@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers['X-Requested-With']='Hillwatch';yield c
@pytest.fixture
def authority(client):
    with Session() as db:
        db.add(User(username='simulated-authority',password_hash=hash_password('simulated-test-password'),role='Road Authority'));db.commit()
    assert client.post('/api/auth/login',json={'username':'simulated-authority','password':'simulated-test-password'}).status_code==200
    return client
