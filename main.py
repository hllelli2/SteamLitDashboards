# app.py
import streamlit as st
import os
import importlib.util
from pathlib import Path

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Multi-Page Dashboard", layout="wide")
st.title("📊")

# ---- DETECT SUBDIRECTORIES ----
BASE_DIR = Path(__file__).parent
subdirs = [f for f in BASE_DIR.iterdir() if f.is_dir() and not f.name.startswith("__")]

# extra check if they don't have dashboard.py
subdirs = [d for d in subdirs if (d / "dashboard.py").exists()]
if not subdirs:
    st.warning(
        "No dashboards found. Please add subdirectories with a dashboard.py file."
    )
    st.stop()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a dashboard", [d.name for d in subdirs])


# ---- DYNAMIC IMPORT FUNCTION ----
def load_page(page_dir):
    page_file = (
        Path(page_dir) / "dashboard.py"
    )  # convention: each page has dashboard.py
    if page_file.exists():
        spec = importlib.util.spec_from_file_location("dashboard", page_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "app"):
            module.app()  # must define app() function inside dashboard.py
        else:
            st.error(f"`{page_file}` must define an app() function")
    else:
        st.warning(f"No dashboard.py found in {page_dir}")


# ---- LOAD SELECTED PAGE ----
selected_dir = BASE_DIR / page
load_page(selected_dir)
