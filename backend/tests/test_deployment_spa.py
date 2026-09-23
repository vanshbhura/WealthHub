import pytest


def test_health_endpoints(client):
    """Verify both /health and /api/health return healthy status."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_api_health = client.get("/api/health")
    assert res_api_health.status_code == 200
    assert res_api_health.json()["status"] == "healthy"


def test_docs_endpoint(client):
    """Verify FastAPI /docs Swagger UI is accessible."""
    res = client.get("/docs")
    assert res.status_code == 200
    assert "swagger" in res.text.lower() or "html" in res.headers.get("content-type", "").lower()


def test_root_serves_spa_html(client):
    """Verify GET / serves the React application index.html."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert '<div id="root">' in res.text


def test_spa_fallback_routes(client):
    """Verify non-API routes serve index.html for client-side React routing."""
    spa_routes = ["/dashboard", "/platforms", "/platform/123", "/settings"]
    for route in spa_routes:
        res = client.get(route)
        assert res.status_code == 200, f"Route {route} failed to return 200"
        assert "text/html" in res.headers.get("content-type", "")
        assert '<div id="root">' in res.text


def test_api_routes_never_intercepted_by_spa_fallback(client):
    """Verify unhandled /api/* endpoints return 404 JSON, NEVER the HTML index.html."""
    res = client.get("/api/nonexistent_endpoint_for_test")
    assert res.status_code == 404
    assert "application/json" in res.headers.get("content-type", "")
    data = res.json()
    assert "ENDPOINT_NOT_FOUND" in str(data) or "detail" in data
    assert '<div id="root">' not in res.text


def test_cors_configuration(client):
    """Verify CORS preflight allows https://wealthhub.antideploy.com."""
    headers = {
        "Origin": "https://wealthhub.antideploy.com",
        "Access-Control-Request-Method": "GET",
    }
    res = client.options("/api/health", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://wealthhub.antideploy.com"
