import os
from datetime import datetime

import pandas as pd
import streamlit as st

from query_parser import parse_query, parse_removals, is_reset_query
from llm_preference_updater import update_preferences_with_llm

# -----------------------------
# Load data
# -----------------------------
df = pd.read_csv("venues.csv")

# Standardise text columns
for col in [
    "category",
    "area",
    "city",
    "level_entry_access",
    "sloped_access",
    "accessible_toilet",
    "wheelchair_space",
    "accessible_parking",
]:
    df[col] = df[col].astype(str).str.strip().str.lower()


# -----------------------------
# Helper functions
# -----------------------------
def passes_required_filters(
    row,
    preferred_category,
    preferred_city,
    require_level_entry,
    require_accessible_toilet,
    require_wheelchair_space,
    require_accessible_parking,
    ):
    if preferred_category is not None and row["category"] != preferred_category:
        return False

    if preferred_city is not None and row["city"] != preferred_city:
        return False

    if require_level_entry and row["level_entry_access"] != "yes":
        return False

    if require_accessible_toilet and row["accessible_toilet"] != "yes":
        return False

    if require_wheelchair_space and row["wheelchair_space"] != "yes":
        return False

    if require_accessible_parking and row["accessible_parking"] != "yes":
        return False

    return True


def score_venue(row, preferred_category, preferred_city):
    score = 0

    if preferred_category is not None:
        score += 4

    if preferred_city is not None:
        score += 4

    if row["level_entry_access"] == "yes":
        score += 5

    if row["sloped_access"] == "yes":
        score += 2

    if row["accessible_toilet"] == "yes":
        score += 5

    if row["wheelchair_space"] == "yes":
        score += 4

    if row["accessible_parking"] == "yes":
        score += 2

    return score


def explain_venue(row):
    reasons = []

    if row["level_entry_access"] == "yes":
        reasons.append("level entry access")
    if row["sloped_access"] == "yes":
        reasons.append("sloped access")
    if row["accessible_toilet"] == "yes":
        reasons.append("an accessible toilet")
    if row["wheelchair_space"] == "yes":
        reasons.append("wheelchair space")
    if row["accessible_parking"] == "yes":
        reasons.append("accessible parking")

    if not reasons:
        return f"{row['name']} was recommended based on the current search filters."

    if len(reasons) == 1:
        reason_text = reasons[0]
    else:
        reason_text = ", ".join(reasons[:-1]) + f", and {reasons[-1]}"

    return f"{row['name']} was recommended because it has {reason_text}."


def save_feedback(venue_id, venue_name, user_query, vote):
    feedback_file = "feedback.csv"

    row = {
        "venue_id": venue_id,
        "venue_name": venue_name,
        "user_query": user_query,
        "vote": vote,
        "timestamp": datetime.now().isoformat()
    }

    df_row = pd.DataFrame([row])

    if os.path.exists(feedback_file):
        df_row.to_csv(feedback_file, mode="a", header=False, index=False)
    else:
        df_row.to_csv(feedback_file, mode="w", header=True, index=False)


def get_feedback_summary(venue_id):
    feedback_file = "feedback.csv"

    if not os.path.exists(feedback_file):
        return {"up": 0, "down": 0, "status": "No feedback yet"}

    feedback_df = pd.read_csv(feedback_file)
    venue_feedback = feedback_df[feedback_df["venue_id"] == venue_id]

    up_count = len(venue_feedback[venue_feedback["vote"] == "up"])
    down_count = len(venue_feedback[venue_feedback["vote"] == "down"])
    total = up_count + down_count

    if total == 0:
        status = "No feedback yet"
    elif down_count >= 3 and down_count >= up_count:
        status = "Needs review"
    elif up_count >= 3 and up_count > down_count * 2:
        status = "High confidence"
    elif down_count > 0 and up_count > down_count:
        status = "Mostly positive"
    else:
        status = "Mixed feedback"

    return {"up": up_count, "down": down_count, "status": status}


def merge_preferences(current_prefs, new_prefs, removals=None):
    merged = current_prefs.copy()

    # Apply new positive/additive updates
    for key, value in new_prefs.items():
        if value is not None and value is not False:
            merged[key] = value

    # Apply removals / relaxations
    if removals:
        for key, value in removals.items():
            if value is False:
                merged[key] = False

    return merged


