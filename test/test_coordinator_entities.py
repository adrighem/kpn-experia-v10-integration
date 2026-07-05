"""Test the ExperiaBox v10 Coordinator and Entities."""
import logging
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from datetime import timedelta

from custom_components.experiaboxv10.coordinator import (
    ExperiaBoxV10Coordinator,
    ExperiaBoxV10Data,
)
from custom_components.experiaboxv10.device_tracker import ExperiaBoxV10DeviceScannerEntity
from custom_components.experiaboxv10.api import (
    ExperiaBoxV10PermissionDeniedError,
    Device,
    RouterInfo,
    WanInfo,
    TrafficInfo,
)

@pytest.fixture
def hass():
    return MagicMock()

@pytest.fixture
def entry():
    mock_entry = MagicMock()
    mock_entry.data = {"host": "1.2.3.4", "username": "u", "password": "p"}
    mock_entry.options = {}
    return mock_entry

@pytest.fixture
def coordinator(hass, entry):
    with patch("custom_components.experiaboxv10.coordinator.async_get_clientsession"):
        return ExperiaBoxV10Coordinator(hass, entry)

def test_coordinator_init(coordinator):
    """Test coordinator initialization."""
    assert coordinator.name == "experiaboxv10"
    assert coordinator.update_interval == timedelta(seconds=30)

@pytest.mark.asyncio
async def test_coordinator_update_data(coordinator):
    """Test coordinator data update."""
    mock_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    
    coordinator.api.get_devices = AsyncMock(return_value=mock_devices)
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic_info)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=True)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)
    
    data = await coordinator._async_update_data()
    assert data.devices == mock_devices
    assert data.router_info == mock_router_info
    assert data.wan_info == mock_wan_info
    assert data.traffic_info == mock_traffic_info
    assert data.guest_wifi_enabled is True

@pytest.mark.asyncio
async def test_coordinator_preserves_devices_on_update_failure(coordinator):
    """Test device list is preserved when device discovery fails after first data."""
    old_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    coordinator.data = ExperiaBoxV10Data(
        old_devices,
        mock_router_info,
        mock_wan_info,
        mock_traffic_info,
        True,
        True,
    )

    coordinator.api.get_devices = AsyncMock(side_effect=Exception("device failure"))
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic_info)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)

    data = await coordinator._async_update_data()

    assert data.devices == old_devices

@pytest.mark.asyncio
async def test_coordinator_logs_device_permission_denied_at_debug(coordinator, caplog):
    """Test device permission errors do not create warning spam after first data."""
    old_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    coordinator.data = ExperiaBoxV10Data(
        old_devices,
        mock_router_info,
        mock_wan_info,
        mock_traffic_info,
        False,
        True,
    )

    coordinator.api.get_devices = AsyncMock(
        side_effect=ExperiaBoxV10PermissionDeniedError(
            "Router API returned permission denied for Devices.Device.guest"
        )
    )
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic_info)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)

    with caplog.at_level(logging.DEBUG, logger="custom_components.experiaboxv10.coordinator"):
        data = await coordinator._async_update_data()

    assert data.devices == old_devices
    assert "Partial update failure" not in caplog.text
    assert "Optional update unavailable for devices" in caplog.text

@pytest.mark.asyncio
async def test_coordinator_logs_optional_permission_denied_at_debug(coordinator, caplog):
    """Test optional permission errors do not create warning spam."""
    mock_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")

    coordinator.api.get_devices = AsyncMock(return_value=mock_devices)
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(
        side_effect=ExperiaBoxV10PermissionDeniedError(
            "Router API returned permission denied for NeMo.Intf.eth0"
        )
    )
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(
        side_effect=ExperiaBoxV10PermissionDeniedError(
            "Router API returned permission denied for NMC.Wifi"
        )
    )

    with caplog.at_level(logging.DEBUG, logger="custom_components.experiaboxv10.coordinator"):
        data = await coordinator._async_update_data()

    assert data.devices == mock_devices
    assert data.traffic_info == TrafficInfo(0, 0, 0, 0)
    assert data.wifi_enabled is False
    assert "Partial update failure" not in caplog.text
    assert "Optional update unavailable for traffic counters" in caplog.text
    assert "Optional update unavailable for Wi-Fi status" in caplog.text

