import os
from datetime import datetime

import pandas as pd
import streamlit as st

from query_parser import parse_query, parse_removals, is_reset_query
from llm_preference_updater import update_preferences_with_llm

# -----------------------------
# Load data
# -----------------------------
df = pd.read_csv("venues_merged.csv")

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


def format_list_nicely(items):
    items = [str(item).strip() for item in items if str(item).strip()]
    items = sorted(set(items))

    if not items:
        return ""

    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"

    return ", ".join(items[:-1]) + f", and {items[-1]}"


def detect_helper_intent(user_message):
    query = user_message.lower().strip()

    # LOCATIONS
    if any(phrase in query for phrase in [
        "what locations are available",
        "which locations are available",
        "what cities are available",
        "which cities are available",
        "what locations do you have",
        "which locations do you support",
        "what cities do you have",
        "available locations",
        "available cities",
        "locations available",
        "cities available",
        "where can i search",
        "which cities can i search",
    ]):
        return "locations"

    # CATEGORIES
    if any(phrase in query for phrase in [
        "what categories are available",
        "which categories are available",
        "what categories do you support",
        "what venues can i search for",
        "what types of venues can i search for",
        "what types of places can i search for",
        "available categories",
        "categories available",
        "what venue types are available",
        "which venue types are available",
    ]):
        return "categories"

    # HELP
    if any(phrase in query for phrase in [
        "what can you help with",
        "what can you do",
        "how can you help",
        "help",
        "show me examples",
        "what can i ask",
        "how does this work",
        "what do you do",
    ]):
        return "help"

    # ACCESSIBILITY
    if any(phrase in query for phrase in [
        "what accessibility features can i search for",
        "which accessibility features can i search for",
        "what accessibility options are available",
        "what accessibility needs can i search for",
        "what accessible features can i search for",
        "what accessible features can i search for?",
        "accessible features",
        "accessibility features",
        "what features can i search for",
        "what accessibility filters are available",
        "what accessible filters are available",
    ]):
        return "accessibility"

    return None


def detect_conversation_intent(user_message):
    query = user_message.lower().strip()

    # Greetings
    if query in ["hi", "hello", "hey", "hey there", "hello there"]:
        return "greeting"

    # Thanks / gratitude
    if query in ["thanks", "thank you", "cheers", "thanks a lot", "thank you very much"]:
        return "gratitude"

    # Goodbye / closing
    if query in ["bye", "goodbye", "see you", "see you later", "that’s all", "thats all", "done for now"]:
        return "goodbye"

    # Weather / clearly unrelated live info
    if any(phrase in query for phrase in [
    "what's the weather",
    "whats the weather",
    "weather",
    "is it raining",
    "temperature today",
    "forecast",
    ]):
        return "out_of_scope"

    # General unrelated info
    if any(phrase in query for phrase in [
    "tell me a joke",
    "who won",
    "capital of",
    "what time is it",
    "news",
    "stock price",
    "translate this",
    "write an essay",
    ]):
        return "out_of_scope"

    # Very short unclear inputs
    if query in ["?", "??", "???", ".", "..", "..."]:
        return "unclear"

    # Random-looking malformed input
    if len(query) <= 3 and query not in ["hi", "hey", "bye"]:
        return "unclear"

    if query in ["asdfgh", "qwerty", "blah", "idk"]:
        return "unclear"

    return None


def get_conversation_response(intent):
    if intent == "greeting":
        return (
            "Hi — I can help you find wheelchair-friendly venues by city, category, and accessibility need. "
            "You can ask things like 'Find me a cafe in Manchester with accessible parking.'"
        )

    if intent == "gratitude":
        return "You’re welcome — let me know if you’d like another venue suggestion or want to refine your search."

    if intent == "goodbye":
        return "No problem — feel free to come back anytime if you want help finding accessible venues."

    if intent == "out_of_scope":
        return (
            "I’m focused on helping with accessible venue search and venue-related feedback. "
            "You can ask about locations, categories, accessibility features, or request venue recommendations."
        )

    if intent == "unclear":
        return (
            "I’m not sure what you mean yet. You can ask me things like "
            "'Find me a restaurant in London with an accessible toilet' or "
            "'What locations are available?'"
        )

    return None


def detect_future_feature_intent(user_message):
    query = user_message.lower().strip()

    if any(phrase in query for phrase in [
    "near soho",
    "near camden",
    "near me",
    "near ",
    "postcode",
    "cv1",
    "distance",
    "closest venue",
    ]):
        return "proximity"

    if any(phrase in query for phrase in [
    "compare venues",
    "compare these",
    "which is better",
    "side by side",
    ]):
        return "comparison"

    return None


def get_future_feature_response(intent):
    if intent == "proximity":
        return (
            "I don’t fully support proximity or postcode-based venue search yet, "
            "but that is planned as a future improvement. For now, you can search by city, "
            "category, and accessibility need."
        )

    if intent == "comparison":
        return (
            "I don’t currently support side-by-side venue comparison, "
            "but that is a possible future improvement. For now, I can still recommend venues "
            "based on your accessibility needs."
        )

    return None



