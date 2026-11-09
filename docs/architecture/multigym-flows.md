# Multi-gym flows: scan to occupancy, and realtime scope

Verified against `backend/app/services/attendance_service.py`, `attendance_realtime_service.py` and `backend/app/api/v1/endpoints/attendance_realtime.py`. This page is separate from `system-architecture.md` on purpose; fold it in when that file is free of other edits.

## Scan to gym-scoped occupancy

```mermaid
sequenceDiagram
  autonumber
  participant Member as Member QR (home gym)
  participant Scanner as Scanner device (belongs to one gym)
  participant API as POST /attendance/check-in
  participant DB as PostgreSQL
  participant Redis
  participant Web as Operations web page

  Member->>Scanner: shows signed QR token
  Scanner->>API: device_id, qr_token, X-Device-Api-Key
  API->>DB: iot_devices row gives gym_id
  API->>DB: membership.home_gym_id must equal device gym
  alt different gym
    API-->>Scanner: 403 MEMBERSHIP_GYM_MISMATCH
  else same gym
    API->>Redis: duplicate-scan key ypgym:attendance:scan:{jti}
    API->>DB: attendance_sessions + attendance_events with gym_id
    API->>DB: recount active sessions for that gym only
    API->>Redis: cache ypgym:attendance:occupancy:{gym_id}
    API->>Redis: PUBLISH ypgym:attendance:{gym_id}:events:v1
    API-->>Scanner: CHECK_IN_SUCCESS
  end
  Redis-->>Web: realtime event for that gym only
```

PostgreSQL is the source of truth. Redis holds only the 30-second occupancy cache, the duplicate-scan guard and the realtime channel. Check-out reads the session and refuses with `403 ATTENDANCE_GYM_MISMATCH` when the scanner belongs to another gym.

## Realtime socket scope

```mermaid
flowchart LR
  A[Web client opens WS /attendance/realtime] --> B[First frame: authenticate + optional gym_id]
  B --> C{Role allowed?}
  C -- no --> X[Close 4403]
  C -- yes --> D[GymScopeService.resolve_gym_id]
  D -- not allowed --> Y[Close 4403]
  D -- one gym --> E[Connection bound to that gym]
  D -- owner, no gym --> F[Connection receives all gyms]
  R[(Redis pattern ypgym:attendance:*:events:v1)] --> G[Server listener]
  G --> H{Connection gym equals event gym?}
  H -- yes or all-gyms --> I[Send payload with gym_id]
  H -- no --> J[Drop]
  E --> H
  F --> H
```

A manager or staff socket is bound to the assigned gym. A member socket is bound to the home gym. Only the owner may leave the gym open. The web client also checks the event's `gym_id` against the gym on screen and ignores a mismatch (`invalidateAttendanceQueries(client, eventGymId)`).

## Cache and channel keys

| Key or channel | Purpose |
|---|---|
| `ypgym:attendance:occupancy:{gym_id}` | 30-second occupancy cache, per gym |
| `ypgym:attendance:{gym_id}:events:v1` | Realtime channel, per gym |
| `ypgym:attendance:*:events:v1` | Listener subscription pattern |
| `ypgym:analytics:summary:` plus gym and revenue flag | 60-second analytics cache; owner and manager responses are cached separately |
| `ypgym:attendance:scan:{jti}` | Duplicate scan guard |
