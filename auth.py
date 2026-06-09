import hashlib
import database as db


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register(username: str, password: str) -> tuple[bool, str]:
    if len(username) < 2:
        return False, "帳號至少 2 個字元"
    if len(password) < 4:
        return False, "密碼至少 4 個字元"

    existing = db.get_user_by_username(username)
    if existing:
        return False, "此帳號已被註冊"

    db.create_user(username, _hash_password(password))
    return True, "註冊成功"


def login(username: str, password: str) -> tuple[bool, str]:
    user = db.get_user_by_username(username)
    if not user:
        return False, "帳號不存在"
    if user["password_hash"] != _hash_password(password):
        return False, "密碼錯誤"
    return True, "登入成功"


def get_user_id(username: str) -> int | None:
    user = db.get_user_by_username(username)
    return user["id"] if user else None


def get_watchlist(username: str) -> list:
    user_id = get_user_id(username)
    if user_id is None:
        return []
    items = db.get_watchlist(user_id)
    return [
        {
            "id": item["id"],
            "symbol": item["symbol"],
            "name": item["name"],
            "buy_price": item["buy_price"],
            "shares": item["shares"],
            "buy_date": item["buy_date"],
            "strategy": item["strategy"],
        }
        for item in items
    ]


def add_to_watchlist(username: str, item: dict) -> bool:
    user_id = get_user_id(username)
    if user_id is None:
        return False
    db.add_watchlist_item(user_id, item)
    return True


def remove_from_watchlist(username: str, item_id: int):
    user_id = get_user_id(username)
    if user_id is not None:
        db.remove_watchlist_item(user_id, item_id)
