"""
Pytest configuration and fixtures for testing.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

# SQLite fallback for JSONB - convert to TEXT
from sqlalchemy.ext.compiler import compiles
@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return compiler.visit_TEXT(Text(), **kw)

from backend.db.base import Base
from backend.db.models.prediction import Prediction
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.news import NewsArticle
from backend.db.models.model import Model


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh database engine for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_stock_code():
    """Return a sample stock code for testing."""
    return "005930"  # Samsung Electronics


@pytest.fixture
def sample_model(db_session):
    """Create a sample model for testing."""
    model = Model(
        id=1,
        name="gpt-4o-test",
        model_identifier="gpt-4o",
        provider="openai",
        is_active=True,
        description="Test Model"
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def sample_news(db_session):
    """Create a sample news article for testing."""
    news = NewsArticle(
        id=1,
        title="Test News",
        content="Test content",
        url="https://test.com",
        published_at=datetime.now(),
        source="Test Source",
        related_stock_codes=["005930"]
    )
    db_session.add(news)
    db_session.commit()
    db_session.refresh(news)
    return news


def create_predictions(db_session, stock_code: str, count: int, direction: str = None, start_time: datetime = None):
    """
    Helper function to create multiple test predictions.

    Args:
        db_session: Database session
        stock_code: Stock code
        count: Number of predictions to create
        direction: Optional specific direction (default: alternating up/hold/down)
        start_time: Optional start time (default: now)
    """
    if start_time is None:
        start_time = datetime.now()

    # Create a news article first
    news = NewsArticle(
        title=f"Test News for {stock_code}",
        content="Test content",
        url=f"https://test.com/{stock_code}",
        published_at=start_time,
        source="Test Source",
        stock_code=stock_code
    )
    db_session.add(news)
    db_session.flush()

    # Create a model if not exists
    model = db_session.query(Model).filter(Model.id == 1).first()
    if not model:
        model = Model(
            id=1,
            name="gpt-4o-test",
            model_identifier="gpt-4o",
            provider="openai",
            is_active=True,
            description="Test Model"
        )
        db_session.add(model)
        db_session.flush()

    directions = ["up", "hold", "down"]
    predictions = []

    for i in range(count):
        pred_direction = direction if direction else directions[i % 3]
        prediction = Prediction(
            news_id=news.id,
            model_id=model.id,
            stock_code=stock_code,
            direction=pred_direction,
            confidence=0.75 + (i % 3) * 0.05,  # Vary confidence slightly
            reasoning=f"Test reasoning {i+1}",
            current_price=50000 + i * 100,
            target_period="1일",
            created_at=start_time - timedelta(minutes=count - i)  # Newer predictions created later
        )
        db_session.add(prediction)
        predictions.append(prediction)

    db_session.commit()
    for pred in predictions:
        db_session.refresh(pred)

    return predictions
