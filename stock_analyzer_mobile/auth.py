import streamlit as st
import database as db

SUPABASE_EMAIL_DOMAIN = "@stockpulse.app"


def register(username: str, password: str) -> tuple[bool, str]:
    if len(username) < 2:
        return False, "帳號至少 2 個字元"
    if len(password) < 4:
        return False, "密碼至少 4 個字元"
    try:
        email = f"{username}{SUPABASE_EMAIL_DOMAIN}"
        admin = db.get_admin_client()
        result = admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"username": username},
        })
        if result.user:
            auth_id = result.user.id
            db.create_user(username, auth_id)
            return True, "註冊成功，請登入"
        return False, "註冊失敗"
    except Exception as e:
        msg = str(e)
        if "already" in msg.lower():
            return False, "此帳號已被註冊"
        return False, msg


def login(username: str, password: str) -> tuple[bool, str]:
    try:
        client = db.get_client()
        email = f"{username}{SUPABASE_EMAIL_DOMAIN}"
        result = client.auth.sign_in_with_password({"email": email, "password": password})
        session = result.session
        if not session:
            return False, "登入失敗"
        st.session_state["supabase_session"] = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
        auth_id = result.user.id
        _store_user_info(auth_id)
        return True, "登入成功"
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "帳號或密碼錯誤"
        if "Email not confirmed" in msg:
            return False, "請先驗證 Email（需在 Supabase 關閉 email confirm）"
        return False, msg


def _store_user_info(auth_id: str):
    st.session_state["auth_id"] = auth_id
    user_meta = None
    try:
        client = db.get_client()
        auth_user = client.auth.get_user()
        user_meta = auth_user.user.user_metadata
    except Exception:
        pass
    rec = db.get_user_by_auth_id(auth_id)
    if rec:
        st.session_state["user_id"] = rec["id"]
        st.session_state["username"] = rec["username"]
    elif user_meta and user_meta.get("username"):
        st.session_state["username"] = user_meta["username"]


def restore_session_from_state():
    session_data = st.session_state.get("supabase_session")
    if session_data:
        try:
            db.restore_session(session_data["access_token"], session_data["refresh_token"])
            auth_id = st.session_state.get("auth_id")
            if auth_id:
                rec = db.get_user_by_auth_id(auth_id)
                if rec:
                    st.session_state["user_id"] = rec["id"]
                    st.session_state["username"] = rec["username"]
        except Exception:
            st.session_state["supabase_session"] = None
            st.session_state["logged_in"] = False


def logout():
    try:
        client = db.get_client()
        client.auth.sign_out()
    except Exception:
        pass
    st.session_state["supabase_session"] = None
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state.pop("auth_id", None)
    st.session_state.pop("user_id", None)


def get_watchlist(username: str) -> list:
    user_id = st.session_state.get("user_id")
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
    user_id = st.session_state.get("user_id")
    if user_id is None:
        return False
    db.add_watchlist_item(user_id, item)
    return True


def remove_from_watchlist(username: str, item_id: int):
    user_id = st.session_state.get("user_id")
    if user_id is not None:
        db.remove_watchlist_item(user_id, item_id)
