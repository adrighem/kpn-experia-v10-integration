"""DataUpdateCoordinator for ExperiaBox v10."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

import time
from .const import DOMAIN, CONF_TRACK_WIRED_DEVICES
from .api import (
    ExperiaBoxV10Api,
    ExperiaBoxV10PermissionDeniedError,
    Device,
    RouterInfo,
    WanInfo,
    TrafficInfo,
)

_LOGGER = logging.getLogger(__name__)

_PARTIAL_UPDATE_ENDPOINTS = (
    "devices",
    "router info",
    "WAN info",
    "traffic counters",
    "guest Wi-Fi status",
    "Wi-Fi status",
)
_PERMISSION_DENIED_DEBUG_ENDPOINTS = {
    "devices",
    "traffic counters",
    "guest Wi-Fi status",
    "Wi-Fi status",
}


class ExperiaBoxV10Data:
    """Class to hold ExperiaBox v10 data."""

    def __init__(
        self,
        devices: list[Device],
        router_info: RouterInfo,
        wan_info: WanInfo,
        traffic_info: TrafficInfo,
        guest_wifi_enabled: bool = False,
        wifi_enabled: bool = False,
        new_device_detected: bool = False,
        last_new_device: str | None = None,
        throughput_down: float = 0,
        throughput_up: float = 0,
    ) -> None:
        """Initialize."""
        self.devices = devices
        self.router_info = router_info
        self.wan_info = wan_info
        self.traffic_info = traffic_info
        self.guest_wifi_enabled = guest_wifi_enabled
        self.wifi_enabled = wifi_enabled
        self.new_device_detected = new_device_detected
        self.last_new_device = last_new_device
        self.throughput_down = throughput_down
        self.throughput_up = throughput_up


class ExperiaBoxV10Coordinator(DataUpdateCoordinator[ExperiaBoxV10Data]):
    """Class to manage fetching ExperiaBox v10 data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api = ExperiaBoxV10Api(
            async_get_clientsession(hass),
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )
        entry_id = getattr(entry, "entry_id", None)
        self.entry_id = (
            entry_id if isinstance(entry_id, str) and entry_id else entry.data[CONF_HOST]
        )
        self.track_wired_devices = (entry.options or {}).get(CONF_TRACK_WIRED_DEVICES, False)
        self._last_traffic_info: TrafficInfo | None = None
        self._last_traffic_time: float | None = None
        self._known_macs: set[str] | None = None
        self._last_new_device_time: float | None = None
        self._last_new_device_info: str | None = None

    @property
    def router_unique_id(self) -> str:
        """Return a stable router identifier for entity unique IDs."""
        if self.data and self.data.router_info.serial_number:
            return self.data.router_info.serial_number
        return self.entry_id

    def _calculate_throughput(self, current_time: float, current_traffic: TrafficInfo) -> tuple[float, float]:
        """Calculate download and upload throughput."""
        throughput_down = 0.0
        throughput_up = 0.0

        if self._last_traffic_info and self._last_traffic_time:
            time_delta = current_time - self._last_traffic_time
            if time_delta > 0:
                bytes_down_delta = (
                    current_traffic.bytes_received - self._last_traffic_info.bytes_received
                )
                bytes_up_delta = (
                    current_traffic.bytes_sent - self._last_traffic_info.bytes_sent
                )

                if bytes_down_delta >= 0 and bytes_up_delta >= 0:
                    throughput_down = bytes_down_delta / time_delta
                    throughput_up = bytes_up_delta / time_delta

        self._last_traffic_info = current_traffic
        self._last_traffic_time = current_time
        return throughput_down, throughput_up

    def _preserve_transient_router_info(self, router_info: RouterInfo) -> RouterInfo:
        """Preserve previous router uptime when the router briefly reports zero."""
        if (
            self.data is None
            or router_info.uptime != 0
            or self.data.router_info.uptime <= 0
        ):
            return router_info

        _LOGGER.debug("Ignoring transient zero router uptime during update")
        return router_info._replace(uptime=self.data.router_info.uptime)

    def _preserve_transient_traffic_info(
        self,
        traffic_info: TrafficInfo,
        traffic_info_current: bool,
        router_reboot_detected: bool,
    ) -> tuple[TrafficInfo, bool]:
        """Preserve previous traffic counters when the router briefly reports zeros."""
        if not traffic_info_current or self.data is None or router_reboot_detected:
            return traffic_info, traffic_info_current

        current_counters = tuple(traffic_info)
        previous_counters = tuple(self.data.traffic_info)
        if all(value == 0 for value in current_counters) and any(
            value > 0 for value in previous_counters
        ):
            _LOGGER.debug("Ignoring transient zero traffic counters during update")
            return self.data.traffic_info, False

        return traffic_info, traffic_info_current

    def _detect_new_devices(self, current_time: float, devices: list[Device]) -> bool:
        """Track devices and detect newly connected ones."""
        current_macs = {device.mac for device in devices}
        if self._known_macs is None:
            # First run, just populate known devices
            self._known_macs = current_macs
            return False
            
        new_macs = current_macs - self._known_macs
        if new_macs:
            self._known_macs.update(new_macs)
            # Find first new device to show in sensor
            for device in devices:
                if device.mac in new_macs:
                    self._last_new_device_info = f"{device.name or device.mac} ({device.mac})"
                    self._last_new_device_time = current_time
                    break

        if self._last_new_device_time:
            # Alert stays active for 5 minutes
            return current_time - self._last_new_device_time < 300
            
        return False

    def _log_partial_update_failures(self, results: list[object]) -> None:
        """Log partial update failures without warning for unavailable optional endpoints."""
        for idx, result in enumerate(results):
            if not isinstance(result, Exception):
                continue

            endpoint = (
                _PARTIAL_UPDATE_ENDPOINTS[idx]
                if idx < len(_PARTIAL_UPDATE_ENDPOINTS)
                else f"endpoint index {idx}"
            )
            if (
                endpoint in _PERMISSION_DENIED_DEBUG_ENDPOINTS
                and isinstance(result, ExperiaBoxV10PermissionDeniedError)
            ):
                _LOGGER.debug(
                    "Optional update unavailable for %s: %s",
                    endpoint,
                    result,
                )
                continue

            _LOGGER.warning("Partial update failure for %s: %s", endpoint, result)

    async def _async_update_data(self) -> ExperiaBoxV10Data:
        """Update data via library."""
        try:
            _LOGGER.debug("Fetching data from ExperiaBox v10")
            results = await asyncio.gather(
                self.api.get_devices(self.track_wired_devices),
                self.api.get_router_info(),
                self.api.get_wan_info(),
                self.api.get_traffic_info(),
                self.api.get_guest_wifi_enabled(),
                self.api.get_wifi_enabled(),
                return_exceptions=True,
            )
                        
            # Unpack results with fallback to previous data on partial failures
            # Raise exception on first run only for critical components
            if isinstance(results[0], Exception):
                if self.data is None:
                    raise results[0]
                devices = self.data.devices
            else:
                devices = results[0]
                
            if isinstance(results[1], Exception):
                if self.data is None:
                    raise results[1]
                router_info = self.data.router_info
            else:
                router_info = results[1]
                
            if isinstance(results[2], Exception):
                if self.data is None:
                    raise results[2]
                wan_info = self.data.wan_info
            else:
                wan_info = results[2]
                
            if isinstance(results[3], Exception):
                traffic_info = self.data.traffic_info if self.data else TrafficInfo(0, 0, 0, 0)
                traffic_info_current = False
            else:
                traffic_info = results[3]
                traffic_info_current = True
                
            if isinstance(results[4], Exception):
                guest_wifi_enabled = self.data.guest_wifi_enabled if self.data else False
            else:
                guest_wifi_enabled = results[4]

            if isinstance(results[5], Exception):
                wifi_enabled = self.data.wifi_enabled if self.data else False
            else:
                wifi_enabled = results[5]

            self._log_partial_update_failures(results)

            router_reboot_detected = (
                self.data is not None
                and 0 < router_info.uptime < self.data.router_info.uptime
            )
            router_info = self._preserve_transient_router_info(router_info)
            traffic_info, traffic_info_current = self._preserve_transient_traffic_info(
                traffic_info,
                traffic_info_current,
                router_reboot_detected,
            )

            _LOGGER.debug("Successfully fetched data from ExperiaBox v10")

            current_time = time.monotonic()
            if traffic_info_current:
                throughput_down, throughput_up = self._calculate_throughput(
                    current_time,
                    traffic_info,
                )
            elif self.data:
                throughput_down = self.data.throughput_down
                throughput_up = self.data.throughput_up
            else:
                throughput_down = 0.0
                throughput_up = 0.0
            new_device_detected = self._detect_new_devices(current_time, devices) if devices else False

            return ExperiaBoxV10Data(
                devices,
                router_info,
                wan_info,
                traffic_info,
                guest_wifi_enabled,
                wifi_enabled,
                new_device_detected,
                self._last_new_device_info,
                throughput_down,
                throughput_up,
            )
        except Exception as exception:
            _LOGGER.exception("Error communicating with ExperiaBox v10")
            raise UpdateFailed(
                f"Error communicating with ExperiaBox: {exception}"
            ) from exception
