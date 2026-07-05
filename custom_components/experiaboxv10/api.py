"""API for ExperiaBox v10."""

from __future__ import annotations

from collections import namedtuple
import asyncio
import logging
from json import JSONDecodeError
from typing import Any
from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

Device = namedtuple("Device", ["mac", "name", "ip", "active"])
RouterInfo = namedtuple(
    "RouterInfo", ["model", "hardware_version", "software_version", "serial_number", "uptime"]
)
WanInfo = namedtuple("WanInfo", ["external_ip", "connected", "link_status"])
TrafficInfo = namedtuple(
    "TrafficInfo", ["bytes_sent", "bytes_received", "packets_sent", "packets_received"]
)

_AUTH_ERROR_CODES = {"196621", "196614"}
_AUTH_ERROR_TEXT_MARKERS = (
    "invalid session",
    "session expired",
    "session timeout",
    "not authenticated",
    "authentication",
)
_OPTIONAL_PERMISSION_DENIED_SERVICES = {
    "Devices.Device.guest",
    "NeMo.Intf.eth0",
    "NMC.Wifi",
}


class ExperiaBoxV10ApiError(Exception):
    """Base exception for router API errors."""


class ExperiaBoxV10AuthenticationError(ExperiaBoxV10ApiError):
    """Raised when router authentication fails after retry."""


class ExperiaBoxV10PermissionDeniedError(ExperiaBoxV10ApiError):
    """Raised when the router denies access to a specific API endpoint."""


