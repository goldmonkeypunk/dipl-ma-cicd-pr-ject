import pytest
from app import app, db


@pytest.fixture()
def client():
    """Тестовий Flask‑клієнт із чистою БД SQLite in‑memory."""
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
