"""Test the ExperiaBox v10 API."""
from json import JSONDecodeError
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from custom_components.experiaboxv10.api import (
    ExperiaBoxV10Api,
    ExperiaBoxV10ApiError,
    ExperiaBoxV10AuthenticationError,
    ExperiaBoxV10PermissionDeniedError,
)

@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def api(mock_session):
    return ExperiaBoxV10Api(mock_session, "192.168.2.254", "admin", "password")

def create_mock_response(status=200, json_data=None, headers=None):
    """Create a mock response object."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.headers = headers or {}
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.raise_for_status = MagicMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    return mock_resp

@pytest.mark.asyncio
async def test_get_devices(api, mock_session):
    """Test get_devices using the new topology method."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_topology_resp = create_mock_response(
        status=200,
        json_data={
            "status": [
                {
                    "Key": "lan",
                    "Children": [
                        {
                            "Key": "ETH0",
                            "Tags": "lan eth",
                            "Children": [
                                {
                                    "PhysAddress": "11:22:33:44:55:66",
                                    "Name": "PC",
                                    "Active": True,
                                    "Tags": "edev lan eth"
                                }
                            ]
                        },
                        {
                            "Key": "vap2g0priv",
                            "Tags": "wifi",
                            "Children": [
                                {
                                    "PhysAddress": "AA:BB:CC:DD:EE:FF",
                                    "Name": "Phone",
                                    "Active": True,
                                    "Tags": "edev wifi"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    )
    # Mocking guest topology as empty
    mock_empty_resp = create_mock_response(status=200, json_data={"status": []})

    def mock_post(url, **kwargs):
        print("MOCK POST CALLED:", url)
        if "login" in url or "ws" in url and "ssw" in str(kwargs.get("json")):
            return mock_login_resp
        if "topology" in str(kwargs.get("json")) and "lan" in str(kwargs.get("json")):
            return mock_topology_resp
        return mock_empty_resp

    mock_session.post.side_effect = mock_post
    devices = await api.get_devices(track_wired_devices=True)

    print("DEVICES FOUND:", devices)
    assert len(devices) == 2
    assert any(d.name == "Phone" for d in devices)
    assert any(d.name == "PC" for d in devices)

@pytest.mark.asyncio
async def test_get_router_info_universal(api, mock_session):
    """Test get_router_info with universal approach."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_data_resp = create_mock_response(
        status=200,
        json_data={
            "status": {
                "ModelName": "H369A",
                "UpTime": 12345
            }
        }
    )
    mock_session.post.side_effect = [mock_login_resp, mock_data_resp]
    info = await api.get_router_info()
    assert info.model == "H369A"
    assert info.uptime == 12345

@pytest.mark.asyncio
async def test_get_wan_info_nmc(api, mock_session):
    """Test get_wan_info using the new NMC:getWANStatus method."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_info_resp = create_mock_response(
        status=200,
        json_data={
            "status": True,
            "data": {
                "IPAddress": "1.2.3.4",
                "LinkState": "up"
            }
        }
    )
    mock_session.post.side_effect = [mock_login_resp, mock_info_resp]
    info = await api.get_wan_info()
    assert info.external_ip == "1.2.3.4"
    assert info.connected is True

@pytest.mark.asyncio
async def test_get_traffic_info(api, mock_session):
    """Test get_traffic_info using the new NeMo.Intf.eth0 method."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_data_resp = create_mock_response(
        status=200,
        json_data={
            "status": {
                "TxBytes": 1000,
                "RxBytes": 2000,
                "TxPackets": 100,
                "RxPackets": 200
            }
        }
    )
    mock_session.post.side_effect = [mock_login_resp, mock_data_resp]
    info = await api.get_traffic_info()
    assert info.bytes_sent == 1000
    assert info.bytes_received == 2000

@pytest.mark.asyncio
async def test_get_guest_wifi_enabled_uses_nmc_guest(api, mock_session):
    """Test get_guest_wifi_enabled uses NMC.Guest as the primary endpoint."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_data_resp = create_mock_response(
        status=200,
        json_data={"status": {"Enable": True}},
    )
    mock_session.post.side_effect = [mock_login_resp, mock_data_resp]

    enabled = await api.get_guest_wifi_enabled()

    assert enabled is True
    request_payload = mock_session.post.call_args_list[1].kwargs["json"]
    assert request_payload["service"] == "NMC.Guest"
    assert request_payload["method"] == "get"

@pytest.mark.asyncio
async def test_get_guest_wifi_enabled_falls_back_to_radio(api, mock_session):
    """Test Guest Wi-Fi status falls back to the Wi-Fi radio list."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_guest_error_resp = create_mock_response(
        status=200,
        json_data={"errors": [{"error": "196618"}]},
    )
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_radio_resp = create_mock_response(
        status=200,
        json_data={
            "status": [
                {"SSID": "KPN", "Enable": True},
                {"SSID": "KPN Guest", "Enable": False},
            ]
        },
    )
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_guest_error_resp,
        mock_login_resp_2,
        mock_radio_resp,
    ]

    enabled = await api.get_guest_wifi_enabled()

    assert enabled is False
    request_payload = mock_session.post.call_args_list[3].kwargs["json"]
    assert request_payload["service"] == "sah.Device.WiFi.Radio"
    assert request_payload["method"] == "get"

@pytest.mark.asyncio
async def test_get_guest_wifi_enabled_radio_fallback_handles_196618(api, mock_session):
    """Test the radio fallback safely catches the 196618 disabled error."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_guest_error_resp = create_mock_response(
        status=200,
        json_data={"errors": [{"error": "196618"}]},
    )
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_data_resp = create_mock_response(
        status=200,
        json_data={
            "error": "196618",
            "errors": [
                {"error": "196618"}
            ]
        }
    )
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_guest_error_resp,
        mock_login_resp_2,
        mock_data_resp,
    ]

    enabled = await api.get_guest_wifi_enabled()

    assert enabled is False

@pytest.mark.asyncio
async def test_set_guest_wifi_uses_nmc_guest(api, mock_session):
    """Test set_guest_wifi uses NMC.Guest as the primary endpoint."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_data_resp = create_mock_response(status=200, json_data={"status": True})
    mock_session.post.side_effect = [mock_login_resp, mock_data_resp]

    await api.set_guest_wifi(False)

    request_payload = mock_session.post.call_args_list[1].kwargs["json"]
    assert request_payload == {
        "service": "NMC.Guest",
        "method": "set",
        "parameters": {"Enable": False},
    }

@pytest.mark.asyncio
async def test_set_guest_wifi_falls_back_to_radio(api, mock_session):
    """Test set_guest_wifi falls back to the Wi-Fi radio UID flow."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_guest_error_resp = create_mock_response(
        status=200,
        json_data={"errors": [{"error": "196618"}]},
    )
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_radio_get_resp = create_mock_response(
        status=200,
        json_data={
            "status": [
                {"SSID": "KPN", "UID": "private", "Enable": True},
                {"SSID": "KPN Guest", "UID": "guest", "Enable": False},
            ]
        },
    )
    mock_radio_set_resp = create_mock_response(status=200, json_data={"status": True})
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_guest_error_resp,
        mock_login_resp_2,
        mock_radio_get_resp,
        mock_radio_set_resp,
    ]

    await api.set_guest_wifi(True)

    radio_get_payload = mock_session.post.call_args_list[3].kwargs["json"]
    radio_set_payload = mock_session.post.call_args_list[4].kwargs["json"]
    assert radio_get_payload["service"] == "sah.Device.WiFi.Radio"
    assert radio_get_payload["method"] == "get"
    assert radio_set_payload == {
        "service": "sah.Device.WiFi.Radio",
        "method": "set",
        "parameters": {"uid": "guest", "Enable": True},
    }

