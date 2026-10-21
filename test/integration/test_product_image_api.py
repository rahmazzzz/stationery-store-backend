
from fastapi.testclient import TestClient


def create_category(api_client: TestClient) -> int:
    response = api_client.post(
        "/api/v1/categories",
        json={"name": "Notebooks", "slug": "notebooks"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_product(api_client: TestClient, category_id: int) -> int:
    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": "A5 Notebook",
            "slug": "a5-notebook",
            "sku": "NOTEBOOK-A5-001",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": "100.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_image(
    api_client: TestClient,
    product_id: int,
    *,
    storage_key: str = "products/notebook.png",
    is_primary: bool = False,
) -> dict:
    response = api_client.post(
        f"/api/v1/products/{product_id}/images",
        json={
            "image_url": f"https://cdn.example.com/{storage_key}",
            "storage_key": storage_key,
            "content_type": "image/png",
            "file_size_bytes": 2048,
            "is_primary": is_primary,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_product_image_returns_201(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)

    response = api_client.post(
        f"/api/v1/products/{product_id}/images",
        json={
            "image_url": "https://cdn.example.com/products/notebook.png",
            "storage_key": "products/notebook.png",
        },
    )

    assert response.status_code == 201, response.text
    image = response.json()
    assert image["product_id"] == product_id
    assert image["storage_key"] == "products/notebook.png"
    assert image["is_primary"] is False


def test_create_image_rejects_nonexistent_product(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/products/999999/images",
        json={
            "image_url": "https://cdn.example.com/missing.png",
            "storage_key": "products/missing.png",
        },
    )

    assert response.status_code == 404


def test_create_image_rejects_duplicate_storage_key(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    create_image(api_client, product_id)

    response = api_client.post(
        f"/api/v1/products/{product_id}/images",
        json={
            "image_url": "https://cdn.example.com/duplicate.png",
            "storage_key": "products/notebook.png",
        },
    )

    assert response.status_code == 409


def test_list_product_images(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    create_image(api_client, product_id)
    create_image(
        api_client,
        product_id,
        storage_key="products/notebook-back.png",
    )

    response = api_client.get(
        f"/api/v1/products/{product_id}/images"
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["sort_order"] <= response.json()[1]["sort_order"]


def test_list_images_rejects_nonexistent_product(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/products/999999/images")

    assert response.status_code == 404


def test_update_product_image(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    image = create_image(api_client, product_id)

    response = api_client.patch(
        f"/api/v1/products/{product_id}/images/{image['id']}",
        json={"alt_text": "Front cover"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["alt_text"] == "Front cover"


def test_update_image_rejects_null_storage_key(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    image = create_image(api_client, product_id)

    response = api_client.patch(
        f"/api/v1/products/{product_id}/images/{image['id']}",
        json={"storage_key": None},
    )

    assert response.status_code == 422


def test_update_image_rejects_empty_patch(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    image = create_image(api_client, product_id)

    response = api_client.patch(
        f"/api/v1/products/{product_id}/images/{image['id']}",
        json={},
    )

    assert response.status_code == 422


def test_update_image_rejects_image_from_another_product(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    first_product_id = create_product(api_client, category_id)

    second_response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": "Sketchbook",
            "slug": "sketchbook",
            "sku": "SKETCHBOOK-001",
            "width_cm": "20.00",
            "height_cm": "20.00",
            "price": "150.00",
        },
    )
    assert second_response.status_code == 201, second_response.text
    second_product_id = second_response.json()["id"]

    image = create_image(api_client, first_product_id)

    response = api_client.patch(
        f"/api/v1/products/{second_product_id}/images/{image['id']}",
        json={"alt_text": "Wrong product"},
    )

    assert response.status_code == 404


def test_set_primary_image(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    first = create_image(
        api_client,
        product_id,
        storage_key="products/first.png",
        is_primary=True,
    )
    second = create_image(
        api_client,
        product_id,
        storage_key="products/second.png",
    )

    response = api_client.put(
        f"/api/v1/products/{product_id}/images/{second['id']}/primary"
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_primary"] is True

    listing = api_client.get(
        f"/api/v1/products/{product_id}/images"
    )
    assert listing.status_code == 200

    primary_images = [
        image for image in listing.json() if image["is_primary"]
    ]
    assert len(primary_images) == 1
    assert primary_images[0]["id"] == second["id"]


def test_set_primary_rejects_missing_image(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)

    response = api_client.put(
        f"/api/v1/products/{product_id}/images/999999/primary"
    )

    assert response.status_code == 404


def test_delete_product_image(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)
    image = create_image(api_client, product_id)

    response = api_client.delete(
        f"/api/v1/products/{product_id}/images/{image['id']}"
    )

    assert response.status_code == 204

    listing = api_client.get(
        f"/api/v1/products/{product_id}/images"
    )
    assert listing.status_code == 200
    assert listing.json() == []


def test_delete_image_rejects_missing_image(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product_id = create_product(api_client, category_id)

    response = api_client.delete(
        f"/api/v1/products/{product_id}/images/999999"
    )

    assert response.status_code == 404