def format_preferences_for_humans(prefs):
    category = prefs.get("preferred_category")
    city = prefs.get("preferred_city")

    if category == "cafe":
        base = "cafés"
    elif category == "restaurant":
        base = "restaurants"
    else:
        base = "venues"

    if city:
        base = f"{base} in {city.title()}"

    requirements = []
    if prefs.get("require_level_entry"):
        requirements.append("level access")
    if prefs.get("require_accessible_toilet"):
        requirements.append("an accessible toilet")
    if prefs.get("require_wheelchair_space"):
        requirements.append("wheelchair space")
    if prefs.get("require_accessible_parking"):
        requirements.append("accessible parking")

    if not requirements:
        return base

    if len(requirements) == 1:
        req_text = requirements[0]
    else:
        req_text = ", ".join(requirements[:-1]) + f" and {requirements[-1]}"

    return f"{base} with {req_text}"


def get_feature_badges(row):
    badges = []

    if row["level_entry_access"] == "yes":
        badges.append("✅ Level access")

    if row["sloped_access"] == "yes":
        badges.append("⛰️ Sloped access")

    if row["accessible_toilet"] == "yes":
        badges.append("🚻 Accessible toilet")

    if row["wheelchair_space"] == "yes":
        badges.append("♿ Wheelchair space")

    if row["accessible_parking"] == "yes":
        badges.append("🅿️ Accessible parking")

    return badges


def reset_preferences():
    return {
        "preferred_category": None,
        "preferred_city": None,
        "require_level_entry": False,
        "require_accessible_toilet": False,
        "require_wheelchair_space": False,
        "require_accessible_parking": False,
    }


def normalize_preferences(prefs):
    normalized = prefs.copy()

    # Normalize category
    category = normalized.get("preferred_category")
    if category is not None:
        category = str(category).strip().lower()

        if category in ["restaurant", "restaurants"]:
            category = "restaurant"
        elif category in ["cafe", "cafes", "café", "cafés", "coffee shop", "coffee shops"]:
            category = "cafe"

        normalized["preferred_category"] = category

    # Normalize city
    city = normalized.get("preferred_city")
    if city is not None:
        city = str(city).strip().lower().rstrip(".")
        normalized["preferred_city"] = city

    return normalized


def get_updated_preferences(user_message, current_preferences):
    """
    Hybrid preference updater:
    1. Try OpenRouter LLM updater
    2. If it fails, fall back to rule-based parser
    """
    try:
        llm_result = update_preferences_with_llm(user_message, current_preferences)

        required_keys = {
            "preferred_category",
            "preferred_city",
            "require_level_entry",
            "require_accessible_toilet",
            "require_wheelchair_space",
            "require_accessible_parking",
            "action",
        }

        if not isinstance(llm_result, dict):
            raise ValueError("LLM output was not a dictionary.")

        if not required_keys.issubset(llm_result.keys()):
            raise ValueError("LLM output missing required keys.")

        action = llm_result.get("action", "update_preferences")

        if action == "reset_search":
            return reset_preferences(), "I've reset your search preferences. You can start a new search now.", "llm"

        updated_preferences = {
            "preferred_category": llm_result["preferred_category"],
            "preferred_city": llm_result["preferred_city"],
            "require_level_entry": llm_result["require_level_entry"],
            "require_accessible_toilet": llm_result["require_accessible_toilet"],
            "require_wheelchair_space": llm_result["require_wheelchair_space"],
            "require_accessible_parking": llm_result["require_accessible_parking"],
        }

        updated_preferences = normalize_preferences(updated_preferences)
        summary = format_preferences_for_humans(updated_preferences)
        return updated_preferences, f"Got it — I'm now looking for {summary}.", "llm"

    except Exception:
        # Fallback to your existing rule-based logic
        if is_reset_query(user_message):
            return reset_preferences(), "I've reset your search preferences. You can start a new search now.", "rule"

        parsed = parse_query(user_message)
        removals = parse_removals(user_message)

        updated_preferences = merge_preferences(
            current_preferences,
            parsed,
            removals
        )

        updated_preferences = normalize_preferences(updated_preferences)
        summary = format_preferences_for_humans(updated_preferences)
        return updated_preferences, f"Got it — I'm now looking for {summary}.", "rule"


