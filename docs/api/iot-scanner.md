# IoT Scanner API Contract

The scanner boundary is hardware-agnostic. ESP32, Raspberry Pi, tablet, and the local simulator all call HTTP; they never connect to PostgreSQL or Redis directly.

## Authentication

Seeded development device:

```text
device_id: local-simulator-1
X-Device-Api-Key: local-iot-key
```

Production deployments must provision a unique key per device over a separate trusted process. The API stores only a SHA-256 key hash. Device credentials are not member JWTs and must not be embedded in the member QR code.

The dedicated phone app can verify a provisioned device before saving it:

```http
POST /api/v1/attendance/device/verify
X-Device-Api-Key: <device key>
Content-Type: application/json

{"device_id":"front-door-1"}
```

The response contains only `device_id`, `display_name`, and `status`. It does not return the key.

## Check-in and check-out

```http
POST /api/v1/attendance/check-in
POST /api/v1/attendance/check-out
Content-Type: application/json
X-Device-Api-Key: <device key>

{
  "device_id": "local-simulator-1",
  "qr_token": "<short-lived member QR JWT>"
}
```

Success response:

```json
{
  "code": "CHECK_IN_SUCCESS",
  "message": "Check-in recorded.",
  "session_id": "<uuid>",
  "member_id": "<uuid>",
  "member": {
    "display_name": "Nguyen Anh Khoa",
    "membership_status": "active"
  },
  "attendance_status": "active",
  "action": "check_in",
  "occurred_at": "2026-07-18T08:00:00Z",
  "occupancy": {
    "active_count": 1,
    "capacity": 150,
    "percentage": 0.7,
    "status": "Low",
    "calculated_at": "2026-07-18T08:00:00Z"
  }
}
```

Checkout uses `CHECK_OUT_SUCCESS`, `action: "check_out"`, and `attendance_status: "checked_out"`. The added fields are backward compatible with the original response. Identity/status are derived on the server; the response deliberately excludes email, phone, payment and membership history. Clients should branch on `code`, not English `message` text.

## Authenticated realtime invalidation

Authenticated web/member clients connect to `WS /api/v1/attendance/realtime`, then send the ordinary access token in the first JSON frame within five seconds:

```json
{"type":"authenticate","access_token":"<access JWT>"}
```

The access token is never placed in the URL. Members receive only their own attendance invalidation plus identity-free occupancy invalidation. Staff, manager and admin receive operations invalidation. Clients answer application `ping` frames with `{"type":"pong"}` and refetch authorized REST data after connect, reconnect, `attendance_changed`, `occupancy_changed`, or `resync_required`.

Post-commit events use Redis Pub/Sub across API processes. They contain safe IDs/timestamps, not member names, contact data, QR material, device keys, or access tokens. PostgreSQL remains authoritative; a publish failure cannot undo committed attendance. Timeout batches publish per-member invalidation but only one occupancy invalidation.

## Stable failure responses

Errors use the shared envelope:

```json
{"error":{"code":"DUPLICATE_SCAN","message":"This QR token was scanned too recently.","details":null}}
```

| HTTP | Code | Scanner behavior |
|---:|---|---|
| 401 | `INVALID_DEVICE` | Reject the scan and show device provisioning/support state. |
| 400 | `INVALID_TOKEN` | Ask the member to reopen/refresh My QR. |
| 400 | `EXPIRED_TOKEN` | Ask the member to wait for/trigger QR refresh. |
| 409 | `SUPERSEDED_TOKEN` | A newer token exists; scan the current QR. |
| 403 | `INACTIVE_MEMBERSHIP` | Deny entry and show the returned membership guidance. |
| 409 | `DUPLICATE_SCAN` | Do not retry immediately; honor the configured duplicate window. |
| 409 | `ACTIVE_SESSION_EXISTS` | Treat member as already checked in. |
| 409 | `NO_ACTIVE_SESSION` | Checkout cannot proceed; offer staff assistance. |
| 503 | `QR_STATE_UNAVAILABLE` | Retry later; token state cannot be safely verified. |
| 503 | `SCAN_STATE_UNAVAILABLE` | Retry later; duplicate protection is unavailable. |

Validation failures return `422 VALIDATION_ERROR`; unexpected failures return `500 INTERNAL_SERVER_ERROR` without secrets.

## Token and concurrency behavior

1. The member requests `GET /api/v1/attendance/qr-token/me` with their bearer token.
2. The API validates central membership eligibility, signs a short-lived JWT, and atomically makes its JTI current in Redis.
3. The scanner authenticates the device before parsing the QR.
4. Check-in revalidates JTI and membership, claims a Redis duplicate guard, locks the active-session query, and relies on PostgreSQL's partial unique index as the final race guard.
5. Successful session changes commit before the occupancy projection is reconciled.

## Simulator

From `iot-simulator/`:

```powershell
python -m app.main --scenario valid --token "<QR_TOKEN>"
python -m app.main --scenario duplicate --token "<QR_TOKEN>"
python -m app.main --scenario invalid-token
python -m app.main --scenario unauthorized-device --token "<QR_TOKEN>"
```

Expired and inactive scenarios use deliberately captured development tokens in `EXPIRED_QR_TOKEN` and `INACTIVE_QR_TOKEN`; the simulator does not forge signed tokens.

Optional Compose execution:

```powershell
$env:QR_TOKEN="<QR_TOKEN>"
docker compose --profile iot run --rm iot-simulator python -m app.main --scenario valid --token $env:QR_TOKEN
```
