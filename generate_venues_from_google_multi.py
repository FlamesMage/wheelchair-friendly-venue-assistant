import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

if not GOOGLE_PLACES_API_KEY:
    raise ValueError("Missing GOOGLE_PLACES_API_KEY in .env")

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
CITIES = [
    "London",
    "Birmingham",
    "Manchester",
    "Leeds",
    "Bristol",
]

CATEGORIES = {
    "restaurant": "restaurant",
    "cafe": "cafe",
    "museum": "museum",
}

OUTPUT_FILE = "venues_google_multi.csv"
PAGE_SIZE = 10
CITY_SEARCH_RADIUS_METERS = 12000

# ---------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Wildcard  returns the full Google response shape.
PLACES_FIELD_MASK = "*"


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------
def normalize_yes_no_unknown(value):
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def normalize_app_category(place_types, fallback_label):
    """
    Convert Google place types into your simplified app categories.
    """
    if not place_types:
        return fallback_label

    lower_types = [t.lower() for t in place_types]

    if "cafe" in lower_types or "coffee_shop" in lower_types:
        return "cafe"
    if "museum" in lower_types:
        return "museum"

    return "restaurant"


def geocode_text_query(query_text):
    """
    Geocode a city string like 'London' into lat/lng for search biasing.
    """
    params = {
        "address": query_text,
        "key": GOOGLE_PLACES_API_KEY,
    }

    response = requests.get(GEOCODE_URL, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    results = data.get("results", [])
    if not results:
        return None

    loc = results[0]["geometry"]["location"]
    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "raw": results[0]
    }


def extract_lat_lng_from_place(place):
    """
    Places API (New) commonly returns coordinates inside place['location'].
    """
    loc = place.get("location", {})
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    return lat, lng


def extract_area_from_address(formatted_address):
    """
    Simple fallback area:
    use the first chunk of the formatted address before the first comma.
    This is not a true neighbourhood, but it gives a short location label.
    """
    if not formatted_address or formatted_address == "unknown":
        return "unknown"

    if "," in formatted_address:
        return formatted_address.split(",")[0].strip()

    return formatted_address.strip()


def fetch_places_for_city_and_category(city_name, included_type):
    """
    Search for places in a city with a type filter using Places API (New).
    """
    city_geocode = geocode_text_query(city_name)
    if not city_geocode:
        print(f"Could not geocode city: {city_name}")
        return []

    center_lat = city_geocode["lat"]
    center_lng = city_geocode["lng"]

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": PLACES_FIELD_MASK,
    }

    payload = {
        "textQuery": f"{included_type}s in {city_name}",
        "includedType": included_type,
        "strictTypeFiltering": True,
        "pageSize": PAGE_SIZE,
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": center_lat,
                    "longitude": center_lng
                },
                "radius": CITY_SEARCH_RADIUS_METERS
            }
        }
    }

    response = requests.post(PLACES_SEARCH_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    return data.get("places", [])


def map_place_to_row(place, venue_id, source_city, search_category):
    display_name_obj = place.get("displayName", {})
    name = display_name_obj.get("text", "unknown")

    formatted_address = place.get("formattedAddress", "unknown")
    place_types = place.get("types", [])
    app_category = normalize_app_category(place_types, search_category)

    place_id = place.get("id", "")
    rating = place.get("rating", None)
    user_ratings_total = place.get("userRatingCount", None)
    business_status = place.get("businessStatus", "unknown")

    lat, lng = extract_lat_lng_from_place(place)

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

    area = extract_area_from_address(formatted_address)

    row = {
        "venue_id": venue_id,
        "place_id": place_id,
        "name": name,
        "category": app_category,
        "search_category": search_category,
        "area": area,
        "city": source_city.lower(),
        "source_city": source_city.lower(),
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
        "lat": lat,
        "lng": lng,
        "rating": rating,
        "user_ratings_total": user_ratings_total,
        "business_status": business_status,
        "google_types": "|".join(place_types) if place_types else "",
    }

    return row


def deduplicate_rows(rows):
    """
    Deduplicate by place_id first, then by (name, address).
    """
    seen_place_ids = set()
    seen_name_address = set()
    deduped = []

    for row in rows:
        place_id = row.get("place_id")
        fallback_key = (
            str(row.get("name", "")).strip().lower(),
            str(row.get("address", "")).strip().lower(),
        )

        if place_id:
            if place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)
        else:
            if fallback_key in seen_name_address:
                continue
            seen_name_address.add(fallback_key)

        deduped.append(row)

    return deduped


def main():
    all_rows = []
    venue_id_counter = 1

    for city in CITIES:
        for app_category, google_type in CATEGORIES.items():
            print(f"Fetching {app_category}s in {city}...")
            try:
                places = fetch_places_for_city_and_category(city, google_type)
            except Exception as e:
                print(f"Error fetching {app_category}s in {city}: {e}")
                continue

            for place in places:
                row = map_place_to_row(
                    place=place,
                    venue_id=venue_id_counter,
                    source_city=city,
                    search_category=app_category,
                )
                all_rows.append(row)
                venue_id_counter += 1

    all_rows = deduplicate_rows(all_rows)

    # Reassign venue IDs after dedupe
    for i, row in enumerate(all_rows, start=1):
        row["venue_id"] = i

    df = pd.DataFrame(all_rows)

    preferred_order = [
        "venue_id",
        "place_id",
        "name",
        "category",
        "search_category",
        "area",
        "city",
        "source_city",
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
        "lat",
        "lng",
        "rating",
        "user_ratings_total",
        "business_status",
        "google_types",
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    df = df[existing_cols]

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved {len(df)} venues to {OUTPUT_FILE}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()