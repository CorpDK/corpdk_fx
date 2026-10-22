"""Desk app launcher permission (v16 apps screen)."""

import frappe


def has_app_permission() -> bool:
	if frappe.session.user == "Guest":
		return False
	if "System Manager" in frappe.get_roles():
		return True
	return frappe.has_permission("CorpDK FX Pair", ptype="read") or frappe.has_permission(
		"Sales Invoice", ptype="read"
	)
