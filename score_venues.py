import pandas as pd
from query_parser import parse_query

# Load the venue data
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

user_query = "I need somewhere in London with wheelchair space and an accessible toilet"

parsed = parse_query(user_query)

preferred_category = parsed["preferred_category"]
preferred_city = parsed["preferred_city"]
require_level_entry = parsed["require_level_entry"]
require_accessible_toilet = parsed["require_accessible_toilet"]
require_wheelchair_space = parsed["require_wheelchair_space"]
require_accessible_parking = parsed["require_accessible_parking"]

print("\nParsed query:")
print(parsed)

def passes_required_filters(row):
    if preferred_category is not None and row["category"] != preferred_category:
        return False

    if row["city"] != preferred_city:
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

def score_venue(row):
    score = 0

    # Base match scoring
    if preferred_category is not None:
        score += 4  # category already matched
    score += 4  # city already matched

    # Accessibility scoring
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

    reason_text = ", ".join(reasons)

    return f'{row["name"]} was recommended because it has {reason_text}.'

filtered = df[df.apply(passes_required_filters, axis=1)].copy()

if filtered.empty:
    print("\nNo venues matched the required filters.")
else:
    filtered["score"] = filtered.apply(score_venue, axis=1)
    ranked = filtered.sort_values(by="score", ascending=False)

    print("\nTop venue matches after required filtering:\n")

    for _, row in ranked.head(5).iterrows():
        print(f"Name: {row['name']}")
        print(f"Category: {row['category']}")
        print(f"City: {row['city']}")
        print(f"Area: {row['area']}")
        print(f"Score: {row['score']}")
        print(f"Explanation: {explain_venue(row)}")
        print("-" * 50)