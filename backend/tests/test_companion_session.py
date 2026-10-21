"""Companion session state must tolerate concurrent first requests."""
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.services.companion_service import get_or_rotate_avatar


class Query:
    def __init__(self, session):
        self.session = session

    def filter(self, *args):
        return self

    def first(self):
        self.session.queries += 1
        if self.session.queries == 1:
            return None
        return SimpleNamespace(
            current_shape="molecule",
            current_color="green",
            last_session_key="winner",
        )


class RacingSession:
    def __init__(self):
        self.queries = 0
        self.rolled_back = False

    def query(self, model):
        return Query(self)

    def add(self, state):
        pass

    def commit(self):
        raise IntegrityError("insert avatar_state", {}, Exception("unique user_id"))

    def rollback(self):
        self.rolled_back = True


def test_concurrent_avatar_insert_reloads_winning_row():
    db = RacingSession()
    avatar = get_or_rotate_avatar(db, user_id=7, session_key="loser")
    assert db.rolled_back is True
    assert avatar == {"shape": "molecule", "color": "green"}
