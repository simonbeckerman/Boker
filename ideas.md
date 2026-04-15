# Boker Ideas (Claude-First Strategy)

This document follows one rule:

**If Claude can do it well already, do not build custom code for it.**

We only code what Claude cannot reliably do on its own.

## Product Principle

- Claude should handle:
  - natural language understanding
  - follow-up questions
  - wording and final explanation
  - lightweight comparisons and summaries
- Boker server should handle:
  - fetching trusted Oref data
  - strict counting/filtering logic
  - returning clear structured JSON

## What We Should Not Build (for now)

Avoid these unless there is clear repeated failure:

- Large routing trees based on user prompt text
- Many narrow tools for each phrasing style
- Hard-coded prompt templates users must memorize
- Duplicate summarization logic already done by Claude

## What We Should Build (minimum code, high value)

### 1) One general data tool (recommended)

Create one flexible data tool as the main entry point:

- `get_alert_data`
- Inputs (all optional except a safe default):
  - `city` (single city)
  - `cities` (list for comparison)
  - `from_date`
  - `to_date`
  - `group_by` (`day` default)
- Behavior:
  - if dates are missing, default to last 7 days
  - if city is missing, return national/top-cities snapshot

This keeps server code small while giving Claude enough structure to answer many question types.

### 2) Keep existing specific tools for backward compatibility

- `get_tel_aviv_alert_count`
- `get_alerts_by_city`

Claude can still use them, but new flows should prefer the general tool.

### 3) Strong output schema (important)

Always return:

- exact normalized parameters used
- daily counts
- total counts
- metadata (`source`, `timezone`, `is_partial`)

This gives Claude consistent raw material to generate good answers without extra coding.

## Guardrails (small code, big reliability)

- Date defaulting (last 7 days)
- City normalization (English/Hebrew aliases; already partly implemented)
- Clear errors:
  - missing city when needed
  - invalid dates
  - upstream Oref unavailable
- Transparent echo of interpreted parameters in every response

## Safety-Oriented Ideas (Claude-heavy, low backend effort)

These can mostly be prompt-level behavior with existing data:

- "Calm brief" mode: short, plain summary with no jargon
- Family watchlist summary (if user provides city list)
- "Is it quieter now?" trend sentence (based on simple period comparison)
- Confidence note when data is sparse or upstream uncertain

## Build Order (best ROI)

1. Introduce `get_alert_data` with defaults
2. Keep existing tools; document preferred usage
3. Add basic period comparison helper in output (optional fields)
4. Only then consider extra tools (leaderboard, compare, recap) if needed

## Success Criteria

We are successful when:

- Users ask naturally in plain language
- Claude answers correctly without users memorizing prompts
- Backend remains small, testable, and easy to maintain
- New feature requests mostly require prompt/design changes, not heavy backend rewrites
