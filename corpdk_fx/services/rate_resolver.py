from __future__ import annotations

from typing import TYPE_CHECKING, Any

import frappe
from frappe.utils import now_datetime, today

from corpdk_fx.services import providers
from corpdk_fx.services.fx_quote import FxQuote

if TYPE_CHECKING:
	from corpdk_fx.corpdk_fx.doctype.corpdk_fx_pair.corpdk_fx_pair import CorpDKFXPair

PROVIDER_HANDLERS = {
	"FBIL Frankfurter": providers.fetch_fbil,
	"ECB Frankfurter": providers.fetch_ecb,
	"Frankfurter Blended": providers.fetch_frankfurter_blended,
	"Frankfurter (provider key)": providers.fetch_frankfurter_custom_key,
	"Currency Exchange": providers.fetch_currency_exchange,
	"ERPNext Default": providers.fetch_erpnext_default,
}


def list_enabled_pairs() -> list["CorpDKFXPair"]:
	return frappe.get_all(
		"CorpDK FX Pair",
		filters={"enabled": 1},
		fields=["name"],
		pluck="name",
	)


def get_pair_doc(name: str) -> "CorpDKFXPair":
	return frappe.get_doc("CorpDK FX Pair", name)


def resolve_for_pair(
	pair: "CorpDKFXPair | str",
	posting_date: str | None = None,
	*,
	use_cache: bool = False,
) -> FxQuote:
	if isinstance(pair, str):
		pair = get_pair_doc(pair)

	if use_cache and pair.cached_rate and pair.cached_effective_date:
		return FxQuote(
			rate=float(pair.cached_rate),
			from_currency=pair.from_currency,
			to_currency=pair.to_currency,
			posting_date=posting_date or today(),
			effective_date=str(pair.cached_effective_date),
			source=pair.policy_label or pair.provider,
			provider=pair.provider,
			pair_name=pair.name,
		)

	handler = PROVIDER_HANDLERS.get(pair.provider)
	if not handler:
		frappe.throw(f"Unknown FX provider {pair.provider!r} on pair {pair.name}")

	target_date = posting_date or today()
	lookback = int(pair.lookback_days or 14)
	if pair.provider == "Frankfurter (provider key)":
		quote = handler(
			pair.from_currency,
			pair.to_currency,
			target_date,
			pair.frankfurter_provider_key or "",
			lookback,
		)
	elif pair.provider in ("FBIL Frankfurter", "ECB Frankfurter", "Frankfurter Blended"):
		quote = handler(pair.from_currency, pair.to_currency, target_date, lookback)
	else:
		quote = handler(pair.from_currency, pair.to_currency, target_date)

	if not quote:
		frappe.throw(
			f"No {pair.from_currency}/{pair.to_currency} rate for {target_date} "
			f"via {pair.provider} (pair {pair.name})"
		)

	quote = FxQuote(
		rate=quote.rate,
		from_currency=quote.from_currency,
		to_currency=quote.to_currency,
		posting_date=target_date,
		effective_date=quote.effective_date,
		source=pair.policy_label or quote.source,
		provider=quote.provider,
		pair_name=pair.name,
	)
	return quote


def refresh_pair_cache(pair: "CorpDKFXPair | str", posting_date: str | None = None) -> FxQuote:
	quote = resolve_for_pair(pair, posting_date=posting_date or today(), use_cache=False)
	if isinstance(pair, str):
		pair = get_pair_doc(pair)

	pair.db_set(
		{
			"cached_rate": quote.rate,
			"cached_effective_date": quote.effective_date,
			"cached_at": now_datetime(),
			"cached_provider_note": f"{quote.provider} · {quote.source}",
		}
	)
	return quote


def ensure_currency_exchange(quote: FxQuote) -> None:
	name = frappe.db.get_value(
		"Currency Exchange",
		{
			"from_currency": quote.from_currency,
			"to_currency": quote.to_currency,
			"date": quote.effective_date,
		},
		"name",
	)
	if name:
		frappe.db.set_value("Currency Exchange", name, "exchange_rate", quote.rate)
		return
	ce = frappe.new_doc("Currency Exchange")
	ce.from_currency = quote.from_currency
	ce.to_currency = quote.to_currency
	ce.date = quote.effective_date
	ce.exchange_rate = quote.rate
	ce.insert(ignore_permissions=True)


def find_pair_for_sales_invoice(doc) -> "CorpDKFXPair | None":
	if doc.doctype != "Sales Invoice":
		return None

	candidates: list[dict[str, Any]] = frappe.get_all(
		"CorpDK FX Pair",
		filters={
			"enabled": 1,
			"apply_on_sales_invoice_submit": 1,
			"from_currency": doc.currency,
		},
		fields=[
			"name",
			"company",
			"require_export_naming",
			"naming_series_contains",
		],
	)

	def specificity(row: dict[str, Any]) -> int:
		score = 0
		if row.company:
			score += 4 if row.company == doc.company else -1
		else:
			score += 1
		return score

	candidates.sort(key=specificity, reverse=True)

	for row in candidates:
		if row.company and row.company != doc.company:
			continue
		if row.require_export_naming:
			series = doc.naming_series or ""
			name = doc.name or ""
			needle = (row.naming_series_contains or "CDK-EXP").strip()
			if needle not in series and not str(name).startswith("CDK-EXP-"):
				continue
		return get_pair_doc(row.name)
	return None


def apply_pair_to_sales_invoice(doc, pair: "CorpDKFXPair | str", *, persist_remarks: bool = True) -> FxQuote:
	if isinstance(pair, str):
		pair = get_pair_doc(pair)

	quote = resolve_for_pair(pair, posting_date=doc.posting_date, use_cache=False)
	ensure_currency_exchange(quote)
	doc.conversion_rate = quote.rate

	meta = frappe.get_meta("Sales Invoice")
	if meta.has_field("export_usd_inr_rate_source"):
		doc.export_usd_inr_rate_source = quote.provider
	if meta.has_field("export_usd_inr_effective_date"):
		doc.export_usd_inr_effective_date = quote.effective_date
	if meta.has_field("export_usd_inr_policy"):
		doc.export_usd_inr_policy = quote.source

	if persist_remarks:
		line = quote.audit_line()
		remarks = doc.remarks or ""
		if "[CorpDK FX]" in remarks:
			parts = [p for p in remarks.split("\n") if not p.strip().startswith("[CorpDK FX]")]
			remarks = "\n".join(parts).strip()
		doc.remarks = (remarks + "\n" + line).strip() if remarks else line

	return quote