@pytest.mark.asyncio
async def test_coordinator_preserves_transient_zero_uptime(coordinator, caplog):
    """Test transient zero uptime does not create a sensor history dip."""
    mock_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    previous_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 3600)
    current_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 0)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    coordinator.data = ExperiaBoxV10Data(
        mock_devices,
        previous_router_info,
        mock_wan_info,
        mock_traffic_info,
        False,
        True,
    )

    coordinator.api.get_devices = AsyncMock(return_value=mock_devices)
    coordinator.api.get_router_info = AsyncMock(return_value=current_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic_info)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)

    with caplog.at_level(logging.DEBUG, logger="custom_components.experiaboxv10.coordinator"):
        data = await coordinator._async_update_data()

    assert data.router_info == current_router_info._replace(uptime=3600)
    assert "Ignoring transient zero router uptime during update" in caplog.text

@pytest.mark.asyncio
async def test_coordinator_preserves_transient_zero_traffic_counters(coordinator, caplog):
    """Test transient zero traffic counters do not reset sensors or throughput baseline."""
    mock_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 3600)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    previous_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    zero_traffic_info = TrafficInfo(0, 0, 0, 0)
    coordinator.data = ExperiaBoxV10Data(
        mock_devices,
        mock_router_info,
        mock_wan_info,
        previous_traffic_info,
        False,
        True,
        throughput_down=12.0,
        throughput_up=6.0,
    )
    coordinator._last_traffic_info = previous_traffic_info
    coordinator._last_traffic_time = 100.0

    coordinator.api.get_devices = AsyncMock(return_value=mock_devices)
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=zero_traffic_info)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)

    with (
        caplog.at_level(logging.DEBUG, logger="custom_components.experiaboxv10.coordinator"),
        patch("time.monotonic", return_value=130.0),
    ):
        data = await coordinator._async_update_data()

    assert data.traffic_info == previous_traffic_info
    assert data.throughput_down == 12.0
    assert data.throughput_up == 6.0
    assert coordinator._last_traffic_info == previous_traffic_info
    assert coordinator._last_traffic_time == 100.0
    assert "Ignoring transient zero traffic counters during update" in caplog.text

@pytest.mark.asyncio
async def test_coordinator_accepts_zero_traffic_counters_after_reboot(coordinator):
    """Test zero traffic counters are accepted when uptime confirms a reboot."""
    mock_devices = [Device("MAC1", "Name1", "1.1.1.1", True)]
    previous_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 3600)
    current_router_info = RouterInfo("H369A", "V1.0", "V10.C.25.08.15", "SN1", 30)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    previous_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    zero_traffic_info = TrafficInfo(0, 0, 0, 0)
    coordinator.data = ExperiaBoxV10Data(
        mock_devices,
        previous_router_info,
        mock_wan_info,
        previous_traffic_info,
        False,
        True,
        throughput_down=12.0,
        throughput_up=6.0,
    )
    coordinator._last_traffic_info = previous_traffic_info
    coordinator._last_traffic_time = 100.0

    coordinator.api.get_devices = AsyncMock(return_value=mock_devices)
    coordinator.api.get_router_info = AsyncMock(return_value=current_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=zero_traffic_info)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)

    with patch("time.monotonic", return_value=130.0):
        data = await coordinator._async_update_data()

    assert data.router_info == current_router_info
    assert data.traffic_info == zero_traffic_info
    assert data.throughput_down == 0.0
    assert data.throughput_up == 0.0
    assert coordinator._last_traffic_info == zero_traffic_info
    assert coordinator._last_traffic_time == 130.0

@pytest.mark.asyncio
async def test_coordinator_throughput(coordinator):
    """Test throughput calculation in coordinator."""
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    
    # First update
    mock_traffic_1 = TrafficInfo(1000, 2000, 10, 20)
    coordinator.api.get_devices = AsyncMock(return_value=[])
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic_1)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)
    
    with patch("time.monotonic", return_value=100.0):
        data1 = await coordinator._async_update_data()
        assert data1.throughput_down == 0
        assert data1.throughput_up == 0
    
    # Second update after 10 seconds
    mock_traffic_2 = TrafficInfo(2000, 4000, 20, 40) # +1000 sent, +2000 received
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic_2)
    
    with patch("time.monotonic", return_value=110.0):
        data2 = await coordinator._async_update_data()
        # (4000 - 2000) / 10 = 200 bytes/s
        assert data2.throughput_down == 200.0
        # (2000 - 1000) / 10 = 100 bytes/s
        assert data2.throughput_up == 100.0

