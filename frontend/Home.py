"""Streamlit shell: disclaimer, demo-user switcher, and the current user's profile.

The frontend only talks to the API over HTTP; it never touches the database.
"""

import os
from typing import Any, NoReturn

import httpx2
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
DEMO_USER_HEADER = "X-Demo-User"
DISCLAIMER = "Synthetic demo data only — not for production banking data."


def stop_with_error(message: str) -> NoReturn:
    st.error(message)
    st.stop()


def fetch(path: str, username: str | None = None) -> Any:
    """GET an API path and return its JSON; on failure, explain why and stop this run."""
    headers = {DEMO_USER_HEADER: username} if username else {}
    try:
        response = httpx2.get(f"{API_BASE_URL}/api/v1{path}", headers=headers, timeout=5)
    except httpx2.HTTPError:
        stop_with_error(
            f"The API is unreachable at {API_BASE_URL}. "
            "Check that the api service is running (`docker compose ps`) and reload."
        )
    if response.is_error:
        try:
            message = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = f"HTTP {response.status_code}"
        stop_with_error(f"The API returned an error: {message}")
    return response.json()


st.set_page_config(page_title="Banking Data Lakehouse Simulator", page_icon=":bank:")
st.warning(DISCLAIMER)
st.title("Banking Data Lakehouse Simulator")

users = {user["username"]: user for user in fetch("/demo-users")["items"]}
if not users:
    stop_with_error(
        "No demo users found. Seed them with "
        "`docker compose exec api python -m scripts.seed_demo_data`."
    )

username = st.sidebar.selectbox(
    "Demo user",
    options=list(users),
    index=None,
    placeholder="Pick a demo user",
    format_func=lambda name: f"{users[name]['display_name']} ({users[name]['unit']['unit_name']})",
    key="demo_user",
)
st.sidebar.caption("Mock sign-in: the API trusts the selected demo user.")

if username is None:
    st.info("Pick a demo user in the sidebar to continue.")
    st.stop()

me = fetch("/me", username)
st.subheader(me["display_name"])
st.markdown(f"**Unit:** {me['unit']['unit_name']}")
st.markdown("**Roles:** " + ", ".join(role["role_name"] for role in me["roles"]))
st.caption(f"{me['username']} · {me['email']}")