class ExperiaBoxV10Api:
    """API for ExperiaBox v10."""

    def __init__(
        self, session: ClientSession, host: str, username: str, password: str
    ) -> None:
        """Initialize."""
        self._session = session
        self._host = host
        self._username = username
        self._password = password
        self._context_id: str | None = None
        self._cookie: str | None = None
        self._user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self._login_lock = asyncio.Lock()

    def _clear_context(self) -> None:
        """Clear cached router login context."""
        self._context_id = None
        self._cookie = None

    def _extract_error_details(self, data: dict[str, Any]) -> tuple[str | None, str]:
        """Extract router error code and text from known response shapes."""
        details: list[Any] = [data]

        for key in ("status", "data"):
            value = data.get(key)
            if isinstance(value, dict):
                details.append(value)

        for detail in details:
            if not isinstance(detail, dict):
                continue

            error_code = detail.get("error")
            error_text_parts = [
                str(detail.get(key, ""))
                for key in ("description", "info", "message", "reason")
            ]

            errors = detail.get("errors")
            if isinstance(errors, list) and errors:
                first_error = errors[0]
                if isinstance(first_error, dict):
                    error_code = first_error.get("error", error_code)
                    error_text_parts.extend(
                        str(first_error.get(key, ""))
                        for key in ("description", "info", "message", "reason")
                    )

            if error_code is not None:
                return str(error_code), " ".join(error_text_parts).lower()

        return None, ""

    def _is_auth_error(self, error_code: str | None, error_text: str) -> bool:
        """Return true when a router error should trigger session renewal."""
        if error_code in _AUTH_ERROR_CODES:
            return True

        return bool(error_text) and any(
            marker in error_text for marker in _AUTH_ERROR_TEXT_MARKERS
        )

    def _should_retry_permission_denied(self, service: str) -> bool:
        """Return true when permission denied likely means the context expired."""
        return service not in _OPTIONAL_PERMISSION_DENIED_SERVICES

    async def _retry_after_auth_error(
        self,
        service: str,
        method: str,
        parameters: dict | None,
        endpoint: str,
        retry_on_auth_error: bool,
        error_message: str,
    ) -> dict[str, Any]:
        """Clear cached login data and retry once after an auth failure."""
        self._clear_context()
        if retry_on_auth_error:
            return await self._request(
                service,
                method,
                parameters,
                endpoint,
                retry_on_auth_error=False,
            )
        raise ExperiaBoxV10AuthenticationError(error_message)

    async def _get_context(self) -> tuple[str, str]:
        """Get context ID and cookie for the JSON API."""
        async with self._login_lock:
            # Check if another task already got the context while we were waiting
            if self._context_id and self._cookie is not None:
                return self._context_id, self._cookie
                
            from aiohttp import ClientTimeout

            login_url = f"http://{self._host}/ws"
            login_payload = {
                "service": "sah.Device.Information",
                "method": "createContext",
                "parameters": {
                    "applicationName": "webui",
                    "username": self._username.lower(),
                    "password": self._password,
                },
            }
            headers = {
                "Content-Type": "application/x-sah-ws-4-call+json",
                "Authorization": "X-Sah-Login",
                "User-Agent": self._user_agent,
            }

            _LOGGER.debug("Attempting to get context from %s", login_url)
            timeout = ClientTimeout(total=5)
            try:
                async with self._session.post(
                    login_url, json=login_payload, headers=headers, timeout=timeout
                ) as resp:
                    response_headers = resp.headers
                    # If /ws fails, fallback to lan:getMIBs for older firmware
                    if resp.status != 200:
                        _LOGGER.debug("Login to /ws failed, trying fallback")
                        login_url = f"http://{self._host}/ws/NeMo/Intf/lan:getMIBs"
                        async with self._session.post(
                            login_url, json=login_payload, headers=headers, timeout=timeout
                        ) as resp_fb:
                            resp_fb.raise_for_status()
                            data = await resp_fb.json(content_type=None)
                            response_headers = resp_fb.headers
                    else:
                        data = await resp.json(content_type=None)

                try:
                    # The response could have "data" or "status" depending on firmware versions
                    if "data" in data and "contextID" in data["data"]:
                        self._context_id = data["data"]["contextID"]
                    elif "status" in data and isinstance(data["status"], dict) and "contextID" in data["status"]:
                        self._context_id = data["status"]["contextID"]
                    else:
                        _LOGGER.error("Failed to parse contextID. Raw response: %s", data)
                        raise KeyError("contextID not found in response")
                        
                    cookie_header = response_headers.get("set-cookie", "")
                    self._cookie = cookie_header.split(";")[0] if cookie_header else ""
                    return self._context_id, self._cookie
                except KeyError as err:
                    _LOGGER.error("Context key error: %s, raw response: %s", err, data)
                    raise
            except Exception as err:
                _LOGGER.debug("Failed to get context: %s", err)
                raise

    async def _request(
        self,
        service: str,
        method: str,
        parameters: dict | None = None,
        endpoint: str = "ws/NeMo/Intf/lan:getMIBs",
        retry_on_auth_error: bool = True,
    ) -> dict[str, Any]:
        """Make a request to the router API."""
        if not self._context_id or self._cookie is None:
            await self._get_context()

        # Only override default if it's the standard gateway and we know these services need root /ws
        if endpoint == "ws/NeMo/Intf/lan:getMIBs" and service in ("sah.Device.Information", "DeviceInfo", "sah.Device.WiFi.Radio"):
            endpoint = "ws"

        url = f"http://{self._host}/{endpoint}"
        headers = {
            "Content-Type": "application/x-sah-ws-4-call+json",
            "Authorization": f"X-Sah {self._context_id}",
            "X-Context": self._context_id,
            "Cookie": self._cookie,
            "User-Agent": self._user_agent,
        }
        payload = {
            "service": service,
            "method": method,
            "parameters": parameters or {},
        }
        try:
            async with self._session.post(url, headers=headers, json=payload) as resp:
                if resp.status in (401, 403):
                    return await self._retry_after_auth_error(
                        service,
                        method,
                        parameters,
                        endpoint,
                        retry_on_auth_error,
                        f"Router authentication failed with HTTP {resp.status}"
                    )

                resp.raise_for_status()
                try:
                    data = await resp.json(content_type=None)
                except JSONDecodeError as err:
                    try:
                        return await self._retry_after_auth_error(
                            service,
                            method,
                            parameters,
                            endpoint,
                            retry_on_auth_error,
                            "Router returned a non-JSON response after authentication retry",
                        )
                    except ExperiaBoxV10AuthenticationError as auth_err:
                        raise auth_err from err

                # Check for application-level errors
                if isinstance(data, dict):
                    error_code, error_text = self._extract_error_details(data)

                    if error_code is not None:
                        if self._is_auth_error(error_code, error_text):
                            return await self._retry_after_auth_error(
                                service,
                                method,
                                parameters,
                                endpoint,
                                retry_on_auth_error,
                                f"Router session expired after retry: {data}"
                            )
                        elif error_code == "196618" and service == "sah.Device.WiFi.Radio":
                            _LOGGER.debug("Ignoring 196618 error for WiFi Radio (disabled)")
                            return {}
                        elif error_code == "13":
                            if self._should_retry_permission_denied(service):
                                return await self._retry_after_auth_error(
                                    service,
                                    method,
                                    parameters,
                                    endpoint,
                                    retry_on_auth_error,
                                    f"Router permission denied after authentication retry: {data}"
                                )
                            raise ExperiaBoxV10PermissionDeniedError(
                                f"Router API returned permission denied for {service}: {data}"
                            )
                        else:
                            raise ExperiaBoxV10ApiError(
                                f"Router API returned error {error_code}: {data}"
                            )

                return data if isinstance(data, dict) else {}
        except ExperiaBoxV10PermissionDeniedError:
            raise
        except Exception:
            self._clear_context()
            raise

    def _parse_devices(self, status_list: list[dict], track_wired_devices: bool, results: dict[str, Device], parent_is_wifi: bool = False) -> None:
        """Parse a list of device objects and update the results dictionary."""
        for d in status_list:
            if not isinstance(d, dict):
                continue
            
            mac = d.get("PhysAddress")
            if not mac:
                continue

            active = bool(d.get("Active", False))
            tags = str(d.get("Tags", "")).lower().split()
            inf = str(d.get("InterfaceName", d.get("Layer2Interface", ""))).lower()
            
            is_wifi = parent_is_wifi or "wifi" in tags or "ssw_sta" in tags or "wl0" in inf or "wl1" in inf
            is_wired = not is_wifi and ("eth" in tags or "lan" in tags or "eth" in inf)

            if not track_wired_devices and is_wired:
                continue

            results[mac.upper()] = Device(
                mac.upper(),
                str(d.get("Name", d.get("Key", mac))),
                str(d.get("IPAddress", "")),
                active
            )

    def _parse_topology(self, nodes: list[dict], track_wired_devices: bool, results: dict[str, Device], parent_is_wifi: bool = False) -> None:
        """Recursively parse the topology tree and update the results dictionary."""
        for node in nodes:
            tags = str(node.get("Tags", "")).lower().split()
            inf = str(node.get("InterfaceName", node.get("Layer2Interface", ""))).lower()
            is_wifi = parent_is_wifi or "wifi" in tags or "ssw_sta" in tags or "wl0" in inf or "wl1" in inf
            
            mac = node.get("PhysAddress")
            if mac:
                is_wired = not is_wifi and ("eth" in tags or "lan" in tags or "eth" in inf)
                if not track_wired_devices and is_wired:
                    continue
                results[mac.upper()] = Device(
                    mac.upper(),
                    str(node.get("Name", node.get("Key", mac))),
                    str(node.get("IPAddress", "")),
                    bool(node.get("Active", False))
                )
            
            children = node.get("Children")
            if isinstance(children, list):
                self._parse_topology(children, track_wired_devices, results, parent_is_wifi=is_wifi)

    async def get_devices(self, track_wired_devices: bool = False) -> list[Device]:
        """Get connected devices."""
        results: dict[str, Device] = {}
        successful_query = False
        last_error: Exception | None = None

        # 1. Try generic Devices:get on privileged gateway (proven in trace)
        for expression in (
            "not interface and not self and not voice and .Active==false",
            "not interface and not self and not voice and .Active==true",
        ):
            try:
                data = await self._request(
                    "Devices", "get",
                    {"expression": expression, "flags": "full_links"},
                    endpoint="ws/NeMo/Intf/lan:getMIBs"
                )
                successful_query = True
                status = data.get("status")
                if isinstance(status, list):
                    self._parse_devices(status, track_wired_devices, results)
            except Exception as err:
                last_error = err
                _LOGGER.debug("Failed to get devices via targeted query: %s", err)

        # 2. Try topology traversal as fallback
        if not results:
            for network in ("lan", "guest"):
                try:
                    data = await self._request(
                        f"Devices.Device.{network}", "topology",
                        {"expression": "not logical", "flags": "no_recurse|no_actions"},
                        endpoint="ws/NeMo/Intf/lan:getMIBs"
                    )
                    successful_query = True
                    status = data.get("status")
                    if isinstance(status, list):
                        self._parse_topology(status, track_wired_devices, results)
                except Exception as err:
                    last_error = err
                    _LOGGER.debug("Failed to get %s topology: %s", network, err)

        # Final check to see if we found anything
        if not results:
            _LOGGER.debug("No devices discovered on %s", self._host)
            if not successful_query and last_error:
                raise last_error

        return list(results.values())

    async def get_router_info(self) -> RouterInfo:
        """Get router system information."""
        # Try DeviceInfo first
        data = await self._request("DeviceInfo", "get", endpoint="ws")
        status = data.get("status")
        if not isinstance(status, dict) or not status:
            # Fallback to Devices:get self
            data = await self._request("Devices", "get", {"expression": "self && wan && hgw"}, endpoint="ws/NeMo/Intf/lan:getMIBs")
            status = data.get("status")
            if isinstance(status, list) and status:
                status = status[0]

        if not isinstance(status, dict):
            status = {}

        uptime = int(status.get("UpTime", 0) or 0)
        
        # If uptime is still 0, try to get it from Time service (common in new firmware)
        if uptime == 0:
            try:
                time_data = await self._request("Time", "getTime")
                nmc_data = await self._request("NMC", "get")
                uptime = int(nmc_data.get("status", {}).get("UpTime", 0) or 0)
            except Exception:
                pass

        return RouterInfo(
            model=str(status.get("ModelName", status.get("ProductClass", "Experia Box V10"))),
            hardware_version=str(status.get("HardwareVersion", "")),
            software_version=str(status.get("SoftwareVersion", "")),
            serial_number=str(status.get("SerialNumber", "")),
            uptime=uptime,
        )

    def _parse_mib_result(self, data: dict, mib_names: list[str]) -> dict:
        """Extract MIB data from status dictionary or list."""
        status = data.get("status")
        if isinstance(status, list) and status:
            status = status[0]
        if not isinstance(status, dict):
            # Check if it's in 'data'
            status = data.get("data")
            if isinstance(status, list) and status:
                status = status[0]
            if not isinstance(status, dict):
                return {}
        
        for name in mib_names:
            mib_data = status.get(name)
            if isinstance(mib_data, list) and mib_data:
                mib_data = mib_data[0]
            if isinstance(mib_data, dict):
                return mib_data
            
        return status

    async def get_wan_info(self) -> WanInfo:
        """Get WAN connection information."""
        # Use the confirmed NMC:getWANStatus method
        data = await self._request("NMC", "getWANStatus")
        status = data.get("status", False)
        val = data.get("data", {})
        
        if status and isinstance(val, dict):
            return WanInfo(
                external_ip=str(val.get("IPAddress", "")),
                connected=str(val.get("LinkState", "")).lower() == "up",
                link_status=str(val.get("LinkState", "Down")),
            )

        return WanInfo("", False, "Down")

    async def get_traffic_info(self) -> TrafficInfo:
        """Get traffic information."""
        # Use the confirmed NeMo.Intf.eth0:getNetDevStats method
        # Stats require root /ws endpoint
        data = await self._request("NeMo.Intf.eth0", "getNetDevStats", endpoint="ws")
        status = data.get("status") or {}

        return TrafficInfo(
            bytes_sent=int(status.get("TxBytes", 0) or 0),
            bytes_received=int(status.get("RxBytes", 0) or 0),
            packets_sent=int(status.get("TxPackets", 0) or 0),
            packets_received=int(status.get("RxPackets", 0) or 0),
        )

    async def reboot(self) -> None:
        """Reboot the router."""
        await self._request("NMC", "reboot", {"reason": "WebUI reboot"}, endpoint="ws")

    async def get_guest_wifi_enabled(self) -> bool:
        """Get Guest Wi-Fi status."""
        try:
            data = await self._request("NMC.Guest", "get", endpoint="ws")
            status = data.get("status", {})
            if isinstance(status, dict):
                return bool(status.get("Enable", False))
        except ExperiaBoxV10ApiError as err:
            _LOGGER.debug("Failed to get Guest Wi-Fi via NMC.Guest: %s", err)

        return await self._get_guest_wifi_enabled_from_radio()

    async def _get_guest_wifi_enabled_from_radio(self) -> bool:
        """Get Guest Wi-Fi status from the Wi-Fi radio list."""
        data = await self._request("sah.Device.WiFi.Radio", "get", endpoint="ws")
        status = data.get("status")
        if not isinstance(status, list):
            return False

        for entry in status:
            if isinstance(entry, dict) and "Guest" in str(entry.get("SSID", "")):
                return entry.get("Enable", False)
        return False

    async def set_guest_wifi(self, enable: bool) -> None:
        """Enable or disable Guest Wi-Fi."""
        try:
            await self._request("NMC.Guest", "set", {"Enable": enable}, endpoint="ws")
            return
        except ExperiaBoxV10ApiError as err:
            _LOGGER.debug("Failed to set Guest Wi-Fi via NMC.Guest: %s", err)

        await self._set_guest_wifi_from_radio(enable)

    async def _set_guest_wifi_from_radio(self, enable: bool) -> None:
        """Enable or disable Guest Wi-Fi through the Wi-Fi radio list."""
        data = await self._request("sah.Device.WiFi.Radio", "get", endpoint="ws")
        status = data.get("status")
        if not isinstance(status, list):
            raise Exception("Guest Wi-Fi interface not found")

        for entry in status:
            if isinstance(entry, dict) and "Guest" in str(entry.get("SSID", "")):
                uid = entry.get("UID")
                if uid:
                    await self._request(
                        "sah.Device.WiFi.Radio", "set", {"uid": uid, "Enable": enable}, endpoint="ws"
                    )
                    return
        raise Exception("Guest Wi-Fi interface not found")

    async def get_wifi_enabled(self) -> bool:
        """Get Global Wi-Fi status."""
        data = await self._request("NMC.Wifi", "get", endpoint="ws")
        status = data.get("status", {})
        if not isinstance(status, dict):
            status = {}
        return not status.get("DisableLocalWiFi", False)

    async def set_wifi(self, enable: bool) -> None:
        """Enable or disable Global Wi-Fi."""
        disable_val = not enable
        await self._request("NMC.Wifi", "set", {"DisableLocalWiFi": disable_val}, endpoint="ws")
        await self._request("NeMo.Intf.rad2g0", "set", {"Enable": enable}, endpoint="ws")
        await self._request("NeMo.Intf.rad5g0", "set", {"Enable": enable}, endpoint="ws")
        if enable:
            await self._request("NeMo.Intf.vap2g0priv", "set", {"PersistentEnable": True}, endpoint="ws")
            await self._request("NeMo.Intf.vap5g0priv", "set", {"PersistentEnable": True}, endpoint="ws")
