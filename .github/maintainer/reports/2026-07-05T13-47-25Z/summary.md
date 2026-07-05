# Maintainer Run - 2026-07-05T13:47:25Z

Mode: Maintain -> Ship

## Capture

- Repository: `adrighem/ha-kpn-experia-v10`
- Open issues: 1
- Open pull requests: 0
- Dependabot alerts: 0
- Code scanning alerts: 0
- GitHub inbox: no unread notifications after `gh-helper` cleaned one low-risk notification
- Latest release: `v3.2.4`, published 2026-07-05T05:53:55Z

## Top Recommendation

1. Monitor release-please for the proactive context-renewal patch release update to `PR:13`.
2. Ask the reporter to verify that the uptime graph no longer dips around reconnect after the release is available.
3. Clean root-level scratch artifacts before any unrelated maintenance or release work.

## Work Completed

- Triaged `ISSUE:11` follow-up: the released session-renewal fix keeps the connection active, but uptime briefly drops to `0` around reconnect.
- Implemented coordinator-side preservation for transient zero uptime after prior nonzero uptime.
- Implemented traffic-counter preservation for transient all-zero counters after prior nonzero counters.
- Kept the throughput baseline unchanged while preserved traffic counters are reused.
- Added a reboot guard so all-zero traffic counters are accepted when uptime confirms a real reboot.
- Updated maintainer notes, state, backlog, decisions, patterns, contributors, and relationship index.
- Pushed follow-up fix commit a978b66 to `master`.
- Posted the approved owner comment on `ISSUE:11`.
- Investigated proactive renewal after the user follow-up and pushed 25-minute context refresh commit 04762c4.

## Verification

- `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest test/test_coordinator_entities.py`: 13 passed.
- `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest`: 46 passed.
- Proactive renewal follow-up:
  - `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest test/test_api.py`: 22 passed.
  - `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest`: 49 passed.

## Risks

- The exact router payload around reconnect is still unknown, so the fix targets the observed symptom conservatively.
- A true reboot can briefly report uptime `0`; this fix suppresses only that zero sample when previous nonzero data exists, then accepts the next nonzero lower uptime value.
- It is not confirmed on real hardware whether creating a new context before expiry invalidates any parallel Web UI session, but the integration already uses the same create-context flow for reactive renewal.

## Public Action Status

Public action completed:

- Pushed a978b66 to `master`.
- Pushed 04762c4 to `master`.
- Commented on `ISSUE:11`: https://github.com/adrighem/ha-kpn-experia-v10/issues/11#issuecomment-4886278614
