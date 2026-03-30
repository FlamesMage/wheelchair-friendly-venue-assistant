def parse_query(user_query: str) -> dict:
    query = user_query.lower().strip()

    result = {
        "preferred_category": None,
        "preferred_city": None,
        "require_level_entry": False,
        "require_accessible_toilet": False,
        "require_wheelchair_space": False,
        "require_accessible_parking": False,
    }

    # Category
    if any(word in query for word in ["restaurant", "eat", "food", "lunch", "dinner", "meal"]):
        result["preferred_category"] = "restaurant"
    elif any(word in query for word in ["cafe", "coffee", "brunch"]):
        result["preferred_category"] = "cafe"

    # City
    if "london" in query:
        result["preferred_city"] = "london"

    # Accessibility requirements
    if any(phrase in query for phrase in ["level access", "level entry", "step free", "step-free"]):
        result["require_level_entry"] = True

    if any(phrase in query for phrase in ["accessible toilet", "wheelchair toilet", "disabled toilet", "toilet"]):
        result["require_accessible_toilet"] = True

    if any(phrase in query for phrase in ["wheelchair space", "enough space", "room for wheelchair", "space for wheelchair"]):
        result["require_wheelchair_space"] = True

    if "parking" in query:
        result["require_accessible_parking"] = True

    return result


def is_reset_query(user_query: str) -> bool:
    query = user_query.lower().strip()
    reset_phrases = [
        "start over",
        "reset",
        "reset search",
        "clear search",
        "forget that",
        "new search",
        "begin again",
        "restart"
    ]
    return any(phrase in query for phrase in reset_phrases)


def parse_removals(user_query: str) -> dict:
    query = user_query.lower().strip()

    removals = {
        "require_level_entry": None,
        "require_accessible_toilet": None,
        "require_wheelchair_space": None,
        "require_accessible_parking": None,
    }

    # Parking removal
    if any(phrase in query for phrase in [
        "don't need parking",
        "do not need parking",
        "remove parking",
        "no parking needed",
        "parking doesn't matter",
        "parking does not matter"
    ]):
        removals["require_accessible_parking"] = False

    # Accessible toilet removal
    if any(phrase in query for phrase in [
        "don't need toilet",
        "do not need toilet",
        "don't need accessible toilet",
        "do not need accessible toilet",
        "remove toilet",
        "remove accessible toilet",
        "no toilet needed",
        "toilet doesn't matter",
        "toilet does not matter"
    ]):
        removals["require_accessible_toilet"] = False

    # Wheelchair space removal
    if any(phrase in query for phrase in [
        "don't need wheelchair space",
        "do not need wheelchair space",
        "remove wheelchair space",
        "no wheelchair space needed",
        "space doesn't matter",
        "space does not matter"
    ]):
        removals["require_wheelchair_space"] = False

    # Level access removal
    if any(phrase in query for phrase in [
        "don't need level access",
        "do not need level access",
        "don't need level entry",
        "do not need level entry",
        "remove level access",
        "remove level entry",
        "step free doesn't matter",
        "step-free doesn't matter"
    ]):
        removals["require_level_entry"] = False

    return removals


if __name__ == "__main__":
    test_queries = [
        "Find me a restaurant in London with level access and an accessible toilet",
        "Show me a cafe in London with parking",
        "I don't need accessible toilet anymore",
        "Start over"
    ]

    for q in test_queries:
        print("Query:", q)
        print("Parsed additions:", parse_query(q))
        print("Parsed removals:", parse_removals(q))
        print("Is reset:", is_reset_query(q))
        print("-" * 50)