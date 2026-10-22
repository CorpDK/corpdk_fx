from __future__ import annotations

import frappe

from corpdk_fx.services.rate_resolver import (
	apply_pair_to_sales_invoice,
	find_pair_for_sales_invoice,
	resolve_for_pair,
)


def apply_reimb_usd_lines(doc) -> None:
	"""USD rate on reimb lines = reimb_inr_amount ÷ FBIL(reimb_fx_date); header rate unchanged here."""
	meta = frappe.get_meta("Sales Invoice Item")
	if not meta.has_field("reimb_inr_amount") or not meta.has_field("reimb_fx_date"):
		return
	if doc.currency != "USD":
		return

	pair = find_pair_for_sales_invoice(doc)
	pair_name = pair.name if pair else "USD-INR"

	for row in doc.items:
		inr = row.get("reimb_inr_amount")
		fx_date = row.get("reimb_fx_date")
		if not inr or not fx_date:
			continue
		quote = resolve_for_pair(pair_name, posting_date=str(fx_date), use_cache=False)
		row.rate = round(float(inr) / quote.rate, 2)
		row.qty = row.qty or 1


def before_save(doc, method=None) -> None:
	if doc.doctype != "Sales Invoice" or doc.docstatus != 0:
		return
	apply_reimb_usd_lines(doc)


def before_submit(doc, method=None) -> None:
	if doc.docstatus != 0:
		return
	apply_reimb_usd_lines(doc)
	pair = find_pair_for_sales_invoice(doc)
	if not pair:
		return
	apply_pair_to_sales_invoice(doc, pair, persist_remarks=True)
	doc.run_method("calculate_taxes_and_totals")
