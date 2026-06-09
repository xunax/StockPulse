import os
from supabase import create_client, Client

_client: Client | None = None


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


def get_user_by_username(username: str) -> dict | None:
    client = get_client()
    result = client.table("users").select("*").eq("username", username).execute()
    return result.data[0] if result.data else None


def create_user(username: str, password_hash: str) -> dict:
    client = get_client()
    result = client.table("users").insert({
        "username": username,
        "password_hash": password_hash,
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
