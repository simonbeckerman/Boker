# Oref MCP Backlog (when development resumes)

This file stores future work ideas while active development is paused.

Current priority is keeping the existing service stable for daily Claude siren queries.

## Next best items (small and high value)

1. Add one general tool (`get_alert_data`) as the main entry point.
2. Keep current specific tools for compatibility (`get_tel_aviv_alert_count`, `get_alerts_by_city`).
3. Return a stronger, consistent output schema in every response:
   - normalized parameters used
   - daily counts
   - total count
   - metadata (`source`, `timezone`, `is_partial`)
4. Improve guardrails:
   - better invalid-date errors
   - clear upstream Oref failure messages
   - transparent echo of interpreted parameters
5. Optional helper field for simple period comparison ("quieter or louder than previous period").

## Nice-to-have later (only if needed)

- Calm brief mode (short, plain-language summary).
- Family watchlist summary (user-provided city list).
- Better confidence note when data is sparse or upstream is unstable.

## Source notes

- Based on existing project notes in `../ideas.md`.
- Keep this list short; pick one item at a time when resuming.
