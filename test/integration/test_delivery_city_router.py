from fastapi import HTTPException

from app.container.dependencies import get_current_admin
from app.main import app

def test_admin_can_create_delivery_city(api_client):
    from app.main import app

    app.dependency_overrides[get_current_admin] = allow_admin

    try:
        response = api_client.post(
            "/api/v1/admin/delivery-cities/",
            json={
                "name": "Integration Test City",
                "shipping_fee": "30.00",
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Integration Test City"
        assert float(data["shipping_fee"]) == 30.00
        assert "id" in data
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


def test_admin_can_update_delivery_city(api_client):
    from app.main import app

    app.dependency_overrides[get_current_admin] = allow_admin

    try:
        create_response = api_client.post(
            "/api/v1/admin/delivery-cities/",
            json={
                "name": "City Before Update",
                "shipping_fee": "30.00",
            },
        )

        assert create_response.status_code == 201
        city_id = create_response.json()["id"]

        update_response = api_client.patch(
            f"/api/v1/admin/delivery-cities/{city_id}",
            json={"shipping_fee": "45.00"},
        )

        assert update_response.status_code == 200

        data = update_response.json()
        assert data["id"] == city_id
        assert float(data["shipping_fee"]) == 45.00
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


def test_admin_can_list_delivery_cities(api_client):
    from app.main import app

    app.dependency_overrides[get_current_admin] = allow_admin

    try:
        create_response = api_client.post(
            "/api/v1/admin/delivery-cities/",
            json={
                "name": "City For Listing",
                "shipping_fee": "25.00",
            },
        )

        assert create_response.status_code == 201

        response = api_client.get("/api/v1/admin/delivery-cities/")

        assert response.status_code == 200
        assert any(
            city["name"] == "City For Listing"
            for city in response.json()
        )
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


def allow_admin():
    return {"user_id": "test-admin-id", "email": "admin@example.com"}

def test_delivery_city_admin_routes_require_admin(api_client):
    """Requests without admin authorization must be rejected."""
    from app.main import app

    def reject_non_admin():
        raise HTTPException(
            status_code=403,
            detail="Administrator access is required.",
        )

    app.dependency_overrides[get_current_admin] = reject_non_admin

    try:
        response = api_client.get("/api/v1/admin/delivery-cities/")
        assert response.status_code == 403

        response = api_client.post(
            "/api/v1/admin/delivery-cities/",
            json={"name": "Test City", "shipping_fee": "30.00"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_admin, None)

def test_public_endpoint_returns_active_cities(api_client):
    app.dependency_overrides[get_current_admin] = allow_admin

    try:
        create_response = api_client.post(
            "/api/v1/admin/delivery-cities/",
            json={
                "name": "Active Public Test City",
                "shipping_fee": "25.00",
                "is_active": True,
            },
        )
        assert create_response.status_code == 201

        response = api_client.get("/api/v1/delivery-cities/")

        assert response.status_code == 200
        assert any(
            city["name"] == "Active Public Test City"
            for city in response.json()
        )
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


def test_public_endpoint_excludes_inactive_cities(api_client):
    app.dependency_overrides[get_current_admin] = allow_admin

    try:
        create_response = api_client.post(
            "/api/v1/admin/delivery-cities/",
            json={
                "name": "Inactive Public Test City",
                "shipping_fee": "25.00",
                "is_active": False,
            },
        )
        assert create_response.status_code == 201

        response = api_client.get("/api/v1/delivery-cities/")

        assert response.status_code == 200
        assert all(
            city["name"] != "Inactive Public Test City"
            for city in response.json()
        )
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


def test_public_endpoint_does_not_require_admin(api_client):
    response = api_client.get("/api/v1/delivery-cities/")

    assert response.status_code == 200
