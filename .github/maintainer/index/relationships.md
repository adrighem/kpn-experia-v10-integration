# Relationship Index

- `ISSUE:4` -> `PR:5`: repeated `sah.Device.WiFi.Radio` errors resolved by Wi-Fi radio disabled handling.
- `PR:3` -> release `v3.2.0`: release-please PR that tagged and published the current release.
- `ISSUE:8` -> local maintainer fix: classify router error `13` and debug-log optional permission-denied endpoints.
- `ISSUE:8:C:3` -> local maintainer follow-up fix: debug-log recurring `Devices.Device.guest` permission-denied device refresh failures after previous data exists.
- `ISSUE:11` -> local maintainer fix: broaden stale-session detection and retry once after nested auth errors or non-JSON timeout responses.
- `ISSUE:11:C:3` -> local maintainer follow-up: preserve previous uptime and traffic counters when the router briefly reports zero values around reconnect.
- `ISSUE:11:C:3` -> local proactive renewal investigation: create a new context after 25 minutes to avoid the reported 30-minute timeout path.
