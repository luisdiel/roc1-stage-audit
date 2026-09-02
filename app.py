
# ============================================================
# ROC1 Stage Audit — Streamlit App
# Developed by: Luis Diel
# Repository: github.com/luisdiel/roc1-stage-audit
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime, date
import pytz
from database import (
    init_supabase,
    insert_audit,
    get_audits_by_date,
    get_all_audits,
)
from locations import LOCATIONS
from qr_map import get_location_from_uuid

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="ROC1 Stage Audit",
    page_icon="📋",
    layout="wide",
)

# ── Constants ────────────────────────────────────────────────
EASTERN = pytz.timezone("America/New_York")
SHIFTS = ["FHN (Sun–Wed)", "BHN (Wed–Sat)", "FHD (Sun–Wed)", "BHD (Wed–Sat)"]
AUDIT_RESULTS = ["Pass ✅", "Fail ❌", "N/A ⚪"]

# ── Session State Initialization ─────────────────────────────
if "supabase" not in st.session_state:
    st.session_state.supabase = init_supabase()

if "auditor_name" not in st.session_state:
    st.session_state.auditor_name = ""

if "selected_shift" not in st.session_state:
    st.session_state.selected_shift = SHIFTS[0]

if "scan_input" not in st.session_state:
    st.session_state.scan_input = ""

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/amazon.png",
        width=60,
    )
    st.title("ROC1 Stage Audit")
    st.caption("FC AR Sortable — ROC1")

    st.divider()

    # Auditor Info
    st.subheader("👤 Auditor Info")
    st.session_state.auditor_name = st.text_input(
        "Your Login (e.g., luisdiel)",
        value=st.session_state.auditor_name,
        placeholder="Enter your login",
    )
    st.session_state.selected_shift = st.selectbox(
        "Current Shift", SHIFTS
    )

    st.divider()

    # Navigation
    st.subheader("📂 Navigation")
    page = st.radio(
        "Go to",
        ["🔍 New Audit", "📊 Dashboard", "📥 Export Data"],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("Developed by Luis Diel")
    st.caption(f"v1.0 • {datetime.now(EASTERN).strftime('%m/%d/%Y')}")


# ══════════════════════════════════════════════════════════════
# PAGE 1: NEW AUDIT
# ══════════════════════════════════════════════════════════════
if page == "🔍 New Audit":
    st.header("🔍 New Stage Audit")

    if not st.session_state.auditor_name:
        st.warning("⚠️ Please enter your login in the sidebar to begin.")
        st.stop()

    # ── Location Selection ───────────────────────────────────
    st.subheader("📍 Select Location")

    tab_scan, tab_manual = st.tabs(["📷 Scan QR Code", "✏️ Manual Select"])

    with tab_scan:
        scan_input = st.text_input(
            "Scan or paste QR UUID here",
            value="",
            placeholder="Scan the QR code at the stage location...",
            key="qr_scanner",
        )

        if scan_input:
            location = get_location_from_uuid(scan_input.strip())
            if location:
                st.success(f"✅ Location detected: **{location}**")
                selected_location = location
            else:
                st.error("❌ QR code not recognized. Try manual select.")
                selected_location = None
        else:
            selected_location = None

    with tab_manual:
        # Group locations by door
        doors = sorted(set(loc.split("-")[1] for loc in LOCATIONS))
        selected_door = st.selectbox(
            "Select Door", doors, index=0
        )
        door_locations = sorted(
            [loc for loc in LOCATIONS if f"-{selected_door}-" in loc]
        )
        manual_location = st.selectbox(
            "Select Position", door_locations
        )
        if st.button("Use this location", key="use_manual"):
            selected_location = manual_location

    # ── Audit Form ───────────────────────────────────────────
    if selected_location:
        st.divider()
        st.subheader(f"📋 Audit: {selected_location}")

        with st.form("audit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                audit_result = st.radio(
                    "Audit Result",
                    AUDIT_RESULTS,
                    horizontal=True,
                )

            with col2:
                condition = st.selectbox(
                    "Stage Condition",
                    [
                        "Clean & Organized",
                        "Needs Attention",
                        "Safety Concern",
                        "Missing Label/Sign",
                        "Blocked/Obstructed",
                        "Other",
                    ],
                )

            notes = st.text_area(
                "Notes (optional)",
                placeholder="Any additional observations...",
                max_chars=500,
            )

            submitted = st.form_submit_button(
                "✅ Submit Audit", use_container_width=True
            )

            if submitted:
                now = datetime.now(EASTERN)
                audit_data = {
                    "audit_date": now.strftime("%Y-%m-%d"),
                    "audit_time": now.strftime("%H:%M:%S"),
                    "auditor": st.session_state.auditor_name,
                    "shift": st.session_state.selected_shift,
                    "location": selected_location,
                    "result": audit_result,
                    "condition": condition,
                    "notes": notes,
                }

                try:
                    insert_audit(
                        st.session_state.supabase, audit_data
                    )
                    st.success(
                        f"✅ Audit submitted for **{selected_location}**!"
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error saving audit: {e}")


# ══════════════════════════════════════════════════════════════
# PAGE 2: DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.header("📊 Audit Dashboard")

    # Date filter
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        view_date = st.date_input(
            "Select Date", value=date.today()
        )

    # Fetch data
    audits = get_audits_by_date(
        st.session_state.supabase,
        view_date.strftime("%Y-%m-%d"),
    )

    if not audits:
        st.info(
            f"📭 No audits found for {view_date.strftime('%m/%d/%Y')}."
        )
        st.stop()

    df = pd.DataFrame(audits)

    # ── KPI Cards ────────────────────────────────────────────
    st.subheader("📈 Summary")
    k1, k2, k3, k4 = st.columns(4)

    total = len(df)
    passes = len(df[df["result"].str.contains("Pass")])
    fails = len(df[df["result"].str.contains("Fail")])
    pass_rate = (passes / total * 100) if total > 0 else 0

    k1.metric("Total Audits", total)
    k2.metric("Passed", passes)
    k3.metric("Failed", fails)
    k4.metric("Pass Rate", f"{pass_rate:.1f}%")

    # ── Coverage Progress ────────────────────────────────────
    st.subheader("📍 Coverage Progress")
    total_locations = len(LOCATIONS)
    audited_locations = df["location"].nunique()
    coverage = (audited_locations / total_locations * 100) if total_locations > 0 else 0

    st.progress(coverage / 100)
    st.caption(
        f"{audited_locations} of {total_locations} locations audited "
        f"({coverage:.1f}%)"
    )

    # ── Results by Door ──────────────────────────────────────
    st.subheader("🚪 Results by Door")
    df["door"] = df["location"].apply(
        lambda x: x.split("-")[1] if "-" in x else x
    )
    door_summary = (
        df.groupby("door")
        .agg(
            Total=("result", "count"),
            Passed=("result", lambda x: x.str.contains("Pass").sum()),
            Failed=("result", lambda x: x.str.contains("Fail").sum()),
        )
        .reset_index()
    )
    door_summary["Pass Rate"] = (
        door_summary["Passed"] / door_summary["Total"] * 100
    ).round(1)
    st.dataframe(door_summary, use_container_width=True, hide_index=True)

    # ── Detailed Table ───────────────────────────────────────
    st.subheader("📋 All Audits")
    st.dataframe(
        df[
            [
                "audit_time",
                "auditor",
                "shift",
                "location",
                "result",
                "condition",
                "notes",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════════════════════
# PAGE 3: EXPORT DATA
# ══════════════════════════════════════════════════════════════
elif page == "📥 Export Data":
    st.header("📥 Export Audit Data")

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        start_date = st.date_input("Start Date", value=date.today())
    with col_exp2:
        end_date = st.date_input("End Date", value=date.today())

    if st.button("🔄 Load Data", use_container_width=True):
        all_audits = get_all_audits(st.session_state.supabase)

        if all_audits:
            df_all = pd.DataFrame(all_audits)
            df_all["audit_date"] = pd.to_datetime(df_all["audit_date"])

            mask = (df_all["audit_date"].dt.date >= start_date) & (
                df_all["audit_date"].dt.date <= end_date
            )
            df_filtered = df_all[mask]

            if not df_filtered.empty:
                st.success(
                    f"✅ Found {len(df_filtered)} audits from "
                    f"{start_date.strftime('%m/%d/%Y')} to "
                    f"{end_date.strftime('%m/%d/%Y')}"
                )
                st.dataframe(
                    df_filtered, use_container_width=True, hide_index=True
                )

                csv = df_filtered.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"ROC1_audits_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.warning("No audits found for the selected date range.")
        else:
            st.info("📭 No audit data available yet.")