@pytest.mark.asyncio
async def test_request_retries_auth_once(api, mock_session):
    """Test that authentication errors retry once and then fail."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_unauthorized_resp_1 = create_mock_response(status=401)
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_unauthorized_resp_2 = create_mock_response(status=401)
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_unauthorized_resp_1,
        mock_login_resp_2,
        mock_unauthorized_resp_2,
    ]

    with pytest.raises(ExperiaBoxV10AuthenticationError):
        await api._request("NMC", "get", endpoint="ws")

    assert mock_session.post.call_count == 4

@pytest.mark.asyncio
async def test_request_does_not_retry_invalid_arguments(api, mock_session):
    """Test that invalid arguments do not cause recursive auth retries."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_error_resp = create_mock_response(
        status=200,
        json_data={"errors": [{"error": "9003"}]},
    )
    mock_session.post.side_effect = [mock_login_resp, mock_error_resp]

    with pytest.raises(ExperiaBoxV10ApiError):
        await api._request("NMC", "badMethod", endpoint="ws")

    assert mock_session.post.call_count == 2

@pytest.mark.asyncio
async def test_request_retries_nested_status_auth_error(api, mock_session):
    """Test nested router auth errors trigger one relogin and retry."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_expired_resp = create_mock_response(
        status=200,
        json_data={
            "status": {
                "errors": [
                    {
                        "error": "196614",
                        "description": "Invalid session",
                    }
                ]
            }
        },
    )
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_data_resp = create_mock_response(status=200, json_data={"status": {"UpTime": 123}})
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_expired_resp,
        mock_login_resp_2,
        mock_data_resp,
    ]

    data = await api._request("NMC", "get", endpoint="ws")

    assert data == {"status": {"UpTime": 123}}
    assert api._context_id == "def"
    assert mock_session.post.call_count == 4

@pytest.mark.asyncio
async def test_request_retries_non_json_session_timeout_response(api, mock_session):
    """Test a login-page-style non-JSON timeout response triggers one relogin."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_timeout_resp = create_mock_response(status=200)
    mock_timeout_resp.json = AsyncMock(
        side_effect=JSONDecodeError("Expecting value", "<html>Login</html>", 0)
    )
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_data_resp = create_mock_response(status=200, json_data={"status": {"UpTime": 456}})
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_timeout_resp,
        mock_login_resp_2,
        mock_data_resp,
    ]

    data = await api._request("NMC", "get", endpoint="ws")

    assert data == {"status": {"UpTime": 456}}
    assert api._context_id == "def"
    assert mock_session.post.call_count == 4

