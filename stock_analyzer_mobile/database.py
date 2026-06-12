import os
from typing import Optional
from supabase import create_client, Client

_client: Optional[Client] = None


def _get_config():
    try:
        import streamlit as st
        return st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    except Exception:
        return os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")


def get_client() -> Client:
    global _client
    if _client is None:
        url, key = _get_config()
        _client = create_client(url, key)
    return _client


def get_admin_client() -> Client:
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_SERVICE_KEY", "")
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    return create_client(url, key)


def restore_session(access_token: str, refresh_token: str):
    client = get_client()
    client.auth.set_session(access_token, refresh_token)


def get_user_by_username(username: str) -> Optional[dict]:
    client = get_client()
    result = client.table("users").select("*").eq("username", username).execute()
    return result.data[0] if result.data else None


def get_user_by_auth_id(auth_id: str) -> Optional[dict]:
    client = get_client()
    result = client.table("users").select("*").eq("auth_id", auth_id).execute()
    return result.data[0] if result.data else None


def create_user(username: str, auth_id: str) -> dict:
    client = get_client()
    result = client.table("users").insert({
        "username": username,
        "auth_id": auth_id,
    }).execute()
    return result.data[0]


def get_watchlist(user_id: int) -> list:
    client = get_client()
    result = client.table("watchlist").select("*").eq("user_id", user_id).order("id").execute()
    return result.data


def add_watchlist_item(user_id: int, item: dict) -> dict:
    client = get_client()
    result = client.table("watchlist").insert({
        "user_id": user_id,
        "symbol": item["symbol"],
        "name": item["name"],
        "buy_price": item["buy_price"],
        "shares": item["shares"],
        "buy_date": item["buy_date"],
        "strategy": item["strategy"],
    }).execute()
    return result.data[0]


def remove_watchlist_item(user_id: int, item_id: int):
    client = get_client()
    client.table("watchlist").delete().eq("id", item_id).eq("user_id", user_id).execute()
