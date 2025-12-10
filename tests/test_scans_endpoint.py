import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from app.main import app
from app.api.deps import get_current_user

# Mock auth
async def mock_get_current_user():
    from app.models.user import User
    return User(id=1, email="test@example.com", is_active=True)

app.dependency_overrides[get_current_user] = mock_get_current_user

@pytest.mark.asyncio
async def test_create_scan_success():
    payload = {"url": "https://example.com"}
    
    # Mock ScanService.perform_scan
    with patch("app.api.api_v1.scans.ScanService") as MockServiceClass:
        mock_instance = MockServiceClass.return_value
        mock_instance.perform_scan = AsyncMock(return_value={
            "id": 123,
            "url": "https://example.com",
            "total_images": 1,
            "alt_images": 1,
            "non_alt_images": 0,
            "created_at": "2023-01-01T00:00:00"
        })
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/web-image-analyzer/api/v1/scans/", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 123
        assert data["url"] == "https://example.com"

@pytest.mark.asyncio
async def test_create_scan_invalid_url():
    payload = {"url": "not-a-url"}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/web-image-analyzer/api/v1/scans/", json=payload)
    assert response.status_code in (400, 422)

def test_validate_url_logic():
    from app.services.scan_service import ScanService, ScanError
    from unittest.mock import MagicMock
    
    service = ScanService(db=MagicMock())
    
    with pytest.raises(ScanError) as exc:
        service.validate_url("http://127.0.0.1/foo")
    assert "private" in str(exc.value) or "disallowed" in str(exc.value)

    with pytest.raises(ScanError):
        service.validate_url("ftp://example.com") # Scheme
