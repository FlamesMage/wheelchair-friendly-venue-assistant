# Wheelchair-Friendly Venue Assistant

A conversational, accessibility-first venue recommendation app that helps users find places they can more realistically access, such as cafés, restaurants, and museums, based on needs like level access, accessible toilets, wheelchair space, and parking.

## Why this project exists

This project was inspired by a real family experience. Accessibility information is often fragmented, incomplete, or hard to trust, which means something as simple as choosing a place to go can become stressful and time-consuming. The goal of this app is to reduce that uncertainty by helping users search for venues based on wheelchair-related access needs and by being honest about what is known, unknown, or disputed.

## What the app does

The app allows a user to describe what they need in natural language, for example:

- “Find me a café in Manchester with accessible parking”
- “Show me restaurants in London with an accessible toilet”
- “What locations are available?”

The system then:

1. Interprets the request and extracts user preferences
2. Searches the venue dataset
3. Filters and ranks venues deterministically
4. Explains why venues were recommended
5. Lets users refine the search conversationally
6. Collects feedback to improve trust over time

The app also includes a second page for **Community Accessibility Notes**, where users can share factual written feedback based on their visit and see notes left by other users.

## Who it is for

This app is designed for wheelchair users and also for people planning on their behalf, such as family members, carers, or friends. It is intended to make venue selection more transparent and less frustrating.

## Core product features

### 1. Conversational venue search
Users can search for venues using natural language rather than rigid filters.

### 2. Accessibility-first recommendations
The app focuses on wheelchair-related accessibility needs such as:
- level access
- accessible toilets
- wheelchair space
- accessible parking

### 3. Multi-city, multi-category support
The current version supports multiple cities and categories, including cafés, restaurants, and museums.

### 4. Follow-up refinement
Users can refine their search through follow-up messages, for example:
- “Actually show me cafés instead”
- “I don’t need parking anymore”
- “Reset search”

### 5. Feedback and trust
Users can mark whether a recommendation was helpful or inaccurate. The app uses this feedback to show simple trust labels such as:
- No feedback yet
- High confidence
- Mostly positive
- Mixed feedback
- Needs review

### 6. Community Accessibility Notes
Users can add written notes about a venue visit, tagged by areas such as:
- Entrance
- Toilet
- Seating / space
- Parking
- Staff helpfulness
- General experience

This allows the app to combine structured data with lived experience.

## How generative AI is used

Generative AI is used to interpret user requests and conversational follow-up messages. It helps translate natural language into structured preferences such as:
- venue category
- city
- accessibility requirements
- reset intent

For example, it helps the app understand messages like:
- “Actually show me cafés instead”
- “I don’t need accessible toilet anymore”

## What is deterministic instead

The app does **not** use generative AI to invent venue facts.

Filtering, ranking, and recommendation generation are deterministic and grounded in the dataset. This was an intentional design choice so that accessibility recommendations stay reliable and explainable rather than hallucinated.

A good summary of the architecture is:

> Generative AI interprets the user’s request and follow-up messages, while deterministic logic handles filtering, ranking, and trust-related behavior.

## Architecture overview

The main components are:

- **Frontend**: Streamlit app
- **LLM / intent layer**: OpenRouter-powered conversational preference interpretation
- **Venue dataset**: merged dataset combining curated venue records and Google-generated venue discovery/enrichment
- **Deterministic matching layer**: filters and scores venues based on accessibility fields
- **Feedback layer**: stores user feedback for trust signals
- **Community notes layer**: stores written venue-specific accessibility notes


> When a user describes the kind of wheelchair-accessible venue they need, the system interprets their request, compares it against a structured venue dataset, and returns the best matching venues with explanations and simple trust signals.

## Data sources

The app currently uses a merged dataset built from:

- a manually curated accessibility-focused venue dataset
- Google Places-based venue discovery/enrichment scripts

The merged dataset preserves stronger curated accessibility values where available and supplements them with metadata such as:
- place identifiers
- coordinates
- ratings
- address details

## Community notes and trust model

The trust model in the current version is intentionally simple.

- Structured venue recommendations are based on stored accessibility data
- Users can give thumbs up / thumbs down on recommendations
- Users can also leave written community notes on a separate page

The trust label is based on the **balance** of user feedback rather than simply the presence of disagreement. That means a single negative vote does not automatically make a venue unreliable.

## What worked well

The strongest parts of the project are:

- a clear real-world problem and user motivation
- a working conversational interface
- deterministic recommendation logic
- a deployed live app
- a second page for lived-experience accessibility notes
- a scalable direction through dataset generation and merging

## Current limitations

This is still a prototype, so there are important limitations:

- accessibility data is only as good as the underlying source data
- some accessibility fields may still be `unknown`
- confidence scoring is simple rather than fully evidence-weighted
- helper and out-of-scope conversation handling is improved, but not perfect
- the location model is still mostly city-based rather than true proximity-based search
- the community notes feature is lightweight and does not yet include moderation or claim-level verification

## Future improvements

Planned future improvements include:

- **Proximity-based search** using geocoding and venue coordinates, for queries like “restaurants near Soho”
- **Postcode-based recommendations**, for example “find me cafés near CV1”
- **LLM-based intent routing** to better handle vague, typo-filled, or partial user messages
- **Claim-level feedback**, so users can vote on specific accessibility claims such as entrance or toilet access
- **“Why not shown?” explanations** when no venues match
- **Venue comparison view** for side-by-side decision support
- **Business verification / opt-in venue updates**
- **Stronger confidence scoring** based on multiple sources and user feedback
- **Moderation and review workflow** for disputed claims
- **Larger and cleaner datasets** with more automated refresh logic

## How to run locally

### 1. Clone the repository
```bash
git clone <https://github.com/FlamesMage/wheelchair-friendly-venue-assistant>
cd wheelchair-friendly-venue-assistant
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set environment variables
Create a `.env` file in the project root and add any required keys, for example:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
GOOGLE_PLACES_API_KEY=your_google_key_here
```

### 5. Run the app
```bash
streamlit run app.py
```

## Deployment

The app has been deployed through Streamlit, making it accessible via a live URL. The deployed version uses the same Streamlit interface and requires secrets such as API keys to be configured in the deployment environment.

## Repository structure

A simplified view of the project structure:

```text
app.py
pages/
community_feedback.csv
venues_merged.csv
query_parser.py
llm_preference_updater.py
score_venues.py
generate_venues_from_google.py
generate_venues_from_google_multi.py
README.md
requirements.txt
```

## Demo flow

A strong demo path for this app is:

1. Ask for an accessible venue recommendation
2. Refine the search with follow-up messages
3. Show helper responses like available locations or categories
4. Show trust labels and recommendation explanations
5. Move to the Community Accessibility Notes page
6. Add a note for a venue and show that it appears for future users

That aligns well with the original success criteria: understand the request, return a shortlist, explain the fit, show confidence, and allow user feedback so the assistant becomes more trustworthy over time.

## What I would do next

If I had more time, the next improvements I would prioritise are:

1. geocoded proximity search
2. postcode-based recommendations
3. claim-level feedback
4. better confidence scoring
5. richer data validation and moderation

## Final note

This project is not trying to solve accessibility perfectly. It is trying to make venue search more trustworthy, more transparent, and more useful for wheelchair users and the people planning on their behalf. The aim is to combine structured accessibility data, conversational search, and lived user experience in a way that is practical, explainable, and demonstrable.
