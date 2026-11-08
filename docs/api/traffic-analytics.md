# Gym traffic analytics API

All paths are under `/api/v1`. PostgreSQL attendance sessions are authoritative. Redis stores only a five-minute aggregate projection keyed by gym and reporting month.

## Endpoints and authorization

| Method and path | Roles | Scope |
|---|---|---|
| `GET /attendance/traffic-summary` | Member | The authenticated member's current or previous membership home gym. |
| `GET /admin/analytics/traffic-summary?gym_id={gym_id}` | Manager, admin | Manager is locked to the assigned gym. Admin may select a gym; District 1 remains the temporary compatibility default until the owner branch selector is delivered. |

The member endpoint derives its gym from backend membership state and does not accept a client-supplied gym ID. Staff cannot access either analytics endpoint. A manager-supplied gym UUID never grants access outside the manager's assignment. Responses contain aggregate counts only—never member identities, contact details, device credentials, or QR material.

## Reporting period

The report always covers the previous completed calendar month in the gym's IANA timezone. `period_start` is inclusive and `period_end` is exclusive. For example, a November request for an `Asia/Ho_Chi_Minh` gym reports from October 1 at 00:00 `+07:00` through November 1 at 00:00 `+07:00`.

## Occupancy estimate

The service samples concurrent attendance every 15 minutes, then aggregates those samples into 12 two-hour local-time windows and a 7×12 weekday/window heatmap.

A session contributes to a sample when:

```text
checked_in_at <= sample_time < effective_end
```

Closed sessions use their persisted `closed_at`. Open sessions are capped at `checked_in_at + attendance_timeout_minutes`, so a stale active row cannot inflate the whole month. Sessions crossing a month boundary contribute only inside the reporting period.

Each window returns:

- average concurrent headcount;
- average percentage of that gym's capacity;
- number of 15-minute samples.

The response also includes visits that started in the month, unique members, average visit duration, total overlapping sessions, overall average occupancy, methodology metadata, and whether synthetic demo attendance is included.

Opening hours are not currently stored per gym, so all 12 windows are returned. The API does not fabricate closed hours.

## Data sufficiency

At least three sessions must overlap the reporting month before `busiest_window` or `quietest_window` is returned. Below that threshold:

- `data_sufficient` is `false`;
- both summary windows are `null`;
- `insufficiency_reason` is `Not enough attendance data yet`;
- the complete zero-capable bucket series remains available for transparent inspection.

The results are historical estimates, not forecasts or personalized recommendations.

## Legacy check-in heatmap

`GET /admin/analytics/peak-hours` remains temporarily available for compatibility. It counts check-in events and must not be presented as concurrent crowdedness. The web attendance workspace now uses the traffic-summary endpoint instead.
