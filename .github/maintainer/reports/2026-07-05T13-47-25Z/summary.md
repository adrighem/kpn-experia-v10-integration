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

1. Push the local `ISSUE:11` follow-up fix and let release-please prepare the next patch release.
2. Ask the reporter to verify that the uptime graph no longer dips around reconnect.
3. Clean root-level scratch artifacts before any unrelated maintenance or release work.

## Work Completed

- Triaged `ISSUE:11` follow-up: the released session-renewal fix keeps the connection active, but uptime briefly drops to `0` around reconnect.
- Implemented coordinator-side preservation for transient zero uptime after prior nonzero uptime.
- Implemented traffic-counter preservation for transient all-zero counters after prior nonzero counters.
- Kept the throughput baseline unchanged while preserved traffic counters are reused.
- Added a reboot guard so all-zero traffic counters are accepted when uptime confirms a real reboot.
- Updated maintainer notes, state, backlog, decisions, patterns, contributors, and relationship index.

## Verification

- `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest test/test_coordinator_entities.py`: 13 passed.
- `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest`: 46 passed.

## Risks

- The exact router payload around reconnect is still unknown, so the fix targets the observed symptom conservatively.
- A true reboot can briefly report uptime `0`; this fix suppresses only that zero sample when previous nonzero data exists, then accepts the next nonzero lower uptime value.

## Public Action Status

- No public GitHub action taken for this follow-up.
