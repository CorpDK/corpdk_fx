from __future__ import annotations

import frappe

SERVER_SCRIPT_LEGACY = "CorpDK Export USD-INR on Submit"

CUSTOM_FIELDS: list[dict] = [
	{
		"dt": "Sales Invoice",
		"fieldname": "export_usd_inr_policy",
		"label": "Export USD/INR Policy",
		"fieldtype": "Data",
		"insert_after": "conversion_rate",
		"read_only": 1,
		"no_copy": 1,
	},
	{
		"dt": "Sales Invoice",
		"fieldname": "export_usd_inr_effective_date",
		"label": "Export USD/INR FBIL Date",
		"fieldtype": "Date",
		"insert_after": "export_usd_inr_policy",
		"read_only": 1,
		"no_copy": 1,
	},
	{
		"dt": "Sales Invoice",
		"fieldname": "export_usd_inr_rate_source",
		"label": "Export USD/INR Feed",
		"fieldtype": "Data",
		"insert_after": "export_usd_inr_effective_date",
		"read_only": 1,
		"no_copy": 1,
	},
	{
		"dt": "Sales Invoice Item",
		"fieldname": "reimb_inr_amount",
		"label": "Reimb INR (paid)",
		"fieldtype": "Float",
		"insert_after": "amount",
		"description": "INR outlay at cost; with Reimb FX date, USD rate = INR ÷ FBIL(date X)",
		"precision": "2",
	},
	{
		"dt": "Sales Invoice Item",
		"fieldname": "reimb_fx_date",
		"label": "Reimb FX date",
		"fieldtype": "Date",
		"insert_after": "reimb_inr_amount",
		"description": "Date X for FBIL when converting reimb INR to USD (payment / supplier invoice date)",
	},
]

DEFAULT_PAIR = {
	"pair_code": "USD-INR",
	"enabled": 1,
	"from_currency": "USD",
	"to_currency": "INR",
	"provider": "FBIL Frankfurter",
	"company": "CorpDK",
	"lookback_days": 14,
	"policy_label": "FBIL USD/INR reference (Rule 34(2) export services)",
	"apply_on_sales_invoice_submit": 1,
	"require_export_naming": 1,
	"naming_series_contains": "CDK-EXP",
}


def _ensure_custom_fields() -> None:
	for row in CUSTOM_FIELDS:
		dt = row["dt"]
		fieldname = row["fieldname"]
		name = f"{dt}-{fieldname}"
		if frappe.db.exists("Custom Field", name):
			continue
		cf = frappe.new_doc("Custom Field")
		cf.dt = dt
		cf.update({k: v for k, v in row.items() if k != "dt"})
		cf.insert(ignore_permissions=True)


def _remove_legacy_server_script() -> None:
	if not frappe.db.exists("Server Script", SERVER_SCRIPT_LEGACY):
		return
	frappe.delete_doc("Server Script", SERVER_SCRIPT_LEGACY, force=1)


def _remove_legacy_site_module() -> None:
	from pathlib import Path

	path = Path(frappe.get_site_path("private", "files", "corpdk_export_usd_inr.py"))
	if path.is_file():
		path.unlink()


def _ensure_default_pair() -> None:
	if frappe.db.exists("CorpDK FX Pair", DEFAULT_PAIR["pair_code"]):
		return
	doc = frappe.new_doc("CorpDK FX Pair")
	doc.update(DEFAULT_PAIR)
	doc.insert(ignore_permissions=True)


def after_install() -> None:
	_ensure_custom_fields()
	_remove_legacy_server_script()
	_remove_legacy_site_module()


def after_migrate() -> None:
	_ensure_custom_fields()
	_remove_legacy_server_script()
	_remove_legacy_site_module()
	_ensure_default_pair()
