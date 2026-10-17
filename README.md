# SKYWEAVE AI

SKYWEAVE AI is a civilian India-wide aviation response command console for humanitarian cargo, medical evacuation, rescue and disaster-relief operations. It uses deterministic synthetic data, FastAPI, WebSockets and OR-Tools CP-SAT to provide auditable decision support.

## Run

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Demonstration

1. Open the Operations screen.
2. Choose an India relief hub and inject a closure.
3. Inspect the affected mission list.
4. Run the OR-Tools optimiser.
5. Compare the pending proposal with the approved plan.
6. Review solver explanations and hard-constraint status.
7. Approve or reject the plan.
8. Open Fleet Health for operator-reported defects.
9. Open Weather Desk for the public forecast feed.
10. Use Decision Ledger to review persistent decisions.
11. Open Mission Planner to search missions and compare baseline, minimum-change and priority-optimised plans.
12. Add synthetic missions, aircraft and crew from the UI.
13. Edit aircraft or crew schedules and update aircraft/crew availability.
14. Open Weather Intelligence and scan the full route corridor between two airfields.
15. Ask SKYWEAVE COPILOT for evidence-backed explanations of current risks and bottlenecks.

All locations, aircraft, reports and missions are synthetic. External weather is optional and falls back to clearly labelled local demo data.

The seeded scenario contains 12 aircraft, 20 crew records and 18 missions. Existing local databases with the older smaller scenario are automatically reset once on startup so the canonical demo state matches the current prototype.
