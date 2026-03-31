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
st.title("📝 Knock-Knock! Can I Get In?")
st.subheader("Community Accessibility Notes")
st.write(
    "Share factual accessibility details based on your visit and see notes left by other users."
)

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
        with st.container():
            st.markdown(f"**{row['feedback_tag']}**")
            st.write(row["comment"])
            st.caption(f"Added on {row['timestamp']}")
            st.divider()