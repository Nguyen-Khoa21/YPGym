# Routes added or changed for multi-gym (Packages 5 and 6)

Companion to `route-screen-map.md`, kept separate while that file has uncommitted edits. Source: `frontend/src/app/routes.ts`, `router.tsx` and `navigation.ts`.

| Route | Screen | Roles | What changed |
|---|---|---|---|
| `/app/dashboard` | Member dashboard | Member | Package 5: one integrated dashboard (announcements, upcoming bookings and waitlists, notifications, quick actions). |
| `/admin/attendance` | Attendance operations | Staff, manager, owner | Package 6: gym scope bar for the owner, locked until clock-in for staff (`SHIFT_REQUIRED`), per-gym live occupancy and realtime events. |
| `/admin/branches` | Branches | Owner only | Package 6 (new): one card per gym, location edit, workforce reassignment. |
| `/staff/time-clock` | Time clock | Staff, PT (workforce) | Package 6: clock-in belongs to the assigned gym. |
| `/admin/broadcasts` | Broadcasts | Manager, owner | Package 7: the Message field is a shared `Textarea`; manager broadcasts are limited to the assigned gym. |
| `/app/membership-requests` | Freeze and cancellation requests | Member | Package 7: reason fields use the shared `Textarea`. |

The gym scope bar appears only on Attendance and Branches. Other management pages do not yet show a gym selector.
