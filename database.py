
# ============================================================
# ROC1 Stage Audit — Streamlit App
# Developed by: Luis Diel
# Repository: github.com/luisdiel/roc1-stage-audit
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime, date
import pytz
from database import get_database
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
STATUS_OPTIONS = ["Green ✅", "Yellow ⚠️", "Red ❌"]
PERIODS = ["Period 1", "Period 2", "Period 3"]

# ── Session State Initialization ─────────────────────────────
if "db" not in st.session_state:
    st.session_state.db = get_database()

if "auditor_name" not in st.session_state:
    st.session_state.auditor_name = ""

if "selected_shift" not in st.session_state:
    st.session_state.selected_shift = SHIFTS[0]

if "selected_location" not in st.session_state:
    st.session_state.selected_location = None

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

    now = datetime.now(EASTERN)
    audit_date = now.strftime("%Y-%m-%d")

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
                st.session_state.selected_location = location
            else:
                st.error("❌ QR code not recognized. Try manual select.")
                st.session_state.selected_location = None
        else:
            if not st.session_state.selected_location:
                st.session_state.selected_location = None

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
        if st.button("✅ Use this location", key="use_manual", use_container_width=True):
            st.session_state.selected_location = manual_location
            st.rerun()

    # Show current selection
    if st.session_state.selected_location:
        st.info(f"📍 Selected: **{st.session_state.selected_location}**")

    # ── Audit Form ───────────────────────────────────────────
    if st.session_state.selected_location:
        st.divider()
        st.subheader(f"📋 Audit: {st.session_state.selected_location}")

        with st.form("audit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                status = st.radio(
                    "Status",
                    STATUS_OPTIONS,
                    horizontal=True,
                )
                period = st.selectbox("Period", PERIODS)

            with col2:
                container = st.text_input(
                    "Container ID (optional)",
                    placeholder="Scan or type container...",
                )

            st.markdown("**Issue Flags:**")
            flag_col1, flag_col2, flag_col3, flag_col4 = st.columns(4)
            with flag_col1:
                mix = st.checkbox("Mix/Match")
            with flag_col2:
                pvm = st.checkbox("PVM Issue")
            with flag_col3:
                lbl = st.checkbox("Label Problem")
            with flag_col4:
                qr_issue = st.checkbox("QR Issue")

            submitted = st.form_submit_button(
                "✅ Submit Audit", use_container_width=True
            )

            if submitted:
                try:
                    st.session_state.db.save_audit(
                        location=st.session_state.selected_location,
                        shift=st.session_state.selected_shift,
                        audit_date=audit_date,
                        period=period,
                        status=status,
                        container=container,
                        mix=mix,
                        pvm=pvm,
                        lbl=lbl,
                        qr_issue=qr_issue,
                        auditor=st.session_state.auditor_name,
                    )
                    st.success(
                        f"✅ Audit submitted for "
                        f"**{st.session_state.selected_location}**!"
                    )
                    st.balloons()
                    st.session_state.selected_location = None
                except Exception as e:
                    st.error(f"❌ Error saving audit: {e}")


# ══════════════════════════════════════════════════════════════
# PAGE 2: DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.header("📊 Audit Dashboard")

    now = datetime.now(EASTERN)

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        view_date = st.date_input("Select Date", value=date.today())
    with col_f2:
        view_shift = st.selectbox("Select Shift", SHIFTS)

    # Fetch data using db.get_audits(shift, date)
    audits = st.session_state.db.get_audits(
        shift=view_shift,
        audit_date=view_date.strftime("%Y-%m-%d"),
    )

    if not audits:
        st.info(
            f"📭 No audits found for {view_date.strftime('%m/%d/%Y')} "
            f"— {view_shift}."
        )
        st.stop()

    # Convert dict to DataFrame
    rows = []
    for loc, data in audits.items():
        rows.append({"location": loc, **data})
    df = pd.DataFrame(rows)

    # ── KPI Cards ────────────────────────────────────────────
    st.subheader("📈 Summary")
    k1, k2, k3, k4 = st.columns(4)

    total = len(df)
    greens = len(df[df["status"].str.contains("Green", na=False)])
    reds = len(df[df["status"].str.contains("Red", na=False)])
    green_rate = (greens / total * 100) if total > 0 else 0

    k1.metric("Total Audits", total)
    k2.metric("Green ✅", greens)
    k3.metric("Red ❌", reds)
    k4.metric("Green Rate", f"{green_rate:.1f}%")

    # ── Coverage Progress ────────────────────────────────────
    st.subheader("📍 Coverage Progress")
    total_locations = len(LOCATIONS)
    audited_locations = df["location"].nunique()
    coverage = (
        (audited_locations / total_locations * 100)
        if total_locations > 0
        else 0
    )

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
            Total=("status", "count"),
            Green=(
                "status",
                lambda x: x.str.contains("Green", na=False).sum(),
            ),
            Red=(
                "status",
                lambda x: x.str.contains("Red", na=False).sum(),
            ),
        )
        .reset_index()
    )
    door_summary["Green Rate"] = (
        door_summary["Green"] / door_summary["Total"] * 100
    ).round(1)
    st.dataframe(
        door_summary, use_container_width=True, hide_index=True
    )

    # ── Issue Flags Summary ──────────────────────────────────
    st.subheader("🚩 Issue Flags")
    issue_cols = {
        "mix": "Mix/Match",
        "pvm": "PVM Issue",
        "lbl": "Label Problem",
        "qr_issue": "QR Issue",
    }
    issue_counts = {}
    for col, label in issue_cols.items():
        if col in df.columns:
            issue_counts[label] = int(df[col].sum())
    if issue_counts:
        ic1, ic2, ic3, ic4 = st.columns(4)
        cols = [ic1, ic2, ic3, ic4]
        for i, (label, count) in enumerate(issue_counts.items()):
            cols[i].metric(label, count)

    # ── Detailed Table ───────────────────────────────────────
    st.subheader("📋 All Audits")
    display_cols = [
        c for c in [
            "location", "status", "period", "container",
            "mix", "pvm", "lbl", "qr_issue", "auditor", "timestamp"
        ] if c in df.columns
    ]
    st.dataframe(
        df[display_cols],
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

    # Optional filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        shift_filter = st.selectbox(
            "Filter by Shift", ["All"] + SHIFTS
        )
    with col_f2:
        auditor_filter = st.text_input(
            "Filter by Auditor (optional)",
            placeholder="Login or 'All'",
            value="All",
        )

    if st.button("🔄 Load Data", use_container_width=True):
        history = st.session_state.db.get_history(
            date_from=start_date.strftime("%Y-%m-%d"),
            date_to=end_date.strftime("%Y-%m-%d"),
            shift_filter=shift_filter if shift_filter != "All" else None,
            auditor_filter=auditor_filter if auditor_filter != "All" else None,
        )

        if history:
            df_hist = pd.DataFrame(history)

            st.success(
                f"✅ Found {len(df_hist)} audits from "
                f"{start_date.strftime('%m/%d/%Y')} to "
                f"{end_date.strftime('%m/%d/%Y')}"
            )
            st.dataframe(
                df_hist,
                use_container_width=True,
                hide_index=True,
            )

            csv = df_hist.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=(
                    f"ROC1_audits_{start_date}_{end_date}.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("📭 No audit data found for the selected filters.")

