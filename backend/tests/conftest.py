import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.seed import seed_platforms

# In-memory test SQLite engine
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    # Seed platform metadata for tests
    from app.seed import PLATFORMS_SEED_DATA
    from app.models.platform import Platform
    import uuid

    db = TestingSessionLocal()
    for item in PLATFORMS_SEED_DATA:
        plat = Platform(
            id=uuid.uuid4(),
            name=item["name"],
            slug=item["slug"],
            category=item["category"],
            integration_type=item["integration_type"],
            description=item["description"],
            logo_url=item["logo_url"],
            is_active=True
        )
        db.add(plat)
    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session() -> Generator:
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session) -> Generator:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_token(client) -> dict:
    """Helper creating User A and returning auth header."""
    res = client.post("/api/auth/register", json={
        "email": "usera@example.com",
        "password": "SecurePassword123!",
        "full_name": "User Alpha"
    })
    data = res.json()
    token = data["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": data["user"]
    }


@pytest.fixture
def test_user_b_token(client) -> dict:
    """Helper creating User B and returning auth header."""
    res = client.post("/api/auth/register", json={
        "email": "userb@example.com",
        "password": "SecurePassword456!",
        "full_name": "User Beta"
    })
    data = res.json()
    token = data["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": data["user"]
    }
