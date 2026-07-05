# Maintainer Decisions

## 2026-07-05 - Prefer NMC.Guest for guest Wi-Fi

- The Domoticz Experia v10 plugin uses `NMC.Guest` for guest Wi-Fi get/set after moving away from scanning `sah.Device.WiFi.Radio`.
- Decided the Home Assistant integration should use `NMC.Guest` as the primary guest Wi-Fi endpoint because `sah.Device.WiFi.Radio` has been fragile on firmware `V10.C.25.08.15`.
- Kept the existing `sah.Device.WiFi.Radio` UID flow as fallback for older firmware or routers that do not expose `NMC.Guest`.

## 2026-07-05 - Broaden stale-session renewal handling

- `ISSUE:11` reports that firmware `V10.C.25.08.15` stops updating after the router's 30-minute HTTP session timeout.
- No exact expired-session payload was provided, so the fix targets likely router-auth response shapes while preserving single-retry behavior.
- Decided to extract auth errors from root, `status`, and `data` objects and to retry once on non-JSON router responses, which likely represent a login page after timeout.
- Decided to reuse cached contexts with empty cookies inside the login lock, because request handling already treats an empty cookie as valid.
- Compared the Domoticz plugin and found it retries router error `13` after clearing context, which likely explains why it recovers from the timeout.
- Decided to retry error `13` for core services, but keep known optional endpoints (`Devices.Device.guest`, `NeMo.Intf.eth0`, `NMC.Wifi`) as permission-denied partial failures so the `ISSUE:8` behavior remains intact.

## 2026-06-28 - Suppress recurring device permission-denied warnings after initial load

- `ISSUE:8` received a post-release follow-up after `v3.2.2`: firmware `V10.C.25.08.15` can also deny `Devices.Device.guest` with router error `13`.
- Decided device permission-denied failures should stay fatal during initial setup/first refresh, because setup validates router access through device discovery.
- Decided recurring coordinator refreshes should preserve the previous device list and debug-log device permission denials, matching the non-fatal behavior users expect once core data is already available.

## 2026-06-27 - Handle optional endpoint permission denials

- `ISSUE:8` reports repeated warning logs on firmware `V10.C.25.08.15` when optional endpoints `NeMo.Intf.eth0` and `NMC.Wifi` return router error `13`, `Permission denied`.
- Decided to classify router error `13` as a distinct permission-denied API error.
- Decided optional permission-denied failures should be debug-level coordinator logs, not warnings, because core data can still update and warning spam repeats every polling interval.
- Kept unexpected partial failures at warning level and critical first-run failures as hard update failures.

## 2026-06-11 - Establish maintainer baseline

- Captured GitHub backlog manually because the skill's triage script is unavailable locally.
- Confirmed there are no open issues and no open pull requests.
- Recorded `ISSUE:4` as recently resolved by `PR:5`.
- Updated the current branch manifest version from `3.1.1` to `3.2.0` to avoid regressing the already-published release version if this branch is merged later.
