"""
Streamlit + Supabase demo with authentication and Row Level Security.

Each visitor signs in with Supabase Auth (email + password). Every query is
sent with that user's access token, so the RLS policies in
supabase/schema.sql only ever return or change that user's own todos.
"""

import streamlit as st
from supabase import Client, ClientOptions, create_client

st.set_page_config(page_title="Streamlit + Supabase Demo", page_icon="✅")

TABLE = "todos"


def get_client() -> Client:
    """One Supabase client per browser session.

    Don't use a cached/shared client (e.g. st.connection or st.cache_resource)
    here: Streamlit shares cached objects across all visitors, so one person
    signing in would sign everyone in as them.
    """
    if "sb" not in st.session_state:
        cfg = st.secrets["connections"]["supabase_connection"]
        st.session_state.sb = create_client(
            cfg["url"],
            cfg["key"],
            options=ClientOptions(persist_session=False),
        )
    return st.session_state.sb


sb = get_client()
st.title("✅ Streamlit + Supabase Demo")


def auth_screen():
    st.caption("Sign in to see your todos. Each user only sees their own rows.")
    sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])

    with sign_in_tab:
        with st.form("sign_in"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in"):
                try:
                    res = sb.auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign-in failed: {e}")

    with sign_up_tab:
        with st.form("sign_up"):
            email = st.text_input("Email")
            password = st.text_input("Password (min 6 characters)", type="password")
            if st.form_submit_button("Create account"):
                try:
                    res = sb.auth.sign_up({"email": email.strip(), "password": password})
                    if res.session:  # email confirmation is turned off
                        st.session_state.user = res.user
                        st.rerun()
                    else:
                        st.success(
                            "Account created. Check your email for a confirmation "
                            "link, then sign in."
                        )
                except Exception as e:
                    st.error(f"Sign-up failed: {e}")


if "user" not in st.session_state:
    auth_screen()
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.write(f"Signed in as **{user.email}**")
    if st.button("Sign out"):
        sb.auth.sign_out()
        del st.session_state["user"]
        st.rerun()


def load_todos():
    # No .eq("user_id", ...) needed: RLS filters to this user's rows server-side.
    return sb.table(TABLE).select("*").order("id").execute().data


st.subheader("Add a todo")
with st.form("add_todo", clear_on_submit=True):
    task = st.text_input("Task", placeholder="e.g. Learn Row Level Security")
    if st.form_submit_button("Add") and task.strip():
        # user_id is filled in by the database (default auth.uid()).
        sb.table(TABLE).insert({"task": task.strip()}).execute()
        st.rerun()

st.subheader("Your todos")

try:
    todos = load_todos()
except Exception as e:
    st.error(
        "Couldn't load todos. Check .streamlit/secrets.toml and that you ran "
        "supabase/schema.sql in the SQL Editor."
    )
    st.exception(e)
    st.stop()

if not todos:
    st.info("No todos yet — add one above.")
else:
    for row in todos:
        col_done, col_task, col_delete = st.columns([0.12, 0.68, 0.2])

        with col_done:
            done = st.checkbox(
                "Done",
                value=row["is_complete"],
                key=f"done_{row['id']}",
                label_visibility="collapsed",
            )
            if done != row["is_complete"]:
                sb.table(TABLE).update({"is_complete": done}).eq("id", row["id"]).execute()
                st.rerun()

        with col_task:
            st.markdown(f"~~{row['task']}~~" if row["is_complete"] else row["task"])

        with col_delete:
            if st.button("Delete", key=f"del_{row['id']}"):
                sb.table(TABLE).delete().eq("id", row["id"]).execute()
                st.rerun()

with st.expander("Raw rows returned from Supabase"):
    st.dataframe(todos, width="stretch")
