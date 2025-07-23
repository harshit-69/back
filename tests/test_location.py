import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_driver_location_update(client: AsyncClient):
    response = await client.post("/api/v1/locations/driver/1", json={
        "latitude": 12.9716,
        "longitude": 77.5946,
        "heading": 45.0,
        "speed": 20.0
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Location updated successfully"}  # or whatever your API returns

@pytest.mark.asyncio
async def test_find_nearby_drivers(client: AsyncClient):
    # First update a driver location to ensure there's someone nearby
    await client.post("/api/v1/locations/driver/1", json={
        "latitude": 12.9716,
        "longitude": 77.5946
    })
    
    response = await client.get("/api/v1/locations/drivers/nearby", params={
        "latitude": 12.9716,
        "longitude": 77.5946,
        "radius": 5000
    })
    assert response.status_code == 200
    data = response.json()
    assert "drivers" in data
    assert len(data["drivers"]) > 0  # At least one driver should be nearby