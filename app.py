
# ============================================================
# ROC1 Stage Audit — Full Redesign
# Developed by: luisdiel
# Powered by Amazon Quick
# Repository: github.com/luisdiel/roc1-stage-audit
# ============================================================

import pytz
import streamlit as st
import pandas as pd
from datetime import datetime, date
from datetime import time as dtime
from locations import LOC_AREA, ALL_LOCATIONS, AREAS, TT_BASE, PAIRS
from qr_map import load_qr_map, resolve_scan, learn_uuid
from database import get_database

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ROC1 Stage Audit",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS (ROC1 Lions theme — dark + cyan/teal) ────────────────────────
st.markdown("""
<style>
    /* ─── Base dark theme ─── */
    .stApp {
        background-color: #0a0e17;
        color: #eaf0fa;
    }

    /* ─── Stat cards ─── */
    .stat-card {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .stat-number {
        font-size: 28px;
        font-weight: 800;
        font-family: 'SF Mono', Consolas, monospace;
    }
    .stat-label {
        font-size: 11px;
        color: #7dd3fc;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ─── Status colors ─── */
    .status-green { color: #22c55e; }
    .status-yellow { color: #facc15; }
    .status-red { color: #ef4444; }
    .status-empty { color: #64748b; }

    /* ─── Flag colors ─── */
    .flag-mix { color: #f59e0b; }
    .flag-pvm { color: #818cf8; }
    .flag-lbl { color: #ec4899; }
    .flag-qr { color: #f43f5e; }

    /* ─── Claim badges ─── */
    .claim-badge {
        background: #0891b2;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }
    .claimed-other {
        background: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }

    /* ─── Sidebar dark theme ─── */
    section[data-testid="stSidebar"] {
        background-color: #0d1321 !important;
        border-right: 1px solid #1e3a5f;
    }
    section[data-testid="stSidebar"] * {
        color: #eaf0fa !important;
    }
    section[data-testid="stSidebar"] .stRadio label span {
        color: #7dd3fc !important;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #111827 !important;
        border-color: #1e3a5f !important;
    }

    /* ─── Inputs dark ─── */
    input, .stTextInput input, .stSelectbox > div > div {
        background-color: #111827 !important;
        border: 2px solid #1e3a5f !important;
        color: #eaf0fa !important;
        border-radius: 10px !important;
    }
    input:focus, .stTextInput input:focus {
        border-color: #06b6d4 !important;
    }

    /* ─── Metric cards ─── */
    div[data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 12px;
    }
    div[data-testid="stMetric"] label {
        color: #7dd3fc !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #eaf0fa !important;
        font-family: 'SF Mono', Consolas, monospace !important;
    }

    /* ─── Primary buttons (cyan/teal) ─── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #06b6d4, #0891b2) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 12px 16px !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0891b2, #0e7490) !important;
    }

    /* ─── Secondary buttons ─── */
    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {
        background: #334155 !important;
        color: white !important;
        border: 1px solid #475569 !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 12px 16px !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {
        background: #475569 !important;
    }

    /* ─── Tabs ─── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0d1321;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #7dd3fc !important;
    }
    .stTabs [aria-selected="true"] {
        color: #06b6d4 !important;
        border-bottom-color: #06b6d4 !important;
    }

    /* ─── Progress bar (cyan gradient) ─── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #06b6d4, #22c55e) !important;
    }

    /* ─── Header area ─── */
    header[data-testid="stHeader"] {
        background-color: #0a0e17 !important;
    }

    /* ─── Dataframe/tables ─── */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
EASTERN = pytz.timezone("America/New_York")
SHIFTS = ["FHD", "FHN", "BHD", "BHN"]
STATUS_OPTIONS = ["Green ✅", "Yellow ⚠️", "Red ❌"]
PERIODS = ["P1", "P2", "P3"]

# ─── Initialize Database ─────────────────────────────────────────────────────
@st.cache_resource
def init_db():
    return get_database()

db = init_db()

# ─── Load QR Map ─────────────────────────────────────────────────────────────
if "qr_map" not in st.session_state:
    st.session_state.qr_map = load_qr_map()

# ─── Session State Initialization ────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "auditor_name" not in st.session_state:
    st.session_state.auditor_name = ""
if "current_location" not in st.session_state:
    st.session_state.current_location = None
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

# ─── Login Screen ────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("")
    st.markdown("")

    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        # Logo
        try:
            st.image("roc1_logo.png", width=200)
        except Exception:
            st.markdown("# 🦁")

        st.markdown("# ROC1 — Stage Audit")
        st.markdown("### Multi-User Edition")
        st.markdown("*FC AR Sortable — Rochester, NY*")
        st.markdown("---")

        name = st.text_input(
            "Your Login",
            placeholder="e.g., luisdiel or badge ID",
            label_visibility="collapsed"
        )

        if st.button("🚀 Start Auditing", type="primary", use_container_width=True):
            if name.strip():
                st.session_state.auditor_name = name.strip()
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Please enter your name or badge ID")

        st.markdown("---")
        st.info(
            "💡 Shared version — all auditors see the same data in real-time. "
            "No more duplicate areas!"
        )
        st.markdown("")
        st.caption("Developed by luisdiel · Powered by Amazon Quick")

    st.stop()

# ─── Sidebar: Session Config ─────────────────────────────────────────────────
with st.sidebar:
    # Logo in sidebar
    try:
        st.image("roc1_logo.png", width=80)
    except Exception:
        st.markdown("### 🦁")

    st.markdown(f"### 👤 {st.session_state.auditor_name}")
    st.markdown("---")

    # Shift selection
    st.markdown("**Shift**")
    shift = st.radio(
        "Shift", SHIFTS,
        horizontal=True, label_visibility="collapsed"
    )

    # Date
    audit_date = st.date_input("Audit Date", value=date.today())
    audit_date_str = audit_date.strftime("%Y-%m-%d")

    # Period
    st.markdown("**Period**")
    period = st.radio(
        "Period", PERIODS,
        horizontal=True, label_visibility="collapsed",
        key="period_radio"
    )

    st.markdown("---")

    # Area claim system
    st.markdown("### 🔒 Claim an Area")
    st.markdown("*Prevents others from auditing the same zone*")

    claims = db.get_claims(shift, audit_date_str)

    selected_area = st.selectbox(
        "Select Area to Claim",
        ["(None)"] + AREAS
    )

    if selected_area != "(None)":
        if selected_area in claims:
            claimer = claims[selected_area]["auditor"]
            if claimer == st.session_state.auditor_name:
                st.success("✅ You have this area claimed")
                if st.button("Release Area"):
                    db.release_area(
                        selected_area, shift, audit_date_str,
                        st.session_state.auditor_name
                    )
                    st.rerun()
            else:
                st.error(f"⛔ Claimed by: {claimer}")
        else:
            if st.button("🔒 Claim Area", type="primary"):
                success = db.claim_area(
                    selected_area, shift, audit_date_str,
                    st.session_state.auditor_name
                )
                if success:
                    st.success("Area claimed!")
                    st.rerun()
                else:
                    st.error("Could not claim — someone else got it first")

    # Show active claims
    if claims:
        st.markdown("**Active Claims:**")
        for area, info in claims.items():
            emoji = "🟢" if info["auditor"] == st.session_state.auditor_name else "🔴"
            st.markdown(f"{emoji} **{area}** — {info['auditor']}")

    st.markdown("---")

    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.auditor_name = ""
        st.rerun()

    st.markdown("---")
    st.caption("Developed by luisdiel")
    st.caption("Powered by Amazon Quick")
    st.caption(f"v2.0 · {datetime.now(EASTERN).strftime('%m/%d/%Y')}")

# ─── Load Audit Data ─────────────────────────────────────────────────────────
audits = db.get_audits(shift, audit_date_str)

# ─── Main Header ─────────────────────────────────────────────────────────────
st.markdown("# 🦁 ROC1 — Stage Audit")
st.markdown(
    f"**{shift}** · {audit_date_str} · **{period}** · "
    f"Auditor: **{st.session_state.auditor_name}**"
)

# ─── Progress Overview ────────────────────────────────────────────────────────
total_locations = len(ALL_LOCATIONS)
audited = len([k for k, v in audits.items() if v.get("status")])
green_count = len([k for k, v in audits.items() if "Green" in v.get("status", "")])
yellow_count = len([k for k, v in audits.items() if "Yellow" in v.get("status", "")])
red_count = len([k for k, v in audits.items() if "Red" in v.get("status", "")])
mix_count = len([k for k, v in audits.items() if v.get("mix")])
pvm_count = len([k for k, v in audits.items() if v.get("pvm")])
lbl_count = len([k for k, v in audits.items() if v.get("lbl")])
qr_count = len([k for k, v in audits.items() if v.get("qr_issue")])

progress = audited / total_locations if total_locations > 0 else 0
st.progress(progress, text=f"Progress: {audited}/{total_locations} locations ({progress*100:.1f}%)")

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
col1.metric("Audited", audited)
col2.metric("Green ✅", green_count)
col3.metric("Yellow ⚠️", yellow_count)
col4.metric("Red ❌", red_count)
col5.metric("Mix Match", mix_count)
col6.metric("PVM", pvm_count)
col7.metric("Label", lbl_count)
col8.metric("QR Fix", qr_count)

st.markdown("---")

# ─── Main Tabs ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Scan & Audit", "📊 By Area", "📋 By Period", "📈 History", "⬇️ Export"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: SCAN & AUDIT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Step 1 — Select or Scan Location")

    col_loc, col_jump = st.columns([3, 1])

    with col_loc:
        location_input = st.text_input(
            "Scan QR or type STG-ID",
            placeholder="Scan QR code or type STG-DD115-1...",
            key=f"loc_input_{st.session_state.input_counter}",
            help="Scan a location QR code (UUID auto-resolves) or type a STG-ID directly"
        )

    with col_jump:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⏭️ Next Un-audited", use_container_width=True):
            for loc in ALL_LOCATIONS:
                if loc not in audits or not audits[loc].get("status"):
                    st.session_state.current_location = loc
                    st.rerun()
                    break
            else:
                st.success("🎉 All locations audited!")

    # Resolve the input
    if location_input:
        resolved, source = resolve_scan(location_input, st.session_state.qr_map)

        if source == 'direct':
            if resolved in LOC_AREA:
                st.session_state.current_location = resolved
            else:
                st.error(f"❌ '{resolved}' is not a recognized STG location")
                st.session_state.current_location = None
        elif source == 'qr_map':
            st.session_state.current_location = resolved
            st.info(f"🔗 QR resolved → **{resolved}**")
        elif source == 'unknown':
            st.warning(f"⚠️ Unknown QR UUID: `{location_input.strip().upper()}`")
            learn_stg = st.selectbox(
                "Map this QR to which location?",
                [""] + ALL_LOCATIONS, key="learn_select"
            )
            if learn_stg and st.button("💾 Save QR Mapping", type="primary"):
                st.session_state.qr_map = learn_uuid(
                    location_input, learn_stg, st.session_state.qr_map
                )
                st.session_state.current_location = learn_stg
                st.toast(f"✅ Learned: QR → {learn_stg}")
                st.rerun()

    current_loc = st.session_state.current_location

    if current_loc and current_loc in LOC_AREA:
        area = LOC_AREA[current_loc]

        # Check if area is claimed by someone else
        if area in claims and claims[area]["auditor"] != st.session_state.auditor_name:
            st.warning(
                f"⚠️ This area ({area}) is claimed by "
                f"**{claims[area]['auditor']}**. "
                "You can still audit but coordinate to avoid duplicates."
            )

        # Show location info
        already_audited = current_loc in audits and audits[current_loc].get("status")
        status_text = (
            f" — ⚠️ Already audited ({audits[current_loc]['status']})"
            if already_audited else ""
        )

        st.success(f"📍 **{current_loc}** — {area}{status_text}")

        # Trouble Tool link
        tt_url = TT_BASE + "&searchType=Container&searchId="
        st.markdown(f"[🔎 Look up in Trouble Tool]({tt_url})")

        # QR Issue flag
        qr_flagged = current_loc in audits and audits[current_loc].get("qr_issue")
        if st.checkbox(
            "🏷️ Flag: Location QR Missing / Broken",
            value=qr_flagged, key="qr_flag"
        ):
            if not qr_flagged:
                db.flag_qr_issue(
                    current_loc, shift, audit_date_str,
                    st.session_state.auditor_name
                )
                st.toast("QR flagged for replacement!")

        st.markdown("---")
        st.markdown("### Step 2 — Status & Container")

        # Status selection (Green/Yellow/Red)
        status = st.radio(
            "Status", STATUS_OPTIONS,
            horizontal=True, key="status_radio"
        )

        container_id = st.text_input(
            "Scan / Type Container ID (optional for empty locations)",
            placeholder="Scan container barcode...",
            key=f"container_input_{st.session_state.input_counter}"
        )

        # Trouble Tool link when container is scanned
        if container_id:
            tt_container_url = TT_BASE + "&searchType=Container&searchId=" + container_id
            st.markdown(
                f"🔎 [Open Trouble Tool for **{container_id}**]({tt_container_url})"
            )

        # Flag toggles
        st.markdown("**Issue Flags:**")
        flag_cols = st.columns(4)
        with flag_cols[0]:
            mix_flag = st.checkbox(
                "🔶 MIX MATCH",
                key=f"mix_flag_{st.session_state.input_counter}"
            )
        with flag_cols[1]:
            pvm_flag = st.checkbox(
                "🟣 PVM",
                key=f"pvm_flag_{st.session_state.input_counter}"
            )
        with flag_cols[2]:
            lbl_flag = st.checkbox(
                "🩷 LABEL",
                key=f"lbl_flag_{st.session_state.input_counter}"
            )
        with flag_cols[3]:
            qr_flag_inline = st.checkbox(
                "🔴 QR ISSUE",
                key=f"qr_inline_{st.session_state.input_counter}"
            )

        # Action buttons
        st.markdown("---")
        btn_cols = st.columns(2)

        with btn_cols[0]:
            if st.button("✅ Submit Audit", type="primary", use_container_width=True):
                db.save_audit(
                    location=current_loc,
                    shift=shift,
                    audit_date=audit_date_str,
                    period=period,
                    status=status,
                    container=container_id,
                    mix=mix_flag,
                    pvm=pvm_flag,
                    lbl=lbl_flag,
                    qr_issue=qr_flag_inline or st.session_state.get("qr_flag", False),
                    auditor=st.session_state.auditor_name
                )
                flags_text = []
                if mix_flag: flags_text.append("MIX")
                if pvm_flag: flags_text.append("PVM")
                if lbl_flag: flags_text.append("LABEL")
                if qr_flag_inline: flags_text.append("QR")
                extra = f" [{'/'.join(flags_text)}]" if flags_text else ""
                st.toast(f"✅ Saved {current_loc} — {status}{extra}")
                st.session_state.current_location = None
                st.session_state.input_counter += 1
                st.rerun()

        with btn_cols[1]:
            if st.button("⏭️ Skip Location", use_container_width=True):
                st.session_state.current_location = None
                st.session_state.input_counter += 1
                st.rerun()

    elif current_loc:
        st.error(f"❌ '{current_loc}' is not a recognized location")
    else:
        st.info("👆 Scan a QR code, type a location, or click 'Next Un-audited' to start")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: BY AREA
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Progress by Area")

    area_data = []
    for area_name in AREAS:
        locs_in_area = [loc for loc in ALL_LOCATIONS if LOC_AREA[loc] == area_name]
        total = len(locs_in_area)
        aud = len([l for l in locs_in_area if l in audits and audits[l].get("status")])
        grn = len([l for l in locs_in_area if l in audits and "Green" in audits[l].get("status", "")])
        ylw = len([l for l in locs_in_area if l in audits and "Yellow" in audits[l].get("status", "")])
        red = len([l for l in locs_in_area if l in audits and "Red" in audits[l].get("status", "")])
        mx = len([l for l in locs_in_area if l in audits and audits[l].get("mix")])
        pv = len([l for l in locs_in_area if l in audits and audits[l].get("pvm")])
        lb = len([l for l in locs_in_area if l in audits and audits[l].get("lbl")])
        qr = len([l for l in locs_in_area if l in audits and audits[l].get("qr_issue")])

        claim_info = ""
        if area_name in claims:
            claim_info = claims[area_name]["auditor"]

        area_data.append({
            "Area": area_name,
            "Audited": f"{aud}/{total}",
            "Progress": f"{(aud/total*100):.0f}%" if total > 0 else "0%",
            "Green ✅": grn,
            "Yellow ⚠️": ylw,
            "Red ❌": red,
            "Mix": mx,
            "PVM": pv,
            "Label": lb,
            "QR Fix": qr,
            "Claimed By": claim_info
        })

    df_areas = pd.DataFrame(area_data)
    st.dataframe(df_areas, use_container_width=True, hide_index=True)

    # Team activity
    st.markdown("---")
    st.markdown("### 👥 Team Activity")
    auditor_counts = {}
    for loc, rec in audits.items():
        if rec.get("status") and rec.get("auditor"):
            aud_name = rec["auditor"]
            auditor_counts[aud_name] = auditor_counts.get(aud_name, 0) + 1

    if auditor_counts:
        team_data = [
            {"Auditor": name, "Locations Audited": count}
            for name, count in sorted(
                auditor_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]
        df_team = pd.DataFrame(team_data)
        st.dataframe(df_team, use_container_width=True, hide_index=True)
    else:
        st.info("No team activity yet for this shift.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: BY PERIOD
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Progress by Period")

    period_data = []
    for p in PERIODS:
        p_audits = {k: v for k, v in audits.items() if v.get("period") == p}
        period_data.append({
            "Period": p,
            "Audited": len(p_audits),
            "Green ✅": len([v for v in p_audits.values() if "Green" in v.get("status", "")]),
            "Yellow ⚠️": len([v for v in p_audits.values() if "Yellow" in v.get("status", "")]),
            "Red ❌": len([v for v in p_audits.values() if "Red" in v.get("status", "")]),
            "Mix": len([v for v in p_audits.values() if v.get("mix")]),
            "PVM": len([v for v in p_audits.values() if v.get("pvm")]),
            "QR Fix": len([v for v in p_audits.values() if v.get("qr_issue")])
        })

    # Full shift total
    period_data.append({
        "Period": "FULL SHIFT",
        "Audited": audited,
        "Green ✅": green_count,
        "Yellow ⚠️": yellow_count,
        "Red ❌": red_count,
        "Mix": mix_count,
        "PVM": pvm_count,
        "QR Fix": qr_count
    })

    df_period = pd.DataFrame(period_data)
    st.dataframe(df_period, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🕐 Recent Scans")

    recent = sorted(
        [(k, v) for k, v in audits.items() if v.get("status")],
        key=lambda x: x[1].get("timestamp", ""),
        reverse=True
    )[:15]

    if recent:
        recent_data = []
        for loc, rec in recent:
            flags = []
            if rec.get("mix"): flags.append("🔶 MIX")
            if rec.get("pvm"): flags.append("🟣 PVM")
            if rec.get("lbl"): flags.append("🩷 LABEL")
            if rec.get("qr_issue"): flags.append("🔴 QR")

            recent_data.append({
                "Location": loc,
                "Status": rec.get("status", ""),
                "Container": rec.get("container", ""),
                "Flags": " ".join(flags),
                "Auditor": rec.get("auditor", ""),
                "Time": rec.get("timestamp", "")[:19]
            })

        df_recent = pd.DataFrame(recent_data)
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("No scans recorded yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: HISTORY (NEW!)
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📈 Historical Dashboard")
    st.markdown("View audit data from previous days.")

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        hist_start = st.date_input("From", value=date.today(), key="hist_start")
    with col_h2:
        hist_end = st.date_input("To", value=date.today(), key="hist_end")

    col_h3, col_h4 = st.columns(2)
    with col_h3:
        hist_shift = st.selectbox(
            "Shift Filter", ["All"] + SHIFTS, key="hist_shift"
        )
    with col_h4:
        hist_auditor = st.text_input(
            "Auditor Filter",
            placeholder="Login or 'All'",
            value="All", key="hist_auditor"
        )

    if st.button("🔄 Load History", use_container_width=True):
        history = db.get_history(
            date_from=hist_start.strftime("%Y-%m-%d"),
            date_to=hist_end.strftime("%Y-%m-%d"),
            shift_filter=hist_shift if hist_shift != "All" else None,
            auditor_filter=hist_auditor if hist_auditor != "All" else None,
        )

        if history:
            df_hist = pd.DataFrame(history)
            st.success(
                f"✅ Found {len(df_hist)} audits from "
                f"{hist_start.strftime('%m/%d/%Y')} to "
                f"{hist_end.strftime('%m/%d/%Y')}"
            )
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No audit data found for the selected filters.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### ⬇️ Export Audit Data")

    if audits:
        export_rows = []
        for loc in ALL_LOCATIONS:
            rec = audits.get(loc, {})
            export_rows.append({
                "Location": loc,
                "Area": LOC_AREA[loc],
                "Shift": rec.get("shift", shift),
                "Audit_Date": rec.get("audit_date", audit_date_str),
                "Period": rec.get("period", ""),
                "Status": rec.get("status", ""),
                "Container_ID": rec.get("container", ""),
                "Mix_Match": "Y" if rec.get("mix") else "",
                "PVM": "Y" if rec.get("pvm") else "",
                "Label_Problem": "Y" if rec.get("lbl") else "",
                "QR_Issue": "Y" if rec.get("qr_issue") else "",
                "Auditor": rec.get("auditor", ""),
                "Timestamp": rec.get("timestamp", ""),
            })

        df_export = pd.DataFrame(export_rows)

        # Preview audited only
        df_preview = df_export[df_export["Status"] != ""]
        if not df_preview.empty:
            st.dataframe(
                df_preview.head(20),
                use_container_width=True, hide_index=True
            )

        # Download
        csv = df_export.to_csv(index=False)
        filename = f"ROC1_stage_audit_{shift}_{audit_date_str}.csv"
        st.download_button(
            "⬇️ Download Full CSV",
            csv, filename, "text/csv",
            use_container_width=True
        )

        st.markdown("---")
        st.markdown(
            f"**Summary:** {audited} of {total_locations} locations audited "
            f"({progress*100:.1f}%) | "
            f"Green: {green_count} | Yellow: {yellow_count} | Red: {red_count}"
        )
    else:
        st.info("No audit data to export yet. Start scanning!")

    st.markdown("---")
    st.markdown("### 🗑️ Clear Data")
    st.warning(
        "⚠️ This will clear ALL audit data for this shift/date. "
        "QR mappings are preserved."
    )

    confirm_clear = st.checkbox("I understand — clear all data for this shift")
    if confirm_clear:
        if st.button("🗑️ Clear All Audit Data", type="secondary"):
            if hasattr(db, 'data'):
                key = f"{audit_date_str}_{shift}"
                if key in db.data["audits"]:
                    db.data["audits"][key] = {}
                    db._save()
                    st.toast("Audit data cleared!")
                    st.rerun()
            else:
                st.error(
                    "Clear is only available in local mode. "
                    "Contact admin for Supabase data management."
                )

