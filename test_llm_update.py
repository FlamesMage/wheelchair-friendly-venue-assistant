from llm_preference_updater import update_preferences_with_llm

current_preferences = {
    "preferred_category": "cafe",
    "preferred_city": "london",
    "require_level_entry": False,
    "require_accessible_toilet": True,
    "require_wheelchair_space": False,
    "require_accessible_parking": True,
}

user_message = "I don't need accessible toilet anymore"

updated = update_preferences_with_llm(user_message, current_preferences)
print(updated)