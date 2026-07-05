# Maintainer Patterns

## Router API support

- Real router responses can vary by firmware state. Preserve tests around API error handling and add fixtures for every newly observed router response shape.
- Firmware `V10.C.25.08.15` can deny optional `NeMo.Intf.eth0` traffic stats and `NMC.Wifi` status calls with application error `13`; avoid warning spam when core data still updates.
- Firmware `V10.C.25.08.15` can also deny `Devices.Device.guest` with application error `13`; after first data is available, preserve the last device list and avoid warning spam.
- Firmware `V10.C.25.08.15` also has a 30-minute router HTTP session timeout; stale-session handling should renew context from multiple auth response shapes, including core-service error `13`, and should include tests for each observed shape.
- Around session renewal, the router can briefly report placeholder zero values for uptime and traffic counters even though the session recovers. Preserve previous nonzero values for those fields to avoid history dips.
- Prefer `NMC.Guest` for guest Wi-Fi get/set, with `sah.Device.WiFi.Radio` as fallback.

## Release hygiene

- After release-please merges a release PR, feature branches created before the release can carry stale `manifest.json` versions. Check branch manifests before merging follow-up fixes.

## Validation

- Minimum local verification for code changes: run the CI-style pytest command from `.github/workflows/tests.yml`.
- HACS and hassfest results should be checked through GitHub Actions before release.
