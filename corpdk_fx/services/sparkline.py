from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from frappe.utils import today

from corpdk_fx.services.frankfurter_v2 import blended_rates_series, provider_rates_series
from corpdk_fx.services.fx_quote import parse_date
from corpdk_fx.services.providers import FRANKFURTER_PROVIDER_KEYS

if TYPE_CHECKING:
	from corpdk_fx.corpdk_fx.doctype.corpdk_fx_pair.corpdk_fx_pair import CorpDKFXPair

SPARKLINE_DAYS = 30


def monthly_rate_series(pair: "CorpDKFXPair", days: int = SPARKLINE_DAYS) -> list[float]:
	"""Daily rates for the last `days` (oldest → newest) for dashboard sparklines."""
	end = parse_date(today())
	start = end - timedelta(days=max(days - 1, 0))
	rows = _fetch_series_rows(pair, start, end)
	if not rows:
		return []
	by_date: dict[str, float] = {}
	for row in rows:
		d = str(row.get("date") or row.get("effective_date") or "")[:10]
		if not d:
			continue
		try:
			by_date[d] = round(float(row["rate"]), 6)
		except (KeyError, TypeError, ValueError):
			continue
	if not by_date:
		return []

	rates: list[float] = []
	last = None
	d = start
	while d <= end:
		key = d.isoformat()
		if key in by_date:
			last = by_date[key]
		if last is not None:
			rates.append(last)
		d += timedelta(days=1)
	return rates


def _fetch_series_rows(pair: "CorpDKFXPair", start, end) -> list[dict]:
	import frappe

	provider = pair.provider or ""
	fc, tc = pair.from_currency, pair.to_currency

	if provider == "Frankfurter Blended":
		raw = blended_rates_series(fc, tc, start, end)
		return [{"date": r["date"], "rate": r["rate"]} for r in raw]

	if provider in ("FBIL Frankfurter", "ECB Frankfurter", "Frankfurter (provider key)"):
		key = (pair.frankfurter_provider_key or FRANKFURTER_PROVIDER_KEYS.get(provider) or "").strip()
		if not key:
			return []
		raw = provider_rates_series(fc, tc, start, end, key)
		return [{"date": r["date"], "rate": r["rate"]} for r in raw]

	if provider in ("Currency Exchange", "ERPNext Default"):
		ex = frappe.get_all(
			"Currency Exchange",
			filters={
				"from_currency": fc,
				"to_currency": tc,
				"date": ("between", [start.isoformat(), end.isoformat()]),
			},
			fields=["date", "exchange_rate as rate"],
			order_by="date asc",
		)
		if ex:
			return ex
		# Fallback: Frankfurter blended if site has no history
		raw = blended_rates_series(fc, tc, start, end)
		return [{"date": r["date"], "rate": r["rate"]} for r in raw]

	return []
