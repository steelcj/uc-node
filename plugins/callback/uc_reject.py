"""uc_reject: record a node uc-node cannot secure in the client log."""
from __future__ import annotations

DOCUMENTATION = r"""
name: uc_reject
type: notification
short_description: Record a node uc-node cannot secure in the client log
description:
  - When a task fails, or a host is unreachable, while the host is in the C(raw_node) group, and the
    failure is not ignored or rescued, writes one rejection to the client log at the end of the run,
    C(<parent of uc_client_inventory>/logs/rejected/<YYYY-MM-DD--HH-MM-SS>-rejected-uc-node-cannot-be-secured.yml),
    with the entry fields of uc-contracts' node lifecycle overview. C(logs/rejected/) is created, mode 0700,
    when it is missing.
  - The entry names the step, the play and task that failed, and the contract clauses that task names, or
    that the confirmation's check found failing. It never holds the task's error message, which may hold
    output from the node.
  - A rejected build leaves no candidate. The node's C(<uc_client_inventory>/candidates/<node>.yml) is
    removed, and the callback says so.
  - A failure before the node is in C(raw_node), such as a node definition the check play refuses, is not
    a rejection, since there is no node, and writes nothing.
  - Takes C(uc_client_inventory) and C(raw_node_batch) from the extra variables, which scripts/build passes.
    It changes nothing in the run's output beyond saying what it wrote.
requirements:
  - Enabled with C(callbacks_enabled = uc_reject) in ansible.cfg.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from ansible.plugins.callback import CallbackBase

GROUP = "raw_node"
CONTROLLER = "uc-node"
REASON = "cannot-be-secured"
# A contract clause identifier, such as RN-ACC-07, as a task name gives it.
CLAUSE = re.compile(r"\bRN-[A-Z]+-[0-9]{2}\b")
# Facts the build sets for this callback: tasks/confirmation.yml sets both.
FINGERPRINT_FACT = "uc_node_fingerprint"
CLAUSES_FACT = "uc_reject_clauses"


def quoted(value) -> str:
    """A YAML double-quoted scalar: a JSON string is one."""
    return json.dumps("" if value is None else str(value))


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "notification"
    CALLBACK_NAME = "uc_reject"
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_vars = {}
        self._play_name = ""
        self._failures = {}
        self._facts = {}

    # --- what the run tells the callback --------------------------------

    def v2_playbook_on_play_start(self, play):
        self._play_name = play.get_name().strip()
        manager = play.get_variable_manager()
        if manager is not None:
            self._extra_vars = dict(manager.extra_vars)

    def v2_runner_on_ok(self, result):
        facts = result._result.get("ansible_facts") or {}
        host = result._host.get_name()
        for name in (FINGERPRINT_FACT, CLAUSES_FACT):
            if name in facts:
                self._facts.setdefault(host, {})[name] = facts[name]

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if not ignore_errors:
            self._record(result)

    def v2_runner_on_unreachable(self, result):
        self._record(result)

    def v2_playbook_on_stats(self, stats):
        for host, failure in self._failures.items():
            summary = stats.summarize(host)
            if summary.get("failures", 0) or summary.get("unreachable", 0):
                self._reject(host, failure)

    # --- recording -------------------------------------------------------

    def _record(self, result):
        host = result._host
        if GROUP not in [group.name for group in host.get_groups()]:
            return
        task = (getattr(result, "task_name", None) or result._task.get_name() or "").strip()
        self._failures[host.get_name()] = {
            "step": f"{self._play_name}: {task}" if self._play_name else task,
            "task_clauses": CLAUSE.findall(task),
        }

    def _reject(self, host, failure):
        inventory = self._extra_vars.get("uc_client_inventory")
        if not isinstance(inventory, str) or not os.path.isabs(inventory):
            self._display.warning(
                f"uc_reject: {host} could not be secured, but uc_client_inventory is not an absolute "
                "path, so no rejection was written.")
            return
        inventory = Path(inventory)
        facts = self._facts.get(host, {})
        found = facts.get(CLAUSES_FACT) or []
        clauses = sorted(set(failure["task_clauses"])
                         | {str(c) for c in found if isinstance(c, str) and CLAUSE.fullmatch(c)})
        fingerprint = facts.get(FINGERPRINT_FACT) or ""

        log = inventory.parent / "logs" / "rejected"
        try:
            for directory in (log.parent, log):
                if not directory.exists():
                    directory.mkdir(mode=0o700)
                    directory.chmod(0o700)
            path = self._write(log, host, failure["step"], clauses, fingerprint)
        except OSError as error:
            self._display.warning(f"uc_reject: could not write the rejection of {host} in {log}: {error}")
            return
        self._display.warning(f"uc_reject: {host} could not be secured. Rejection written to {path}")

        candidate = inventory / "candidates" / f"{host}.yml"
        if candidate.is_file() or candidate.is_symlink():
            try:
                candidate.unlink()
                self._display.warning(
                    f"uc_reject: removed the candidate {candidate}, since a rejected build leaves none.")
            except OSError as error:
                self._display.warning(f"uc_reject: could not remove the candidate {candidate}: {error}")

    def _write(self, log, host, step, clauses, fingerprint):
        """Write the entry once, never over another. Names are by the second,
        so a name already taken waits for the next second."""
        for _ in range(5):
            now = datetime.now().astimezone().replace(microsecond=0)
            path = log / f"{now:%Y-%m-%d--%H-%M-%S}-rejected-{CONTROLLER}-{REASON}.yml"
            text = (
                f"# {path.name}\n"
                "# Written by uc-node's uc_reject callback: a node uc-node could not secure.\n"
                f"node: {quoted(host)}\n"
                f"rejected: {quoted(now.isoformat())}\n"
                f"controller: {quoted(CONTROLLER)}\n"
                f"step: {quoted(step)}\n"
                f"reason: {quoted(REASON)}\n"
                f"clauses: {json.dumps(clauses)}\n"
                f"fingerprint: {quoted(fingerprint)}\n"
                f"raw_node_batch: {quoted(self._extra_vars.get('raw_node_batch'))}\n"
            )
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                time.sleep(1)
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(text)
            return path
        raise OSError("every name for the last five seconds is taken")
