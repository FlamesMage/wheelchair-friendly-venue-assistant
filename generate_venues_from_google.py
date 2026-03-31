import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

if not GOOGLE_PLACES_API_KEY:
    raise ValueError("Missing GOOGLE_PLACES_API_KEY in .env")

# -----------------------------
# Config
# -----------------------------
SEARCH_QUERY = "cafes in London"
OUTPUT_FILE = "venues_google_new.csv"

# Places API (New) Text Search endpoint
SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Field mask for Places API (New)
FIELD_MASK = "*"


def normalize_category(types):
    """
    Map Google place types to your simplified schema.
    """
    if not types:
        return "restaurant"

    types = [t.lower() for t in types]

    if "cafe" in types or "coffee_shop" in types:
        return "cafe"

    return "restaurant"


def normalize_yes_no_unknown(value):
    """
    Convert Google boolean values to yes/no/unknown.
    """
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def extract_city_and_area(formatted_address):
    """
    Simple address parsing.
    City becomes london if present.
    Area is the first chunk of the formatted address as a fallback.
    """
    if not formatted_address:
        return "unknown", "unknown"

    address_lower = formatted_address.lower()
    city = "london" if "london" in address_lower else "unknown"

    area = formatted_address.split(",")[0].strip() if "," in formatted_address else "unknown"

    return city, area


def fetch_places_new(query):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    payload = {
        "textQuery": query,
        "pageSize": 20
    }

    response = requests.post(SEARCH_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    return data.get("places", [])


def map_place_to_row(place, venue_id):
    display_name_obj = place.get("displayName", {})
    name = display_name_obj.get("text", "unknown")
    formatted_address = place.get("formattedAddress", "unknown")
    types = place.get("types", [])

    category = normalize_category(types)
    city, area = extract_city_and_area(formatted_address)

    place_id = place.get("id", "")
    rating = place.get("rating", None)
    user_ratings_total = place.get("userRatingCount", None)
    business_status = place.get("businessStatus", "unknown")

    accessibility = place.get("accessibilityOptions", {})

    level_entry_access = normalize_yes_no_unknown(
        accessibility.get("wheelchairAccessibleEntrance", place.get("wheelchairAccessibleEntrance"))
    )

    accessible_toilet = normalize_yes_no_unknown(
        accessibility.get("wheelchairAccessibleRestroom", place.get("wheelchairAccessibleRestroom"))
    )

    wheelchair_space = normalize_yes_no_unknown(
        accessibility.get("wheelchairAccessibleSeating", place.get("wheelchairAccessibleSeating"))
    )

    accessible_parking = normalize_yes_no_unknown(
        accessibility.get("wheelchairAccessibleParking", place.get("wheelchairAccessibleParking"))
    )

    row = {
        "venue_id": venue_id,
        "place_id": place_id,
        "name": name,
        "category": category,
        "area": area,
        "city": city,
        "level_entry_access": level_entry_access,
        "sloped_access": "unknown",
        "accessible_toilet": accessible_toilet,
        "wheelchair_space": wheelchair_space,
        "accessible_parking": accessible_parking,
        "notes": "Imported from Google Places API (New)",
        "source_type": "api",
        "source_name": "Google Places (New)",
        "confidence_level_entry": "medium" if level_entry_access != "unknown" else "low",
        "confidence_sloped_access": "low",
        "confidence_toilet": "medium" if accessible_toilet != "unknown" else "low",
        "confidence_space": "medium" if wheelchair_space != "unknown" else "low",
        "confidence_parking": "medium" if accessible_parking != "unknown" else "low",
        "address": formatted_address,
        "rating": rating,
        "user_ratings_total": user_ratings_total,
        "business_status": business_status,
    }

    return row


def main():
    places = fetch_places_new(SEARCH_QUERY)
    
    if places:
        print("Sample place response:")
        print(places[0])


    rows = []
    for i, place in enumerate(places, start=1):
        rows.append(map_place_to_row(place, i))

    df = pd.DataFrame(rows)

    preferred_order = [
        "venue_id",
        "place_id",
        "name",
        "category",
        "area",
        "city",
        "level_entry_access",
        "sloped_access",
        "accessible_toilet",
        "wheelchair_space",
        "accessible_parking",
        "notes",
        "source_type",
        "source_name",
        "confidence_level_entry",
        "confidence_sloped_access",
        "confidence_toilet",
        "confidence_space",
        "confidence_parking",
        "address",
        "rating",
        "user_ratings_total",
        "business_status",
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    df = df[existing_cols]

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved {len(df)} venues to {OUTPUT_FILE}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()