@pytest.mark.asyncio
async def test_new_device_detection(coordinator):
    """Test new device detection logic."""
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic = TrafficInfo(1000, 2000, 10, 20)
    
    # 1. First poll: known devices populated
    coordinator.api.get_devices = AsyncMock(return_value=[Device("MAC1", "Device1", "1.1.1.1", True)])
    coordinator.api.get_router_info = AsyncMock(return_value=mock_router_info)
    coordinator.api.get_wan_info = AsyncMock(return_value=mock_wan_info)
    coordinator.api.get_traffic_info = AsyncMock(return_value=mock_traffic)
    coordinator.api.get_guest_wifi_enabled = AsyncMock(return_value=False)
    coordinator.api.get_wifi_enabled = AsyncMock(return_value=True)
    
    with patch("time.monotonic", return_value=100.0):
        data1 = await coordinator._async_update_data()
        assert data1.new_device_detected is False
        assert data1.last_new_device is None
    
    # 2. Second poll: new device joins
    coordinator.api.get_devices = AsyncMock(return_value=[
        Device("MAC1", "Device1", "1.1.1.1", True),
        Device("MAC2", "NewDevice", "1.1.1.2", True)
    ])
    
    with patch("time.monotonic", return_value=200.0):
        data2 = await coordinator._async_update_data()
        assert data2.new_device_detected is True
        assert data2.last_new_device == "NewDevice (MAC2)"
        
    # 3. Third poll: after 6 minutes (360s), alert should be OFF
    with patch("time.monotonic", return_value=600.0):
        data3 = await coordinator._async_update_data()
        assert data3.new_device_detected is False
        assert data3.last_new_device == "NewDevice (MAC2)" # Details remain

def test_entity_properties(coordinator):
    """Test device tracker entity properties."""
    mac = "00:11:22:33:44:55"
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    coordinator.data = ExperiaBoxV10Data(
        [Device(mac, "Test Device", "192.168.1.10", True)],
        mock_router_info,
        mock_wan_info,
        mock_traffic_info,
        True
    )
    
    entity = ExperiaBoxV10DeviceScannerEntity(coordinator, mac)
    
    assert entity.unique_id == f"SN1_{mac}"
    assert entity.mac_address == mac
    assert entity.name == "Test Device"
    assert entity.is_connected is True
    assert entity.source_type == "router"
    assert entity.extra_state_attributes == {"ip": "192.168.1.10"}

def test_entity_unique_id_falls_back_to_entry_id(coordinator):
    """Test entity unique IDs stay stable when the router omits serial."""
    mac = "00:11:22:33:44:55"
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    coordinator.entry_id = "entry-123"
    coordinator.data = ExperiaBoxV10Data(
        [Device(mac, "Test Device", "192.168.1.10", True)],
        mock_router_info,
        mock_wan_info,
        mock_traffic_info,
        True
    )

    entity = ExperiaBoxV10DeviceScannerEntity(coordinator, mac)

    assert entity.unique_id == f"entry-123_{mac}"

def test_entity_disconnected(coordinator):
    """Test entity behavior when device is disconnected."""
    mac = "00:11:22:33:44:55"
    mock_router_info = RouterInfo("H369A", "V1.0", "V10.C.26.04", "SN1", 100)
    mock_wan_info = WanInfo("8.8.8.8", True, "Up")
    mock_traffic_info = TrafficInfo(1000, 2000, 10, 20)
    coordinator.data = ExperiaBoxV10Data([], mock_router_info, mock_wan_info, mock_traffic_info, True) # No devices
    
    entity = ExperiaBoxV10DeviceScannerEntity(coordinator, mac)
    
    assert entity.is_connected is False
    assert entity.name == mac # Fallback to MAC if not in data
    assert entity.extra_state_attributes == {}