def get_helper_response(intent, df):
    if intent == "locations":
        cities = [city.title() for city in df["city"].dropna().astype(str).str.strip().str.lower().unique()]
        city_text = format_list_nicely(cities)
        return f"I currently have venues in {city_text}."

    if intent == "categories":
        categories = [cat.lower() for cat in df["category"].dropna().astype(str).str.strip().str.lower().unique()]
        category_text = format_list_nicely(categories)
        return f"I currently support these venue categories: {category_text}."

    if intent == "accessibility":
        return (
            "You can search using accessibility needs such as level access, accessible toilets, "
            "wheelchair space, and accessible parking."
        )

    if intent == "help":
        return (
            "You can ask me for venues by category, city, and accessibility need. "
            "For example: 'Find me a cafe in Manchester with accessible parking', "
            "'Show me restaurants in London with an accessible toilet', or "
            "'What locations are available?'"
        )

    return None


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
st.logo("assets/logo.jpg", size="large")

st.markdown("""
<style>
    .main {
        background-color: #f7f8fc;
    }

    .hero-card {
        background: linear-gradient(135deg, #ffffff 0%, #f2f6ff 100%);
        padding: 1.5rem 1.5rem 1.2rem 1.5rem;
        border-radius: 18px;
        border: 1px solid #e6ebf5;
        box-shadow: 0 6px 20px rgba(20, 30, 60, 0.06);
        margin-bottom: 1rem;
    }

    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #1f2a44;
        margin-bottom: 0.35rem;
        line-height: 1.15;
    }

    .hero-subtitle {
        font-size: 1rem;
        color: #4d5b7c;
        margin-bottom: 0.8rem;
    }

    .hero-tag {
        display: inline-block;
        background: #e9f2ff;
        color: #2457c5;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.45rem;
        margin-bottom: 0.45rem;
    }

    .section-card {
        background: #ffffff;
        padding: 1rem 1rem 0.75rem 1rem;
        border-radius: 16px;
        border: 1px solid #e8ecf4;
        box-shadow: 0 4px 14px rgba(20, 30, 60, 0.04);
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1f2a44;
        margin-bottom: 0.35rem;
    }

    .muted-text {
        color: #64748b;
        font-size: 0.95rem;
    }

    .example-box {
        background: #f8fafc;
        border: 1px dashed #cfd8e6;
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-top: 0.8rem;
    }

    .example-title {
        font-weight: 700;
        color: #334155;
        margin-bottom: 0.45rem;
    }

    .example-item {
        color: #475569;
        margin-bottom: 0.25rem;
        font-size: 0.95rem;
    }

    .result-card {
        background: #ffffff;
        border: 1px solid #e8ecf4;
        border-radius: 16px;
        padding: 1rem 1rem 0.75rem 1rem;
        box-shadow: 0 4px 14px rgba(20, 30, 60, 0.05);
        margin-bottom: 1rem;
    }

    .small-label {
        font-size: 0.82rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
</style>
""", unsafe_allow_html=True)


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

st.image("assets/logo.jpg", width=280)

st.markdown("""
<div class="hero-card">
    <div class="hero-title">♿ Wheelchair-Friendly Venue Assistant</div>
    <div class="hero-subtitle">
        Find venues across multiple cities based on real accessibility needs like level access,
        accessible toilets, wheelchair space, and parking.
    </div>
    <span class="hero-tag">Accessibility-first</span>
    <span class="hero-tag">Multi-city</span>
    <span class="hero-tag">Community-informed</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="example-box">
    <div class="example-title">Try asking:</div>
    <div class="example-item">• Find me a cafe in Manchester with accessible parking</div>
    <div class="example-item">• Show me restaurants in London with an accessible toilet</div>
    <div class="example-item">• What locations are available?</div>
</div>
""", unsafe_allow_html=True)


user_query = st.chat_input("Ask for a wheelchair-friendly venue...")

if user_query:
    st.session_state.last_user_query = user_query
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    helper_intent = detect_helper_intent(user_query)
    conversation_intent = detect_conversation_intent(user_query)
    future_feature_intent = detect_future_feature_intent(user_query)

    if helper_intent:
        assistant_message = get_helper_response(helper_intent, df)
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})

    elif conversation_intent:
        assistant_message = get_conversation_response(conversation_intent)
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
    
    elif future_feature_intent:
        assistant_message = get_future_feature_response(future_feature_intent)
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
    
    else:
        updated_preferences, assistant_message, update_source = get_updated_preferences(
            user_query,
            st.session_state.current_preferences
        )

        st.session_state.current_preferences = updated_preferences

        if assistant_message.startswith("I've reset"):
            st.session_state.search_active = False
        else:
            st.session_state.search_active = True

        st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})


if st.session_state.chat_history:
    st.markdown("""
    <div class="section-card">
        <div class="section-title">Conversation</div>
        <div class="muted-text">Ask for venues, refine your requirements, or ask what locations and categories are available.</div>
    </div>
    """, unsafe_allow_html=True)
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
    st.markdown(
        f"""
        <div class="section-card">
            <div class="small-label">Current search</div>
            <div class="section-title">{format_preferences_for_humans(current_prefs).capitalize()}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
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

                st.markdown('</div>', unsafe_allow_html=True)

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
    st.info("Tell me what you need and I’ll suggest accessible venues that best match your requirements.")