@pytest.mark.asyncio
async def test_request_retries_core_permission_denied(api, mock_session):
    """Test core permission-denied responses are treated as expired context."""
    mock_login_resp_1 = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_expired_resp = create_mock_response(
        status=200,
        json_data={
            "status": None,
            "errors": [
                {
                    "error": 13,
                    "description": "Permission denied",
                    "info": "Devices",
                }
            ],
        },
    )
    mock_login_resp_2 = create_mock_response(status=200, json_data={"data": {"contextID": "def"}})
    mock_data_resp = create_mock_response(status=200, json_data={"status": []})
    mock_session.post.side_effect = [
        mock_login_resp_1,
        mock_expired_resp,
        mock_login_resp_2,
        mock_data_resp,
    ]

    data = await api._request("Devices", "get")

    assert data == {"status": []}
    assert api._context_id == "def"
    assert mock_session.post.call_count == 4

@pytest.mark.asyncio
async def test_request_raises_permission_denied_without_clearing_context(api, mock_session):
    """Test that permission denied API errors are classified without forcing relogin."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_error_resp = create_mock_response(
        status=200,
        json_data={
            "status": None,
            "errors": [
                {
                    "error": 13,
                    "description": "Permission denied",
                    "info": "NeMo.Intf.eth0",
                }
            ],
        },
    )
    mock_session.post.side_effect = [mock_login_resp, mock_error_resp]

    with pytest.raises(ExperiaBoxV10PermissionDeniedError):
        await api._request("NeMo.Intf.eth0", "getNetDevStats", endpoint="ws")

    assert api._context_id == "abc"
    assert mock_session.post.call_count == 2

@pytest.mark.asyncio
async def test_optional_permission_denied_does_not_clear_context(api, mock_session):
    """Test optional permission-denied responses are not treated as expired context."""
    mock_login_resp = create_mock_response(status=200, json_data={"data": {"contextID": "abc"}})
    mock_error_resp = create_mock_response(
        status=200,
        json_data={
            "status": None,
            "errors": [
                {
                    "error": 13,
                    "description": "Permission denied",
                    "info": "NMC.Wifi",
                }
            ],
        },
    )
    mock_session.post.side_effect = [mock_login_resp, mock_error_resp]

    with pytest.raises(ExperiaBoxV10PermissionDeniedError):
        await api._request("NMC.Wifi", "get", endpoint="ws")

    assert api._context_id == "abc"
    assert mock_session.post.call_count == 2

@pytest.mark.asyncio
async def test_fallback_login_uses_fallback_cookie(api, mock_session):
    """Test fallback login stores the fallback response cookie."""
    mock_login_resp = create_mock_response(
        status=404,
        json_data={},
        headers={"set-cookie": "wrong=1; Path=/"},
    )
    mock_fallback_login_resp = create_mock_response(
        status=200,
        json_data={"data": {"contextID": "abc"}},
        headers={"set-cookie": "fallback=1; Path=/"},
    )
    mock_data_resp = create_mock_response(status=200, json_data={"status": {}})
    mock_session.post.side_effect = [
        mock_login_resp,
        mock_fallback_login_resp,
        mock_data_resp,
    ]

    await api._request("NMC", "get", endpoint="ws")

    request_headers = mock_session.post.call_args_list[2].kwargs["headers"]
    assert request_headers["Cookie"] == "fallback=1"

@pytest.mark.asyncio
async def test_get_context_reuses_context_with_empty_cookie(api, mock_session):
    """Test login lock waiters reuse a context even when no cookie was set."""
    mock_login_resp = create_mock_response(
        status=200,
        json_data={"data": {"contextID": "abc"}},
    )
    mock_session.post.return_value = mock_login_resp

    first_context = await api._get_context()
    second_context = await api._get_context()

    assert first_context == ("abc", "")
    assert second_context == ("abc", "")
    assert mock_session.post.call_count == 1

@pytest.mark.asyncio
async def test_get_context_records_creation_time(api, mock_session):
    """Test successful login records when the context was created."""
    mock_login_resp = create_mock_response(
        status=200,
        json_data={"data": {"contextID": "abc"}},
    )
    mock_session.post.return_value = mock_login_resp

    with patch("custom_components.experiaboxv10.api.time.monotonic", return_value=123.0):
        await api._get_context()

    assert api._context_created_at == 123.0

@pytest.mark.asyncio
async def test_request_reuses_context_before_proactive_refresh_interval(api, mock_session):
    """Test requests keep using a recent cached context."""
    api._context_id = "abc"
    api._cookie = "sid=abc"
    api._context_created_at = 100.0
    mock_data_resp = create_mock_response(status=200, json_data={"status": {"UpTime": 123}})
    mock_session.post.return_value = mock_data_resp

    with patch("custom_components.experiaboxv10.api.time.monotonic", return_value=1000.0):
        data = await api._request("NMC", "get", endpoint="ws")

    request_headers = mock_session.post.call_args.kwargs["headers"]
    assert data == {"status": {"UpTime": 123}}
    assert request_headers["X-Context"] == "abc"
    assert request_headers["Cookie"] == "sid=abc"
    assert mock_session.post.call_count == 1

@pytest.mark.asyncio
async def test_request_refreshes_context_before_timeout(api, mock_session):
    """Test old cached contexts are renewed before the router timeout."""
    api._context_id = "abc"
    api._cookie = "sid=abc"
    api._context_created_at = 100.0
    mock_login_resp = create_mock_response(
        status=200,
        json_data={"data": {"contextID": "def"}},
        headers={"set-cookie": "sid=def; Path=/"},
    )
    mock_data_resp = create_mock_response(status=200, json_data={"status": {"UpTime": 456}})
    mock_session.post.side_effect = [mock_login_resp, mock_data_resp]

    with patch("custom_components.experiaboxv10.api.time.monotonic", return_value=1601.0):
        data = await api._request("NMC", "get", endpoint="ws")

    login_payload = mock_session.post.call_args_list[0].kwargs["json"]
    request_headers = mock_session.post.call_args_list[1].kwargs["headers"]
    assert login_payload["method"] == "createContext"
    assert data == {"status": {"UpTime": 456}}
    assert api._context_id == "def"
    assert api._cookie == "sid=def"
    assert api._context_created_at == 1601.0
    assert request_headers["X-Context"] == "def"
    assert request_headers["Cookie"] == "sid=def"
    assert mock_session.post.call_count == 2

@pytest.mark.asyncio
async def test_get_devices_raises_when_all_endpoints_fail(api):
    """Test device discovery raises if every endpoint fails."""
    api._request = AsyncMock(side_effect=ExperiaBoxV10AuthenticationError("auth failed"))

    with pytest.raises(ExperiaBoxV10AuthenticationError):
        await api.get_devices()
