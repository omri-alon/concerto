"""GUS (Salesforce ADM_Work__c) client via the `sf` CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from datetime import datetime

from .models import Issue

logger = logging.getLogger("concerto.gus")


def _parse_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _priority_to_int(val: str | None) -> int | None:
    """GUS Priority__c is 'P0'..'P4'; map to 0..4."""
    if not val:
        return None
    s = str(val).strip().upper()
    if s.startswith("P") and s[1:].isdigit():
        return int(s[1:])
    try:
        return int(s)
    except ValueError:
        return None


def _instance_url(target_org: str) -> str:
    """Best-effort Lightning base URL for link building. Falls back to gus."""
    if target_org and "." in target_org:
        return target_org.rstrip("/")
    return "https://gus.my.salesforce.com"


def _build_issue_url(instance_url: str, record_id: str) -> str:
    return f"{instance_url}/lightning/r/ADM_Work__c/{record_id}/view"


def _normalize_work(row: dict, instance_url: str) -> Issue:
    return Issue(
        id=row["Id"],
        identifier=row.get("Name", ""),
        title=row.get("Subject__c", "") or "",
        description=(
            row.get("Details_and_Steps_to_Reproduce__c")
            or row.get("Details__c")
            or row.get("Description__c")
        ),
        priority=_priority_to_int(row.get("Priority__c")),
        state=row.get("Status__c", "") or "",
        branch_name=row.get("Branch__c"),
        url=_build_issue_url(instance_url, row["Id"]),
        created_at=_parse_datetime(row.get("CreatedDate")),
        updated_at=_parse_datetime(row.get("LastModifiedDate")),
    )


class GusClient:
    """Async wrapper over the `sf` CLI against a GUS-aliased Salesforce org.

    Mirrors the method surface of the old LinearClient so the orchestrator
    is transport-agnostic. All blocking CLI work runs in a thread pool.

    Comments are posted as ADM_Comment__c child records (Body__c + Work__c),
    which is GUS's native comment object. The HTML-comment tracking markers
    embedded by concerto.tracking survive round-trip verbatim.
    """

    WORK_FIELDS = (
        "Id, Name, Subject__c, Status__c, Priority__c, Branch__c, "
        "Details__c, Details_and_Steps_to_Reproduce__c, Description__c, "
        "CreatedDate, LastModifiedDate, Scrum_Team__c, Scrum_Team_Name__c"
    )

    def __init__(
        self,
        target_org: str,
        scrum_team: str,
        current_sprint_only: bool = False,
        assignee: str = "",
    ):
        """
        target_org: `sf` org alias (e.g. "gus") or full instance URL.
        scrum_team: scope filter — either an ADM_Scrum_Team__c Id or a team Name.
        current_sprint_only: if True, restrict candidates to the team's
            currently-active sprint (TODAY between Start_Date__c and End_Date__c).
        assignee: optional Assignee__r.Username filter. Special value "me"
            resolves to the running user via `sf org display`. Empty disables.
        """
        self.target_org = target_org or "gus"
        self.scrum_team = scrum_team
        self.current_sprint_only = current_sprint_only
        self.assignee = assignee
        self._resolved_assignee: str | None = None
        self.instance_url = _instance_url(self.target_org)

    async def close(self) -> None:
        return None

    # ── CLI plumbing ────────────────────────────────────────────────────────

    async def _run_sf(self, args: list[str]) -> dict:
        cmd = ["sf", *args, "--target-org", self.target_org, "--json"]
        logger.debug("sf cmd: %s", " ".join(shlex.quote(a) for a in cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"sf CLI failed (exit {proc.returncode}): "
                f"{stderr.decode(errors='replace')[:800]}"
            )
        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"sf CLI returned non-JSON: {e}: {stdout[:200]!r}")

    async def _soql(self, query: str) -> list[dict]:
        payload = await self._run_sf(["data", "query", "--query", query])
        result = payload.get("result", {}) or {}
        return result.get("records", []) or []

    async def _resolve_assignee_username(self) -> str:
        """Resolve self.assignee to a concrete Username. "me" → running user."""
        if self._resolved_assignee is not None:
            return self._resolved_assignee
        if not self.assignee:
            self._resolved_assignee = ""
            return ""
        if self.assignee.strip().lower() == "me":
            payload = await self._run_sf(["org", "display"])
            username = (payload.get("result") or {}).get("username") or ""
            if not username:
                raise RuntimeError(
                    "Could not resolve assignee=me: `sf org display` returned no username"
                )
            self._resolved_assignee = username
            logger.info("Resolved assignee=me to %s", username)
        else:
            self._resolved_assignee = self.assignee
        return self._resolved_assignee

    async def _scope_clause(self) -> str:
        """SOQL fragment filtering to scrum team / sprint / assignee."""
        parts: list[str] = []
        if self.scrum_team:
            val = self.scrum_team.replace("'", r"\'")
            if len(val) in (15, 18) and " " not in val:
                parts.append(f"Scrum_Team__c = '{val}'")
            else:
                parts.append(f"Scrum_Team__r.Name = '{val}'")
        if self.current_sprint_only:
            parts.append(
                "Sprint__r.Start_Date__c <= TODAY "
                "AND Sprint__r.End_Date__c >= TODAY"
            )
        username = await self._resolve_assignee_username()
        if username:
            esc = username.replace("'", r"\'")
            parts.append(f"Assignee__r.Username = '{esc}'")
        return ("" if not parts else " AND " + " AND ".join(parts))

    # ── Candidate fetch ─────────────────────────────────────────────────────

    async def fetch_candidate_issues(
        self, scrum_team: str, active_statuses: list[str]
    ) -> list[Issue]:
        if not active_statuses:
            return []
        in_list = ", ".join(f"'{s}'" for s in active_statuses)
        q = (
            f"SELECT {self.WORK_FIELDS} FROM ADM_Work__c "
            f"WHERE Status__c IN ({in_list})"
            f"{await self._scope_clause()} "
            f"ORDER BY Priority__c ASC NULLS LAST, CreatedDate ASC "
            f"LIMIT 500"
        )
        rows = await self._soql(q)
        return [_normalize_work(r, self.instance_url) for r in rows]

    async def fetch_issue_states_by_ids(
        self, issue_ids: list[str]
    ) -> dict[str, str]:
        if not issue_ids:
            return {}
        in_list = ", ".join(f"'{i}'" for i in issue_ids)
        q = f"SELECT Id, Status__c FROM ADM_Work__c WHERE Id IN ({in_list})"
        rows = await self._soql(q)
        return {r["Id"]: (r.get("Status__c") or "") for r in rows}

    async def fetch_issues_by_states(
        self, scrum_team: str, states: list[str]
    ) -> list[Issue]:
        if not states:
            return []
        in_list = ", ".join(f"'{s}'" for s in states)
        q = (
            f"SELECT Id, Name, Subject__c, Status__c FROM ADM_Work__c "
            f"WHERE Status__c IN ({in_list}){await self._scope_clause()} LIMIT 500"
        )
        rows = await self._soql(q)
        return [
            Issue(
                id=r["Id"],
                identifier=r.get("Name", ""),
                title=r.get("Subject__c", "") or "",
                state=r.get("Status__c", "") or "",
                url=_build_issue_url(self.instance_url, r["Id"]),
            )
            for r in rows
        ]

    # ── Comments (ADM_Comment__c) ───────────────────────────────────────────

    async def post_comment(self, issue_id: str, body: str) -> bool:
        try:
            values = f"Work__c={issue_id} Body__c={json.dumps(body)}"
            await self._run_sf([
                "data", "create", "record",
                "--sobject", "ADM_Comment__c",
                "--values", values,
            ])
            return True
        except Exception as e:
            logger.error(f"Failed to post comment on {issue_id}: {e}")
            return False

    async def fetch_comments(self, issue_id: str) -> list[dict]:
        try:
            q = (
                f"SELECT Id, Body__c, CreatedDate FROM ADM_Comment__c "
                f"WHERE Work__c = '{issue_id}' ORDER BY CreatedDate ASC"
            )
            rows = await self._soql(q)
            return [
                {
                    "id": r["Id"],
                    "body": r.get("Body__c") or "",
                    "createdAt": r.get("CreatedDate"),
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to fetch comments for {issue_id}: {e}")
            return []

    # ── Status updates ──────────────────────────────────────────────────────

    async def update_issue_state(self, issue_id: str, state_name: str) -> bool:
        try:
            await self._run_sf([
                "data", "update", "record",
                "--sobject", "ADM_Work__c",
                "--record-id", issue_id,
                "--values", f"Status__c={json.dumps(state_name)}",
            ])
            logger.info(f"Moved {issue_id} to status '{state_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to update status for {issue_id}: {e}")
            return False
