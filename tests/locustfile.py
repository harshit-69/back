from locust import HttpUser, task, between

class LocationUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def update_location(self):
        self.client.post("/api/v1/locations/driver/1", json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "heading": 45.0,
            "speed": 20.0
        })

    @task
    def search_nearby(self):
        self.client.get("/api/v1/locations/drivers/nearby", params={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "radius": 5000
        })
