Part of the [post-multigym master prompt](../post-multigym-master-prompt.md). Read its sections 0 to 3 first (operating rules, evidence, defaults, cross-cutting rules).

# Package 14: Dashboard and form UI tweaks (web and mobile)

Source: the annotated screenshots in `Post_Multigym_UI_tweaks.pdf`. Use `frontend-design` thinking only to stay inside the existing white-and-green system (`docs/design/route-screen-map.md`); do not restyle anything the owner did not mention.

### Reading of the annotated screenshots (D-18)

- **Web, page 1.** Move the gym location to the top and make it stand out. Shrink the occupancy card. Put a two-tab card beside/under it: **Important notifications** and **Membership**.
- **Mobile, page 2.** The live capacity block and the membership block swap places: capacity becomes the large top card; the membership summary becomes the compact tile. The "Show QR" tile and the membership tile then have the **same size**. "Upcoming classes" sits directly under that row so it is visible without scrolling. The bell shows a small red circle with the unread count. The owner's text "Live capacity tab should swap places with the membership tab above" is read this way because the capacity tile is currently below the large membership card. If the owner meant otherwise, stop and ask.
- **Web, page 3.** The heading "When is it quiet?" becomes "YPGym {current gym}'s Occupancy".

### Requirements

| ID | Requirement |
|---|---|
| FR-UIX-001 | Web dashboard header: show the member's gym as a prominent element near the greeting (map-pin icon, larger type, primary colour, for example "YPGym District 1"). Remove the small duplicate "Your gym: ..." text. Inside `OccupancyCard` the label becomes plain "Live occupancy". This replaces `FR-DASH-001`. |
| FR-UIX-002 | `OccupancyCard` becomes compact: less padding, smaller percentage figure, same data (percentage, status, `active_count` of `capacity`, updated time, progress bar). It stays at the top of the left column. |
| FR-UIX-003 | Directly under it, add one card with two tabs: **Important** (with an unread-count pill) and **Membership**. Important lists active broadcasts first, then unread notifications, at most 5, reusing `dedupeNotifications`, each item once, with an "Open inbox" link. Membership shows plan, status badge, days remaining, expiry, gym and the Renew link (and the Package 13 expired panel when expired). Default tab: Important when there is anything unread or any broadcast, otherwise Membership. Implement with native elements: `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, arrow-key navigation. **No new dependency.** Remove the old full-width Membership section and Notifications card. Keep "Upcoming bookings" and "Quick actions". This replaces `FR-DASH-011` and `FR-DASH-012`. |
| FR-UIX-004 | `TrafficHistory.tsx`: the `<h2>` becomes "{display gym name}'s Occupancy" with a helper that adds the "YPGym " prefix only when the name does not already start with it, so the page never shows "YPGym YPGym District 1". During loading or error the heading uses the gym name from the dashboard payload; if none is known it falls back to "Occupancy". Update `aria-labelledby` and any test that reads the old text. Search the mobile app for the same string and change it if present. |
| FR-UIX-005 | Mobile bell: show a small red circle at the top-right of the bell with `unread_notification_count`, capped at "99+", hidden at 0, with `accessibilityLabel` "Notifications, N unread". Use the existing `IconButton`; extend it with an optional badge rather than writing a new button. Refresh with the dashboard query. |
| FR-UIX-006 | Mobile dashboard order: Brand/bell, heading, **Live capacity hero card** (gym name prominent, percentage, status pill, progress bar), then a two-tile row **[Show QR | Membership]** with equal height and width, then **Upcoming classes** (compact: next 2 bookings, "See all"), then announcements, then notifications. The membership tile shows the status pill, days remaining, and "Expires {date}", and taps through to the renew screens. The account tier text moves into the tile as small text; the home gym shows in the hero. On narrow phones (under 390 px) the tiles stack as they do today. |
| FR-UIX-007 | Admin "Schedule a class" dialog: the Description field spans both grid columns (`sm:col-span-2`), is full width, uses the shared `Textarea` from `components/ui/Form.tsx` (same border, radius and focus style as the inputs), has at least 8rem height, vertical resize only, and a live counter against the 3000-character limit already in the Zod schema. Check the edit dialog uses the same field. Do not change other fields. |
| FR-UIX-008 | Update `memberDashboardLogic.ts` and its tests, `frontend/e2e/member-dashboard.spec.ts`, and the Package 5 spec rows listed in E11. Add e2e checks at 390 px and 1280 px wide: no horizontal scroll, tabs switch by mouse and keyboard, the heading text is correct. |

### Acceptance criteria

- **AC-UIX-001.** At 1280 px the gym label, occupancy and the tab card are all visible without scrolling; at 390 px nothing overflows horizontally.
- **AC-UIX-002.** Switching tabs by keyboard works; each notification or broadcast appears once.
- **AC-UIX-003.** A member with no membership still sees the existing "Choose your gym" prompt (decision D-04 is unchanged).
- **AC-UIX-004.** Heading shows "YPGym District 11's Occupancy" for a District 11 member (not a doubled prefix).
- **AC-UIX-005.** Mobile: with 3 unread the bell shows "3"; with 120 it shows "99+"; with 0 no badge. Capacity card is above the QR/Membership row; the two tiles have equal measured size; at least the first upcoming class is on screen on a typical 390 x 844 device without scrolling (verify on a simulator or document a manual check).
- **AC-UIX-006.** The class description field is as wide as the dialog content and the dialog still fits at 1280 x 720.

### Tasks

T14-01 spec and the E11 spec edits. T14-02 web header, `OccupancyCard`, tab component, remove old sections. T14-03 `TrafficHistory` heading and helper. T14-04 mobile bell badge. T14-05 mobile layout reorder and equal tiles. T14-06 class dialog field. T14-07 tests and screenshots at both widths for the report.

**Out of scope:** a web notification badge (add it only if the shell already has a bell and it is a one-line change), redesigning other pages.

