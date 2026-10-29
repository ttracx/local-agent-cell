"""Chat turn. Muse is the only agent. The cell runs behind the reply."""

from __future__ import annotations

from cell.harness import PROPOSER_ID, fingerprint, run


def narrate(result) -> str:
    denied = [s for s in result.steps if s.status == "deny" or s.status == "reject"]
    ran = [s for s in result.steps if s.stage == "cell"]
    parts = [f"Muse is on this machine. {result.decision}."]
    for step in denied:
        parts.append(f"Sentinel stopped it. {step.detail}")
    for step in ran:
        parts.append(step.detail)
    if denied and not ran:
        parts.append("The cell did not run the denied calls.")
    return "\n\n".join(parts)


def turn(goal: str, workspace: str | None, card: bool) -> dict:
    result = run(goal, workspace, card=card)
    return {
        "agent": "muse",
        "proposer": PROPOSER_ID,
        "fingerprint": fingerprint()[:16],
        "content": narrate(result),
        "decision": result.decision,
        "trace": result.markdown(),
        "files": result.files,
        "workspace": result.workspace,
        "steps": [
            {"stage": s.stage, "status": s.status, "detail": s.detail}
            for s in result.steps
        ],
    }
