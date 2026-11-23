"""Pure, non-executing Serverspace RU vStack power/task contract.

Source of paths: Serverspace s2ctl SDK (ssclient.server.power.ServerPowerService,
ssclient.task.TaskService). No network client and no API credentials in this
module. A future caller must enforce separate owner authorization and obtain
the server ID only inside Cloudflare, never through public Actions request files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SERVER_ID = re.compile(r"^l[0-9]+s[0-9]+$")
TASK_ID = re.compile(r"^[a-zA-Z0-9_-]{3,80}$")
ALLOWED = frozenset(("on", "shutdown", "reboot", "off", "reset"))
DISRUPTIVE = frozenset(("off", "reset"))
KNOWN_TASK_STATES = frozenset(("New","InProgress","Completed","Failed","Canceled"))

class ContractError(ValueError):
    """A fixed-code failure; never include identifying provider data in text."""

@dataclass(frozen=True)
class PowerPlan:
    decision: str
    method: str | None
    endpoint: str | None
    action: str

    def public_summary(self) -> dict[str, str]:
        # The endpoint may carry a server identifier and MUST stay private.
        return {"decision":self.decision,"action":self.action}

def sole_server(servers: Any) -> tuple[str,bool]:
    if not isinstance(servers,list) or len(servers)!=1:
        raise ContractError("TARGET_AMBIGUOUS")
    server=servers[0]
    if not isinstance(server,dict):
        raise ContractError("SERVER_SCHEMA")
    server_id=server.get("id")
    power=server.get("is_power_on")
    if not isinstance(server_id,str) or not SERVER_ID.fullmatch(server_id):
        raise ContractError("SERVER_ID_SCHEMA")
    if type(power) is not bool:
        raise ContractError("POWER_STATE_UNKNOWN")
    return server_id,power

def plan_sole_server_power(action: str, servers: Any, *,
                           force_allowed: bool=False) -> PowerPlan:
    """Return a plan, not an operation; only a unique provider server qualifies.

    'off' and 'reset' are hard power operations and require separate explicit
    permission. This module never executes POST, even with force_allowed=True.
    """
    if not isinstance(action,str) or action not in ALLOWED:
        raise ContractError("OPERATION_REFUSED")
    server_id,is_on=sole_server(servers)
    if action in DISRUPTIVE and not force_allowed:
        raise ContractError("HARD_POWER_NOT_AUTHORIZED")
    if action=="on" and is_on:
        return PowerPlan("no_change",None,None,action)
    if action in ("shutdown","off") and not is_on:
        return PowerPlan("no_change",None,None,action)
    if action in ("reboot","reset") and not is_on:
        raise ContractError("SERVER_NOT_POWERED_ON")
    return PowerPlan("ready","POST",f"/api/v1/servers/{server_id}/power/{action}",action)

def task_status(raw: Any) -> dict[str,object]:
    """Strictly whitelist progress, no task/server/resource IDs, errors, secrets."""
    if not isinstance(raw,dict) or not isinstance(raw.get("task"),dict):
        raise ContractError("TASK_SCHEMA")
    item=raw["task"]
    state=item.get("is_completed")
    if state not in KNOWN_TASK_STATES:
        raise ContractError("TASK_STATE_UNKNOWN")
    progress=item.get("progress_percent")
    if progress is not None and (type(progress) is not int or not 0<=progress<=100):
        raise ContractError("TASK_PROGRESS_INVALID")
    return {"state":state,"progress_percent":progress,
            "terminal":state in ("Completed","Failed","Canceled")}

def validate_task_id(value: Any) -> str:
    if not isinstance(value,str) or not TASK_ID.fullmatch(value):
        raise ContractError("TASK_ID_INVALID")
    return value
