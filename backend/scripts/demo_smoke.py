"""Connected HTTP demo on compose.demo.yml only; prints no credentials or token material."""
import argparse
from urllib.parse import urlsplit

import httpx

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Loopback API URL inside the isolated demo backend container.")
    base_url = parser.parse_args().base_url.rstrip("/") + "/"
    address = urlsplit(base_url)
    settings = get_settings()
    if (settings.ENVIRONMENT != "development" or urlsplit(settings.DATABASE_URL).path != "/ypgym_demo"
            or address.hostname not in {"localhost", "127.0.0.1"} or address.port != 8000
            or address.path.rstrip("/") != settings.API_V1_PREFIX):
        raise SystemExit("Refusing demonstration mutations outside the isolated demo database.")
    with httpx.Client(base_url=base_url, timeout=30) as client:
        def request(method, path, *, expected=200, **kwargs):
            response = client.request(method, path.removeprefix(settings.API_V1_PREFIX + "/"), **kwargs)
            assert response.status_code == expected, f"{method} {path}: HTTP {response.status_code}, expected {expected}"
            return response

        def login(slug):
            response = request("POST", "auth/login", json={"email": f"{slug}@ypgym.dev", "password": settings.DEVELOPMENT_SEED_PASSWORD})
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        request("GET", "health/dependencies")
        roles = {slug: login(slug) for slug in ["member", "admin", "manager", "staff", "pt", "newmember", "advance", "normal"]}
        member = roles["member"]
        dashboard = request("GET", "dashboard/me", headers=member).json()
        assert dashboard["membership"]["status"] == "active" and dashboard["qr_access"]["eligible"]
        assert dashboard["upcoming_bookings"] and dashboard["active_broadcasts"]
        plans = request("GET", "membership-plans").json()
        plan = next(item for item in plans if item["name"] == "1 Month")
        assert float(plan["base_price"]) == 720000
        for slug, key in [("newmember", "release-demo-smoke-purchase-v1"), ("member", "release-demo-smoke-renewal-v1")]:
            body = {"plan_id": plan["id"], "idempotency_key": key, "mock_payment_confirmed": True}
            first = request("POST", "memberships/purchase", headers=roles[slug], json=body).json()
            replay = request("POST", "memberships/purchase", headers=roles[slug], json=body).json()
            assert first["payment"]["id"] == replay["payment"]["id"]
            pdf = request("GET", first["invoice"]["download_url"], headers=roles[slug])
            assert pdf.content.startswith(b"%PDF")
        print("PASS membership purchase, renewal, idempotency and invoice PDF")

        initial = request("GET", "attendance/crowdedness", headers=member).json()["active_count"]
        token = request("GET", "attendance/qr-token/me", headers=member).json()["token"]
        scanner_headers = {"X-Device-Api-Key": settings.IOT_DEVICE_API_KEY}
        scan = {"device_id": "local-simulator-1", "qr_token": token}
        check_in = request("POST", "attendance/check-in", headers=scanner_headers, json=scan).json()
        assert check_in["occupancy"]["active_count"] == initial + 1
        request("POST", "attendance/check-in", headers=scanner_headers, json=scan, expected=409)
        assert request("GET", "attendance/crowdedness", headers=member).json()["active_count"] == initial + 1
        scan["qr_token"] = request("GET", "attendance/qr-token/me", headers=member).json()["token"]
        checkout = request("POST", "attendance/check-out", headers=scanner_headers, json=scan).json()
        assert checkout["occupancy"]["active_count"] == initial
        assert request("GET", "attendance/crowdedness", headers=member).json()["active_count"] == initial
        print("PASS rotating QR, device scanner contract, duplicate scan and occupancy increase/decrease")

        classes = request("GET", "classes/upcoming", headers=member).json()["items"]
        open_class = next(item for item in classes if item["title"] == "Strength Foundations Demo")
        full_class = next(item for item in classes if item["title"] == "Capacity One Demo")
        request("POST", f"classes/{open_class['id']}/book", headers=member)
        request("POST", f"classes/{full_class['id']}/book", headers=member, expected=409)
        joined = request("POST", f"classes/{full_class['id']}/waitlist", headers=member).json()
        assert joined["position"] == 2
        bookings = request("GET", "bookings/me", headers=roles["advance"]).json()["bookings"]
        holder = next(item for item in bookings if item["gym_class"]["id"] == full_class["id"])
        request("POST", f"bookings/{holder['id']}/cancel", headers=roles["advance"])
        promoted = request("GET", "dashboard/me", headers=roles["normal"]).json()
        assert any(item["gym_class"]["id"] == full_class["id"] for item in promoted["upcoming_bookings"])
        print("PASS booking capacity, waitlist order, cancellation and cross-account promotion")

        admin = roles["admin"]
        crm = request("GET", "admin/members", headers=admin).json()
        target = next(item for item in crm["items"] if item["email"] == "advance@ypgym.dev")
        request("POST", f"admin/members/{target['id']}/revoke", headers=admin, json={"reason": "Synthetic examiner demo of membership policy enforcement"})
        logs = request("GET", "admin/audit-logs", headers=roles["manager"], params={"action": "membership.revoked"}).json()
        assert any(item["target_user_id"] == target["id"] for item in logs["items"])
        for kind in ["payments", "invoices"]:
            exported = request("GET", f"admin/billing/{kind}/export.csv", headers=admin)
            assert "720000.00" in exported.text
        request("GET", "admin/members/export.csv", headers=roles["manager"], expected=403)
        analytics = request("GET", "admin/analytics/summary", headers=roles["manager"]).json()
        assert analytics["attendance"]["check_ins"] >= 21
        assert request("GET", "admin/analytics/summary", headers=roles["manager"]).json()["cache_hit"]
        request("GET", "admin/analytics/summary", headers=roles["staff"], expected=403)
        request("GET", "dashboard/me", headers=roles["pt"], expected=403)
        print("PASS CRM revocation/audit, exports, persisted manager analytics/cache and role denials")
    print("Connected HTTP demo passed. Browser/native rendering and human UAT are separate checks.")


if __name__ == "__main__":
    main()
