from models import User, db


def test_user_crud(client):
    # Create
    user = User(email="u@example.com", password="pwd", role="parent")
    db.session.add(user)
    db.session.commit()
    assert User.query.count() == 1

    # Read & Update
    fetched = User.query.first()
    fetched.role = "teacher"
    db.session.commit()
    assert db.session.get(User, fetched.id).role == "teacher"

    # Delete
    db.session.delete(fetched)
    db.session.commit()
    assert User.query.count() == 0
