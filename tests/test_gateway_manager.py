from freeai.api.gateway_manager import get_gateway_info, is_gateway_running


def test_gateway_manager_status():
    info = get_gateway_info()
    assert isinstance(info, dict)
    assert "running" in info
    assert "port" in info
    assert "url" in info
    assert is_gateway_running() is False
