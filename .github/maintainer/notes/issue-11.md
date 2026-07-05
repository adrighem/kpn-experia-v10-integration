# ISSUE:11 - Integration does not relogin after session ends

URL: https://github.com/adrighem/ha-kpn-experia-v10/issues/11

Reporter: `gschot`

Created: 2026-07-04T18:06:12Z

## Intent

The reporter wants the integration to automatically renew the router session after the router's 30-minute HTTP session timeout. Their current workaround reloads the integration every 20 minutes, which makes entities temporarily unavailable and creates blocky history.

## Environment

- Home Assistant: 2026.3.4
- Router: ExperiaBox v10
- Firmware: V10.C.25.08.15

## Observed Signal

- No exact expired-session payload was provided.
- The firmware matches the family that previously exposed permission-denied edge cases in `ISSUE:8`.
- Existing code already retried HTTP 401/403 and root-level router auth errors `196621`/`196614`.
- The Domoticz Experia v10 plugin already retries router error `13` after clearing context, which likely explains why it recovers from the same router timeout.

## Decision

Priority: high for patch release. The issue limits useful data to 30-minute windows and forces a workaround that makes entities unavailable.

Action: implemented a local fix that broadens stale-session handling without making retries unbounded:

- Extract router error details from root, `status`, and `data` response objects.
- Treat known auth codes `196621` and `196614`, plus clear session/auth text markers, as session renewal triggers.
- Retry once when the router returns a non-JSON response, which covers login-page-style responses after timeout.
- Retry router error `13` for core services such as `Devices`, while preserving known optional permission-denied endpoints as partial failures.
- Reuse a cached context with an empty cookie while concurrent callers wait on the login lock, matching the existing request behavior.
- Preserve existing behavior for invalid method/API errors.

## Verification

- Added API tests for nested auth errors, non-JSON session timeout responses, core permission-denied relogin, optional permission-denied handling, and empty-cookie context reuse.
- Full local pytest suite passes: 39 tests.

## Public Action Status

No public action taken yet. Suggested owner comment is pending human approval.
