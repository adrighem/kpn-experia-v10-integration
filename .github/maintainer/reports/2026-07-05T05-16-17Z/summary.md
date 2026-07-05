# Maintainer Run - 2026-07-05T05:16:17Z

Mode: Maintain -> Ship

## Capture

- Repository: `adrighem/ha-kpn-experia-v10`
- Open issues: 1
- Open pull requests: 0
- Dependabot alerts: 0
- Code scanning alerts: 0
- GitHub inbox: no unread notifications
- Latest release: `v3.2.3`, published 2026-06-28T20:51:25Z
- Recent CI: green, including scheduled hassfest run on 2026-07-05T03:58:28Z

## Top Recommendation

1. Let release-please prepare the next patch release for the `ISSUE:11` session renewal fix.
2. Ask the reporter to verify the next version without their 20-minute reload automation.
3. Clean root-level scratch artifacts before committing or releasing.

## Work Completed

- Triaged `ISSUE:11`: router session expires after the router's 30-minute timeout and integration does not recover without manual reload.
- Implemented broader stale-session detection in `custom_components/experiaboxv10/api.py`.
- Compared with `/home/vincent/src/domoticz-kpn-experia-v10`; Domoticz retries router error `13` after clearing context, so the Home Assistant fix now retries `13` only for core services.
- Aligned login-lock context reuse with existing empty-cookie request behavior to avoid redundant relogins.
- Added regression tests in `test/test_api.py`.
- Updated maintainer notes, state, backlog, decisions, patterns, contributors, and relationship index.
- Pushed fix commit 1148e94 to `master`.
- Posted the approved owner comment on `ISSUE:11`.

## Verification

- `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest test/test_api.py`: 15 passed.
- `PYTHONPATH=. uv run --with aiohttp --with voluptuous --with pytest --with pytest-asyncio pytest`: 39 passed.

## Risks

- The reporter did not provide the exact expired-session payload, so the fix covers the most likely response shapes rather than a confirmed trace.
- Error `13` can mean either expired context or a real optional endpoint permission denial. The fix retries it for core services but keeps known optional endpoint denials non-fatal to avoid regressing `ISSUE:8`.

## Public Action Status

Public action completed:

- Pushed 1148e94 to `master`.
- Commented on `ISSUE:11`: https://github.com/adrighem/ha-kpn-experia-v10/issues/11#issuecomment-4884962056
