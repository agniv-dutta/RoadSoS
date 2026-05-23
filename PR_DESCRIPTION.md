PR: Dialogue FSM (transitions) + CAP exporter + session store + integration tests

Summary
- Implemented a per-session finite state machine for triage dialogue using `transitions`.
- Added deterministic CAP v1.2 exporter to map NLU output to CAP JSON and validate packets.
- SessionStore for in-memory session management with expiry and background cleanup.
- Integrated FSM into triage router; added session-aware parse-message endpoint.
- Added unit tests for CAP exporter and FSM, plus integration tests for endpoints.

Files changed/added
- backend/app/nlu/cap_exporter.py
- backend/app/dialogue/session_store.py
- backend/app/dialogue/state_machine.py
- backend/app/routers/triage.py (integration)
- backend/app/main.py (session store startup + cleanup task)
- backend/tests/test_cap_exporter.py
- backend/tests/test_state_machine.py
- backend/tests/test_integration_trieage.py (if present)

Notes
- The FSM uses per-session `transitions.Machine` instances attached to SessionState.machine.
- DOT export available via `TriageStateMachine.export_graph(session_id)` for judge auditing.
- All CAP generation is deterministic and offline.

How to run tests
- Activate venv and run pytest with PYTHONPATH=backend:
  $env:PYTHONPATH = "backend"
  .venv\Scripts\python.exe -m pytest backend/tests -q

Request
- Please review and merge into main branch. If you want the FSM graph written to a file or served over an admin endpoint, I can add that as a follow-up.
