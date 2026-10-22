"""Require Frappe / ERPNext v16 (bench native for this app release)."""

from __future__ import annotations

import erpnext
import frappe
from packaging import version

MIN_FRAPPE = "16.0.0"
MIN_ERPNEXT = "16.0.0"


def execute() -> None:
	_check("Frappe", frappe.__version__, MIN_FRAPPE)
	_check("ERPNext", erpnext.__version__, MIN_ERPNEXT)


def _check(app_label: str, current: str, minimum: str) -> None:
	if version.parse(current) < version.parse(minimum):
		frappe.throw(
			f"{app_label} {current} is below the minimum for CorpDK FX 1.x ({minimum}+). "
			f"Upgrade {app_label} or install an older corpdk_fx release built for v15."
		)
