import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_ride_flow(client: AsyncClient):
    # Create a new ride
    ride_data = {
        "pickup": {"latitude": 12.9716, "longitude": 77.5946},
        "dropoff": {"latitude": 12.9816, "longitude": 77.5846},
        "passenger_id": 1  # Assuming you need passenger ID
    }
    ride_response = await client.post("/api/v1/rides/", json=ride_data)
    assert ride_response.status_code == 201
    ride_id = ride_response.json()["id"]

    # Driver accepts the ride
    accept_response = await client.post(
        f"/api/v1/rides/{ride_id}/accept",
        json={"driver_id": 1}  # Assuming driver ID is required
    )
    assert accept_response.status_code == 200

    # Simulate driver movement
    locations = [
        {"latitude": 12.9726, "longitude": 77.5936},
        {"latitude": 12.9736, "longitude": 77.5926},
        {"latitude": 12.9746, "longitude": 77.5916},
    ]
    
    for loc in locations:
        await client.post("/api/v1/locations/driver/1", json=loc)
        # No need for sleep in tests - they should be fast and deterministic

    # Complete the ride
    complete_response = await client.post(f"/api/v1/rides/{ride_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json() == {"status": "completed"}