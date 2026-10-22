from __future__ import annotations

import frappe
from frappe.utils import today

from corpdk_fx.services.rate_resolver import (
	list_enabled_pairs,
	refresh_pair_cache,
	resolve_for_pair,
)
from corpdk_fx.services.sparkline import monthly_rate_series


@frappe.whitelist()
def get_dashboard() -> list[dict]:
	rows: list[dict] = []
	for name in list_enabled_pairs():
		pair = frappe.get_doc("CorpDK FX Pair", name)
		try:
			quote = resolve_for_pair(pair, posting_date=today(), use_cache=False)
		except Exception as exc:
			rows.append(
				{
					"pair": pair.name,
					"from_currency": pair.from_currency,
					"to_currency": pair.to_currency,
					"provider": pair.provider,
					"company": pair.company,
					"error": str(exc),
				}
			)
			continue
		rows.append(
			{
				"pair": pair.name,
				"from_currency": pair.from_currency,
				"to_currency": pair.to_currency,
				"provider": pair.provider,
				"company": pair.company,
				"rate": quote.rate,
				"effective_date": quote.effective_date,
				"posting_date": quote.posting_date,
				"source": quote.source,
				"feed": quote.provider,
				"sparkline": monthly_rate_series(pair),
			}
		)
	return rows


@frappe.whitelist()
def refresh_all_pairs() -> list[dict]:
	for name in list_enabled_pairs():
		refresh_pair_cache(name, posting_date=today())
	return get_dashboard()


@frappe.whitelist()
def refresh_pair(pair_name: str) -> dict:
	quote = refresh_pair_cache(pair_name, posting_date=today())
	return {
		"pair": pair_name,
		"rate": quote.rate,
		"effective_date": quote.effective_date,
		"feed": quote.provider,
	}
