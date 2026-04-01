import os
from datetime import datetime

import pandas as pd
import streamlit as st

# -----------------------------
# Config
# -----------------------------
DATA_FILE = "venues_merged.csv"
FEEDBACK_FILE = "community_feedback.csv"

st.set_page_config(page_title="Community Accessibility Notes", page_icon="📝", layout="wide")
st.logo("assets/logo.jpg", size="large")

st.image("assets/logo.jpg", width=280)

st.markdown("""
<style>
    .feedback-hero {
        background: linear-gradient(135deg, #ffffff 0%, #fff7f0 100%);
        padding: 1.4rem 1.4rem 1.1rem 1.4rem;
        border-radius: 18px;
        border: 1px solid #f1e2d3;
        box-shadow: 0 6px 20px rgba(40, 30, 20, 0.05);
        margin-bottom: 1rem;
    }

    .feedback-title {
        font-size: 2rem;
        font-weight: 800;
        color: #2b2f42;
        margin-bottom: 0.3rem;
    }

    .feedback-subheader {
        font-size: 1rems;
        font-weight: 700;
        color: #3b4cca;
        margin-bottom: 0.35rem;
    }

    .feedback-subtitle {
        color: #5b6477;
        font-size: 1rem;
    }

    .feedback-card {
        background: #ffffff;
        border: 1px solid #e8ecf4;
        border-radius: 16px;
        padding: 1rem 1rem 0.85rem 1rem;
        box-shadow: 0 4px 14px rgba(20, 30, 60, 0.05);
        margin-bottom: 0.9rem;
    }

    .note-tag {
        display: inline-block;
        background: #eef2ff;
        color: #3b4cca;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .guidance-box {
        background: #f8fafc;
        border: 1px dashed #d3dae6;
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-bottom: 1rem;
        color: #475569;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_venues():
    df = pd.read_csv(DATA_FILE)
    return df


def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        return pd.read_csv(FEEDBACK_FILE)
    return pd.DataFrame(columns=["venue_id", "venue_name", "feedback_tag", "comment", "timestamp"])


def save_feedback_note(venue_id, venue_name, feedback_tag, comment):
    new_row = pd.DataFrame([{
        "venue_id": venue_id,
        "venue_name": venue_name,
        "feedback_tag": feedback_tag,
        "comment": comment,
        "timestamp": datetime.now().isoformat()
    }])

    if os.path.exists(FEEDBACK_FILE):
        existing = pd.read_csv(FEEDBACK_FILE)
        updated = pd.concat([existing, new_row], ignore_index=True)
    else:
        updated = new_row

    updated.to_csv(FEEDBACK_FILE, index=False)


# -----------------------------
# UI
# -----------------------------
st.markdown("""
<div class="feedback-hero">
    <div class="feedback-title">📝 Knock Knock? Can I Get In</div>
    <div class="feedback-subheader">Community Accessibility Notes</div>
    <div class="feedback-subtitle">
        Share lived accessibility experience and help other users make better venue decisions.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="guidance-box">
    <strong>What to include:</strong> Share factual accessibility details from your visit, such as entrance access,
    toilet access, wheelchair space, parking, staff helpfulness, or anything that would help another user plan ahead.
</div>
""", unsafe_allow_html=True)

venues_df = load_venues()
feedback_df = load_feedback()

# Build venue dropdown labels
venues_df["venue_display"] = venues_df["name"].astype(str) + " — " + venues_df["city"].astype(str).str.title()

venue_options = venues_df[["venue_id", "name", "city", "venue_display"]].drop_duplicates().sort_values("venue_display")

selected_display = st.selectbox(
    "Choose a venue",
    venue_options["venue_display"].tolist()
)

selected_row = venue_options[venue_options["venue_display"] == selected_display].iloc[0]
selected_venue_id = selected_row["venue_id"]
selected_venue_name = selected_row["name"]

st.subheader(f"Add a note for {selected_venue_name}")

feedback_tag = st.selectbox(
    "What is your note about?",
    [
        "Entrance",
        "Toilet",
        "Seating / space",
        "Parking",
        "Staff helpfulness",
        "General experience",
    ]
)

comment = st.text_area(
    "Write your note",
    placeholder="Example: Step-free entrance, but the accessible toilet needed a staff key."
)

if st.button("Submit note"):
    if comment.strip():
        save_feedback_note(
            selected_venue_id,
            selected_venue_name,
            feedback_tag,
            comment.strip()
        )
        st.success("Your note has been saved.")
        st.cache_data.clear()
        st.rerun()
    else:
        st.warning("Please enter a note before submitting.")

st.divider()

st.subheader(f"Community notes for {selected_venue_name}")

venue_feedback = feedback_df[feedback_df["venue_id"] == selected_venue_id].copy()

if venue_feedback.empty:
    st.info("No notes yet for this venue.")
else:
    venue_feedback = venue_feedback.sort_values("timestamp", ascending=False)

    for _, row in venue_feedback.iterrows():
        st.markdown('<div class="feedback-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="note-tag">{row["feedback_tag"]}</div>', unsafe_allow_html=True)
        st.write(row["comment"])
        st.caption(f"Added on {row['timestamp']}")
        st.markdown('</div>', unsafe_allow_html=True)