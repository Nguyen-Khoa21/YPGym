import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def submit_scan(*, base_url: str, action: str, device_id: str, api_key: str, token: str) -> tuple[int, dict]:
    request = Request(
        f"{base_url.rstrip('/')}/attendance/{action}",
        data=json.dumps({"device_id": device_id, "qr_token": token}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Device-Api-Key": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {"error": {"code": "EMPTY_ERROR", "message": str(exc)}}


def token_for_scenario(scenario: str, token: str | None) -> str:
    if scenario == "invalid-token":
        return "not-a-valid-ypgym-qr-token"
    env_names = {
        "expired-token": "EXPIRED_QR_TOKEN",
        "inactive-membership": "INACTIVE_QR_TOKEN",
    }
    if scenario in env_names:
        scenario_token = os.getenv(env_names[scenario])
        if not scenario_token:
            raise ValueError(f"Set {env_names[scenario]} to a captured development token for this scenario.")
        return scenario_token
    if not token:
        raise ValueError("Provide --token or set QR_TOKEN for valid and duplicate scenarios.")
    return token


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit YPGym QR scans through the hardware-agnostic attendance API.")
    parser.add_argument(
        "--scenario",
        choices=("valid", "invalid-token", "expired-token", "inactive-membership", "duplicate", "unauthorized-device"),
        default="valid",
    )
    parser.add_argument("--action", choices=("check-in", "check-out"), default="check-in")
    parser.add_argument("--token", default=os.getenv("QR_TOKEN"))
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://localhost:8001/api/v1"))
    parser.add_argument("--device-id", default=os.getenv("IOT_DEVICE_ID", "local-simulator-1"))
    parser.add_argument("--api-key", default=os.getenv("IOT_DEVICE_API_KEY", "local-iot-key"))
    args = parser.parse_args()

    try:
        token = token_for_scenario(args.scenario, args.token)
        api_key = "invalid-device-api-key" if args.scenario == "unauthorized-device" else args.api_key
        attempts = 2 if args.scenario == "duplicate" else 1
        for attempt in range(1, attempts + 1):
            status, payload = submit_scan(
                base_url=args.base_url,
                action=args.action,
                device_id=args.device_id,
                api_key=api_key,
                token=token,
            )
            print(json.dumps({"attempt": attempt, "http_status": status, "response": payload}, indent=2))
    except (ValueError, URLError, json.JSONDecodeError) as exc:
        print(f"Simulator error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