# -----------------------------
# App UI
# -----------------------------
st.set_page_config(page_title="Wheelchair-Friendly Venue Assistant", page_icon="♿")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "current_preferences" not in st.session_state:
    st.session_state.current_preferences = reset_preferences()

if "voted_venues" not in st.session_state:
    st.session_state.voted_venues = set()

if "last_user_query" not in st.session_state:
    st.session_state.last_user_query = ""

if "search_active" not in st.session_state:
    st.session_state.search_active = False

st.title("♿ Wheelchair-Friendly Venue Assistant")
st.write("Find venues in London that match wheelchair accessibility needs.")

user_query = st.chat_input("Ask for a wheelchair-friendly venue...")

if user_query:
    st.session_state.last_user_query = user_query
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    updated_preferences, assistant_message, update_source = get_updated_preferences(
        user_query,
        st.session_state.current_preferences
    )

    st.session_state.current_preferences = updated_preferences

    if assistant_message.startswith("I've reset your search preferences. You can start a new search now."):
        st.session_state.search_active = False
    else:
        st.session_state.search_active = True

    st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
if st.session_state.chat_history:
    st.subheader("Conversation")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

with st.expander("View current search preferences"):
    st.json(st.session_state.current_preferences)

current_prefs = st.session_state.current_preferences

preferred_category = current_prefs["preferred_category"]
preferred_city = current_prefs["preferred_city"]
require_level_entry = current_prefs["require_level_entry"]
require_accessible_toilet = current_prefs["require_accessible_toilet"]
require_wheelchair_space = current_prefs["require_wheelchair_space"]
require_accessible_parking = current_prefs["require_accessible_parking"]

# Only show recommendations once the user has started interacting
if st.session_state.search_active:
    st.write(f"**Currently searching for:** {format_preferences_for_humans(current_prefs)}")

    filtered = df[df.apply(
        lambda row: passes_required_filters(
            row,
            preferred_category,
            preferred_city,
            require_level_entry,
            require_accessible_toilet,
            require_wheelchair_space,
            require_accessible_parking,
        ),
        axis=1
    )].copy()

    if filtered.empty:
        st.warning("No venues matched the required filters.")
    else:
        filtered["score"] = filtered.apply(
            lambda row: score_venue(row, preferred_category, preferred_city),
            axis=1
        )
        ranked = filtered.sort_values(by="score", ascending=False)

        st.subheader("Recommended venues")
        for _, row in ranked.head(5).iterrows():
            with st.container():
                st.markdown(f"### {row['name']}")
                st.write(f"**Category:** {row['category'].title()}")
                st.write(f"**Area:** {row['area'].title()}, {row['city'].title()}")
                st.write(f"**Score:** {row['score']}")

                badges = get_feature_badges(row)
                if badges:
                    st.write(" | ".join(badges))

                st.write(explain_venue(row))

                feedback_summary = get_feedback_summary(row["venue_id"])
                st.write(
                    f"**Feedback:** 👍 {feedback_summary['up']} | 👎 {feedback_summary['down']} | "
                    f"**Status:** {feedback_summary['status']}"
                )

                vote_key = str(row["venue_id"])

                if vote_key in st.session_state.voted_venues:
                    st.info("You already voted on this venue in this session.")
                else:
                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("👍 Helpful", key=f"up_{row['venue_id']}"):
                            save_feedback(
                                row["venue_id"],
                                row["name"],
                                st.session_state.last_user_query,
                                "up"
                            )
                            st.session_state.voted_venues.add(vote_key)
                            st.success(f"Saved positive feedback for {row['name']}")

                    with col2:
                        if st.button("👎 Not accurate", key=f"down_{row['venue_id']}"):
                            save_feedback(
                                row["venue_id"],
                                row["name"],
                                st.session_state.last_user_query,
                                "down"
                            )
                            st.session_state.voted_venues.add(vote_key)
                            st.warning(f"Saved negative feedback for {row['name']}")

                st.markdown("---")
else:
    st.info("Start a new search to see venue recommendations.")