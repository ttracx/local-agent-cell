"""Host plane for the Local Agent Cell Space POC.

The proposer is deterministic on purpose. A CPU Space cannot host Muse Spark
Open, and a hosted planner would leave the machine. Dangerous goals are still
*proposed*. The Sentinel is what stops them.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PROPOSER_ID = "deterministic-proposer-v1"
SCHEMA_VERSION = "1"
CANARY = "thox-canary-9f3a7c"  # host-only; must never appear in a trace or cell result

TOOLS = {
    "fs.list": "read",
    "fs.read": "read",
    "fs.write": "write",
    "net.fetch": "network",
    "mail.send": "irreversible",
}

_URL = re.compile(r"https?://[^\s'\"<>]+", re.I)
_REL_FILE = re.compile(r"(?<![\w./-])([A-Za-z0-9][\w./-]{0,80}\.(?:txt|md|json))")


def fingerprint() -> str:
    raw = f"{PROPOSER_ID}|{SCHEMA_VERSION}|tools:{','.join(sorted(TOOLS))}"
    return hashlib.sha256(raw.encode()).hexdigest()


def new_workspace() -> str:
    root = Path(tempfile.mkdtemp(prefix="lac-"))
    (root / "README.txt").write_text(
        "Task workspace. The cell may only touch files inside this directory.\n",
        encoding="utf-8",
    )
    (root / "memory").mkdir()
    (root / "memory" / "notes.md").write_text("# Session notes\n", encoding="utf-8")
    return str(root)


def _inside(root: Path, user_path: str) -> Path | None:
    if not user_path or "\x00" in user_path:
        return None
    raw = user_path.strip()
    if raw.startswith("~") or raw.startswith("/") or raw.startswith("\\"):
        return None
    root_r = root.resolve()
    try:
        candidate = (root_r / raw).resolve()
        candidate.relative_to(root_r)
    except (OSError, ValueError):
        return None
    return candidate


def propose(goal: str) -> dict:
    """Turn a goal into commentary plus typed actions. Does not refuse."""
    text = goal or ""
    low = text.lower()
    actions: list[dict] = []

    if ".ssh" in low or "id_rsa" in low or "/etc/" in low or "passwd" in low:
        path = "/etc/passwd" if ("/etc/" in low or "passwd" in low) else "~/.ssh/id_rsa"
        actions.append({"tool": "fs.read", "args": {"path": path}})

    urls = _URL.findall(text)
    if urls or any(w in low for w in ("curl", "wget", "fetch", "http://", "https://")):
        actions.append(
            {"tool": "net.fetch", "args": {"url": urls[0] if urls else "https://example.invalid/exfil"}}
        )

    if any(w in low for w in ("email", "e-mail", "send mail", "mail ")):
        actions.append(
            {"tool": "mail.send", "args": {"to": "ops@example.invalid", "body": text[:240]}}
        )

    writes = []
    if any(w in low for w in ("write", "create", "save", "summarize", "summary", "note")):
        named = [p for p in _REL_FILE.findall(text) if not p.startswith("/") and ".." not in p.split("/")]
        target = named[0] if named else "notes/goal.txt"
        writes.append(target)
        actions.append(
            {
                "tool": "fs.write",
                "args": {"path": target, "content": text.strip()[:500] or "empty goal"},
            }
        )

    if ".." in text:
        # Propose the traversal literally so the policy, not the parser, stops it.
        trav = next((tok for tok in text.split() if ".." in tok), "notes/../../etc/passwd")
        actions.append({"tool": "fs.read", "args": {"path": trav.strip("'\"")}})

    if any(w in low for w in ("list", "ls ", "files")) or not actions:
        actions.append({"tool": "fs.list", "args": {"path": "."}})

    commentary = (
        "The goal text names these tool calls. "
        "This proposer does not decide permission."
    )
    return {"commentary": commentary, "actions": actions, "writes": writes}


@dataclass
class Step:
    stage: str
    status: str
    detail: str


@dataclass
class RunResult:
    steps: list[Step] = field(default_factory=list)
    files: str = ""
    workspace: str = ""
    decision: str = ""

    def markdown(self) -> str:
        lines = [
            f"**Fingerprint** `{fingerprint()[:16]}` · proposer `{PROPOSER_ID}`",
            f"**Decision** {self.decision}",
            "",
            "| Stage | Status | Detail |",
            "|---|---|---|",
        ]
        for s in self.steps:
            detail = s.detail.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {s.stage} | {s.status} | {detail} |")
        return "\n".join(lines)


def _graph_hash(nodes: list[dict]) -> str:
    blob = json.dumps(nodes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _verify(action: dict, commentary: str) -> str | None:
    tool = action.get("tool")
    if tool not in TOOLS:
        return "unknown_tool"
    if not isinstance(action.get("args"), dict):
        return "bad_args"
    if TOOLS[tool] != "read" and not commentary.strip():
        return "missing_commentary"
    return None


def _sentinel(action: dict, root: Path, card: bool) -> tuple[str, str]:
    tool = action["tool"]
    args = action["args"]
    kind = TOOLS[tool]
    if kind == "network":
        return "deny", "network_default_deny"
    if tool == "mail.send":
        if not card:
            return "deny", "card_required"
        return "allow", "card_accepted_local_outbox_only"
    path = str(args.get("path", "."))
    if _inside(root, path) is None:
        return "deny", "path_outside_workspace"
    name = Path(path).name
    if name in {".env", "id_rsa", "id_ed25519"} or name.endswith(".pem"):
        return "deny", "secret_filename"
    if kind in {"read", "write"}:
        return "allow", "workspace_scope"
    return "deny", "fail_closed"


def _execute(action: dict, root: Path) -> str:
    tool = action["tool"]
    args = action["args"]
    if tool == "fs.list":
        target = _inside(root, str(args.get("path", ".")))
        if target is None or not target.is_dir():
            return "not a directory"
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
        return "\n".join(names) or "(empty)"
    if tool == "fs.read":
        target = _inside(root, str(args["path"]))
        if target is None or not target.is_file():
            return "not a file"
        return target.read_text(encoding="utf-8")[:2000]
    if tool == "fs.write":
        target = _inside(root, str(args["path"]))
        if target is None:
            return "refused"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(args.get("content", "")), encoding="utf-8")
        return f"wrote {target.relative_to(root.resolve())} ({target.stat().st_size} bytes)"
    if tool == "mail.send":
        out = root / "outbox"
        out.mkdir(exist_ok=True)
        dest = out / "message.txt"
        dest.write_text(
            f"to: {args.get('to','')}\n\n{args.get('body','')}\n",
            encoding="utf-8",
        )
        return "queued inside workspace outbox; nothing left the machine"
    return "no executor"


def _list_tree(root: Path) -> str:
    lines = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            lines.append(str(p.relative_to(root)))
    return "\n".join(lines) or "(empty)"


def run(goal: str, workspace: str | None = None, card: bool = False) -> RunResult:
    root = Path(workspace) if workspace else Path(new_workspace())
    root.mkdir(parents=True, exist_ok=True)
    result = RunResult(workspace=str(root))
    proposal = propose(goal)
    commentary = proposal["commentary"]

    nodes = [
        {"id": "goal", "status": "done", "desc": (goal or "")[:180]},
    ]
    parent = _graph_hash([])
    nodes[0]["parent"] = parent

    result.steps.append(
        Step(
            "goal",
            "done",
            f"graph { _graph_hash(nodes)[:12] } parent {parent[:12]}",
        )
    )
    result.steps.append(
        Step(
            "skills",
            "done",
            "attached " + ", ".join(sorted({a['tool'] for a in proposal['actions']})),
        )
    )
    result.steps.append(Step("commentary", "recorded", commentary))

    allows = 0
    denies = 0
    for i, action in enumerate(proposal["actions"], start=1):
        node_id = f"a{i}"
        verr = _verify(action, commentary)
        if verr:
            nodes.append({"id": node_id, "status": "failed", "reason": verr, "parent": _graph_hash(nodes)})
            result.steps.append(Step("verifier", "reject", f"{action['tool']} {verr}"))
            denies += 1
            continue
        result.steps.append(Step("verifier", "pass", f"{action['tool']} schema ok"))
        decision, reason = _sentinel(action, root, card)
        digest = hashlib.sha256(
            json.dumps(action, sort_keys=True).encode()
        ).hexdigest()[:12]
        if decision != "allow":
            nodes.append(
                {
                    "id": node_id,
                    "status": "failed",
                    "reason": reason,
                    "parent": _graph_hash(nodes),
                }
            )
            result.steps.append(
                Step("sentinel", "deny", f"{action['tool']} {reason} digest {digest}")
            )
            denies += 1
            continue
        # Cell runs only an already admitted action. It cannot ask again.
        output = _execute(action, root)
        nodes.append(
            {
                "id": node_id,
                "status": "done",
                "reason": reason,
                "parent": _graph_hash(nodes),
            }
        )
        result.steps.append(
            Step("cell", "ran", f"{action['tool']} {reason}: {output[:180]}")
        )
        allows += 1

    # Memory file is host-written, user-visible, not a KV cache.
    note = root / "memory" / "notes.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    if not note.exists():
        note.write_text("# Session notes\n", encoding="utf-8")
    with note.open("a", encoding="utf-8") as fh:
        fh.write(f"\n- goal recorded, allows={allows}, denies={denies}\n")

    result.steps.append(
        Step("memory", "appended", "memory/notes.md (file store, not a vector index)")
    )
    result.files = _list_tree(root)
    result.decision = f"{allows} admitted, {denies} stopped"
    blob = result.markdown() + result.files
    if CANARY in blob or CANARY in result.files:
        raise RuntimeError("canary leaked into the cell trace")
    return result
