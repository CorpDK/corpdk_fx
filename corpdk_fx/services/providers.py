from __future__ import annotations

from datetime import date, timedelta

from corpdk_fx.services.frankfurter_v2 import (
	blended_rate_on_date,
	blended_rates_series,
	latest_on_or_before,
	resolve_provider_rate,
)
from corpdk_fx.services.fx_quote import FxQuote, parse_date

# Desk Select label → Frankfurter /v2/providers/{key} (case-insensitive on API)
FRANKFURTER_PROVIDER_KEYS = {
	"FBIL Frankfurter": "fbil",
	"ECB Frankfurter": "ecb",
}


def _quote_from_row(
	row: dict,
	from_currency: str,
	to_currency: str,
	posting_date: str,
	source: str,
	provider_label: str,
) -> FxQuote:
	return FxQuote(
		rate=round(float(row["rate"]), 4),
		from_currency=from_currency,
		to_currency=to_currency,
		posting_date=posting_date,
		effective_date=str(row["date"]),
		source=source,
		provider=provider_label,
	)


def fetch_frankfurter_provider(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
	provider_key: str,
	lookback_days: int = 14,
	source: str | None = None,
) -> FxQuote | None:
	key = provider_key.strip().lower()
	row = resolve_provider_rate(
		from_currency,
		to_currency,
		for_date,
		key,
		lookback_days=lookback_days,
	)
	if not row:
		return None
	target = parse_date(for_date).isoformat()
	label = f"frankfurter.dev/v2/providers/{key}"
	return _quote_from_row(
		row,
		from_currency,
		to_currency,
		target,
		source or f"Frankfurter provider {key.upper()} reference",
		label,
	)


def fetch_fbil(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
	lookback_days: int = 14,
) -> FxQuote | None:
	if from_currency != "USD" or to_currency != "INR":
		return None
	return fetch_frankfurter_provider(
		from_currency,
		to_currency,
		for_date,
		"fbil",
		lookback_days=lookback_days,
		source="FBIL reference (Rule 34(2) services)",
	)


def fetch_ecb(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
	lookback_days: int = 14,
) -> FxQuote | None:
	return fetch_frankfurter_provider(
		from_currency,
		to_currency,
		for_date,
		"ecb",
		lookback_days=lookback_days,
		source="ECB reference (Frankfurter provider ecb)",
	)


def fetch_frankfurter_blended(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
	lookback_days: int = 14,
) -> FxQuote | None:
	target = parse_date(for_date)
	row = blended_rate_on_date(from_currency, to_currency, target)
	if not row:
		start = target - timedelta(days=lookback_days)
		series = blended_rates_series(from_currency, to_currency, start, target)
		row = latest_on_or_before(series, target)
	if not row:
		return None
	return _quote_from_row(
		row,
		from_currency,
		to_currency,
		target.isoformat(),
		"Frankfurter blended daily rate",
		"frankfurter.dev/v2/rates",
	)


def fetch_frankfurter_custom_key(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
	provider_key: str,
	lookback_days: int = 14,
) -> FxQuote | None:
	if not (provider_key or "").strip():
		return None
	return fetch_frankfurter_provider(
		from_currency,
		to_currency,
		for_date,
		provider_key.strip(),
		lookback_days=lookback_days,
	)


def fetch_currency_exchange(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
) -> FxQuote | None:
	import frappe

	target = parse_date(for_date)
	rows = frappe.get_all(
		"Currency Exchange",
		filters={
			"from_currency": from_currency,
			"to_currency": to_currency,
			"date": ("<=", target.isoformat()),
		},
		fields=["date", "exchange_rate"],
		order_by="date desc",
		limit=1,
	)
	if not rows:
		return None
	row = rows[0]
	return FxQuote(
		rate=round(float(row.exchange_rate), 4),
		from_currency=from_currency,
		to_currency=to_currency,
		posting_date=target.isoformat(),
		effective_date=str(row.date),
		source="Currency Exchange on site (cached/manual)",
		provider="erpnext/Currency Exchange",
	)


def fetch_erpnext_default(
	from_currency: str,
	to_currency: str,
	for_date: str | date,
) -> FxQuote | None:
	from erpnext.setup.utils import get_exchange_rate

	target = parse_date(for_date)
	try:
		rate = float(get_exchange_rate(from_currency, to_currency, target.isoformat()))
	except Exception:
		return None
	return FxQuote(
		rate=round(rate, 4),
		from_currency=from_currency,
		to_currency=to_currency,
		posting_date=target.isoformat(),
		effective_date=target.isoformat(),
		source="ERPNext get_exchange_rate",
		provider="erpnext.setup.utils",
	)
