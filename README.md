Project title

Wheelchair-Friendly Venue Assistant


What it is

This project is a conversational accessibility-first venue recommendation tool. It helps users search for venues that match wheelchair-related access needs and explains why each recommendation was made. The goal is to reduce the uncertainty and effort involved in checking whether a venue is actually suitable.


Who it is for

The main users are wheelchair users and also people planning on their behalf, such as family members, carers, or friends. The project is based on a real problem: accessibility information is often unclear enough that people sometimes need to call venues directly to confirm basic details.


Problem it solves

Many venue platforms focus on popularity, distance, or general reviews, but not on whether a place is genuinely suitable for a wheelchair user. Accessibility information is often fragmented, vague, or hard to trust. This project tries to make that process easier by:

focusing on wheelchair-related accessibility needs first
explaining why a venue matches
allowing users to provide feedback on recommendations
showing a trust label based on feedback history


Where AI is used

AI is used to interpret conversational follow-up messages and update the user’s search state. This allows the assistant to handle natural language changes such as:

adding a requirement
removing a requirement
changing venue type
resetting the search


Where deterministic logic is used

The actual recommendation logic is deterministic. Venue filtering and ranking are based on structured accessibility fields from the dataset, such as:

level entry access
sloped access
accessible toilet
wheelchair space
accessible parking

This design was chosen so that the assistant does not hallucinate accessibility facts. Recommendations remain grounded in the data. That hybrid architecture is one of the project’s key design choices.


Feedback and trust

Users can give positive or negative feedback on a recommendation. This feedback is stored and used to generate a simple trust label, such as:

No feedback yet
High confidence
Mostly positive
Mixed feedback
Needs review

A key design principle is that the trust label is based on the balance of user feedback rather than just the presence of disagreement, so one isolated negative vote does not unfairly mark a venue as mixed or unreliable.


Why this design was chosen

The project uses a hybrid approach:

OpenRouter / LLM for conversational preference updates
Deterministic logic for filtering and ranking
Feedback loop for improving trust over time

This balances flexibility, explainability, and reliability. It also supports the main capstone goal of building something useful, demonstrable, and grounded in a real user need.

Current scope

This prototype uses a curated venue dataset and focuses on a small, controlled recommendation workflow rather than trying to cover every venue everywhere. That choice was intentional so the system could be built reliably and demonstrated clearly within the capstone timeframe.

Where AI is used

AI is used to interpret conversational follow-up messages and update the user’s search state. This allows the assistant to handle natural language changes such as:

adding a requirement
removing a requirement
changing venue type
resetting the search
Where deterministic logic is used

The actual recommendation logic is deterministic. Venue filtering and ranking are based on structured accessibility fields from the dataset, such as:

level entry access
sloped access
accessible toilet
wheelchair space
accessible parking

This design was chosen so that the assistant does not hallucinate accessibility facts. Recommendations remain grounded in the data. That hybrid architecture is one of the project’s key design choices.

Feedback and trust

Users can give positive or negative feedback on a recommendation. This feedback is stored and used to generate a simple trust label, such as:

No feedback yet
High confidence
Mostly positive
Mixed feedback
Needs review

A key design principle is that the trust label is based on the balance of user feedback rather than just the presence of disagreement, so one isolated negative vote does not unfairly mark a venue as mixed or unreliable.

Why this design was chosen

The project uses a hybrid approach:

OpenRouter / LLM for conversational preference updates
Deterministic logic for filtering and ranking
Feedback loop for improving trust over time

This balances flexibility, explainability, and reliability. It also supports the main capstone goal of building something useful, demonstrable, and grounded in a real user need.

Current scope

This prototype uses a curated venue dataset and focuses on a small, controlled recommendation workflow rather than trying to cover every venue everywhere. That choice was intentional so the system could be built reliably and demonstrated clearly within the capstone timeframe.


Current limitations
the venue dataset is small and curated
the accessibility data depends on the quality of the underlying source data
trust labels are simple and based on basic feedback counts
the system is currently better suited to demonstration than large-scale production use
Future improvements
larger and more diverse venue dataset
richer accessibility attributes
claim-level feedback instead of only venue-level feedback
map/location support
stronger business participation for verified accessibility details
improved moderation/review workflow for disputed claims