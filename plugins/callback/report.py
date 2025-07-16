# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type
import os
import re
import tempfile
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import humanize
import pandas as pd
from ansible.plugins.callback import CallbackBase
from jinja2 import Environment, FileSystemLoader


class CallbackModule(CallbackBase):
    """
    This callback module pretty-prints the host report for Fogo validator nodes.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "aggregate"
    CALLBACK_NAME = "firstset.common_operations.report"

    # only needed if you ship it and don't want to enable by default
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self):
        super().__init__()
        self.summary = pd.DataFrame(
            columns=pd.MultiIndex.from_tuples([("Kernel", ""), ("Uptime", "")])
        )
        self.summary.index.name = "host"

    def v2_runner_on_ok(self, result):
        role = getattr(result._task, "_role", None)
        if str(role) == "firstset.common_operations.common":
            match str(result.task_name):
                case "Collect kernel version":
                    self.summary.loc[result._host.get_name(), ("Kernel", "")] = (
                        result._result["stdout"]
                    )

                case "Collect OS uptime":
                    self.summary.loc[result._host.get_name(), ("Uptime", "")] = (
                        result._result["stdout"].replace("up ", "")
                    )

                case "Collect state + status only for requested units":
                    for r in result._result.get("results", []):
                        service_info = "{active_state} {unit_file_state} <span title='{uptime}'>🕙</span>"
                        active_enter_time = r["stdout_lines"][2]
                        dt = datetime.strptime(
                            active_enter_time, "%a %Y-%m-%d %H:%M:%S %Z"
                        )
                        dt = dt.replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        delta = now - dt
                        uptime = humanize.precisedelta(delta, minimum_unit="minutes")
                        self.summary.loc[
                            result._host.get_name(), ("Services", r["item"])
                        ] = service_info.format(
                            active_state=r["stdout_lines"][0],
                            unit_file_state=r["stdout_lines"][1],
                            uptime=uptime,
                        )

                # case "Get log tail for services":
                #     print(result._result.get("results", []))

                case "Get binary versions":
                    version_pattern = r"\bv?\d+\.\d+\.\d+(?:[-_][\w\d]+)?\b"
                    for r in result._result.get("results", []):
                        version = "unknown"
                        match = re.search(version_pattern, r["stdout"])
                        if match:
                            version = match.group()
                        self.summary.loc[
                            result._host.get_name(), ("Binaries", r["item"]["key"])
                        ] = version

                case "Set fact host_report":
                    facts = result._result.get("ansible_facts", {})
                    report = facts.get("host_report", {})
                    self._display.display(
                        f"[{result._host.get_name()}] HOST REPORT:\n{report}"
                    )
        else:
            return

    def playbook_on_stats(self, _):
        # Generate and save HTML table
        table_html = self.summary.to_html(border=1, justify="center", escape=False)

        # Dynamically locate the template relative to this file
        this_dir = os.path.dirname(__file__)
        env = Environment(loader=FileSystemLoader(this_dir))
        template = env.get_template("check_fleet_report_template.html.j2")
        rendered_html = template.render(table_html=table_html)

        # Construct a reusable file in the OS temp directory
        report_path = Path(tempfile.gettempdir()) / "check_fleet_report.html"
        report_path.write_text(rendered_html, encoding="utf-8")

        # Open in default browser
        webbrowser.open(f"file://{report_path}")
