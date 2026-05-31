# RoadSoS Demo-Day Polish — Task List

## Backend
- [ ] ISSUE 4 — Extend `/api/health` to return stats (places count, SOS today count)
- [ ] ISSUE 9 — Remove all console.log from backend (none visible, skip)

## Frontend — Dashboard.jsx
- [ ] ISSUE 1 — City/coord mismatch: add `getCityFromCoords`, use live store lat/lng for GRID SEC
- [ ] ISSUE 2 — Active Ops: bind to `places.length` from store
- [ ] ISSUE 3 — Filter tabs: add AMBULANCE + TOWING; fix icon colors; update filter logic
- [ ] ISSUE 4 — Telemetry panel: wire real data from `/api/health`
- [ ] ISSUE 5 — Fleet tab: add placeholder panel
- [ ] ISSUE 6 — Empty state: "NO DISPATCH FOUND IN SECTOR" with retry button
- [ ] ISSUE 7 — Loading skeletons: 3 animated skeleton cards while fetching
- [ ] ISSUE 8 — Mobile: bottom nav bar + bottom sheet results panel

## Frontend — SosModal.jsx
- [ ] ISSUE 10 — Audio ping on SOS fire; SOS button flash-white on countdown=0

## Frontend — General
- [ ] ISSUE 9 — Replace all `console.log` with DEV-only guards
- [ ] Create `public/ping.mp3` (or generate tone via Web Audio API instead)
