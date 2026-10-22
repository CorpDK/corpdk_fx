"""Frankfurter API v2 client (https://api.frankfurter.dev/v2).

All rates use v2 only. api.frankfurter.app redirects here; do not call v1 paths.

Provider scoping (compliance / official reference rates):
  GET /v2/providers/{key}/rate/{base}/{quote}?date=
  GET /v2/providers/{key}/rates?base=&quotes=&from=&to=
  GET /v2/rate/{base}/{quote}?date=&providers={key}

Blended (default multi-provider feed):
  GET /v2/rate/{base}/{quote}?date=
  GET /v2/rates?base=&quotes=&date= or from=&to=
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from frappe.utils import get_request_session

from corpdk_fx.services.fx_quote import parse_date

API_ROOT = "https://api.frankfurter.dev/v2"
USER_AGENT = "CorpDK-ERP-FX/1.0 (corpdk_fx; Frankfurter v2)"


def fetch_json(url: str, timeout: int = 20) -> Any:
	"""GET JSON without Frappe integration error logging (404 is normal for lookback)."""
	session = get_request_session()
	response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
	if response.status_code in (404, 422):
		response.raise_for_status()
	response.raise_for_status()
	return response.json()


def _ccy(code: str) -> str:
	return (code or "").strip().lower()


def provider_rate_on_date(
	base: str,
	quote: str,
	for_date: str | date,
	provider_key: str,
) -> dict | None:
	"""Single observation from one provider on a calendar date."""
	target = parse_date(for_date)
	p = _ccy(provider_key)
	url = (
		f"{API_ROOT}/providers/{p}/rate/{_ccy(base)}/{_ccy(quote)}"
		f"?date={target.isoformat()}"
	)
	try:
		data = fetch_json(url)
	except requests.HTTPError as exc:
		if exc.response is not None and exc.response.status_code in (404, 422):
			return None
		return None
	except (requests.RequestException, ValueError):
		return None
	if not isinstance(data, dict) or data.get("rate") is None:
		return None
	return data


def provider_rates_series(
	base: str,
	quote: str,
	from_date: str | date,
	to_date: str | date,
	provider_key: str,
) -> list[dict]:
	p = _ccy(provider_key)
	params = urlencode(
		{
			"base": _ccy(base),
			"quotes": _ccy(quote),
			"from": parse_date(from_date).isoformat(),
			"to": parse_date(to_date).isoformat(),
		}
	)
	url = f"{API_ROOT}/providers/{p}/rates?{params}"
	try:
		data = fetch_json(url)
	except requests.RequestException:
		return []
	if not isinstance(data, list):
		return []
	return [
		row
		for row in data
		if row.get("quote", "").upper() == quote.upper() and row.get("rate") is not None
	]


def blended_rate_on_date(
	base: str,
	quote: str,
	for_date: str | date,
	provider_keys: list[str] | None = None,
) -> dict | None:
	target = parse_date(for_date)
	params: dict[str, str] = {"date": target.isoformat()}
	if provider_keys:
		params["providers"] = ",".join(_ccy(k) for k in provider_keys)
	url = f"{API_ROOT}/rate/{_ccy(base)}/{_ccy(quote)}?{urlencode(params)}"
	try:
		data = fetch_json(url)
	except requests.HTTPError as exc:
		if exc.response is not None and exc.response.status_code in (404, 422):
			return None
		return None
	except requests.RequestException:
		return None
	if not isinstance(data, dict) or data.get("rate") is None:
		return None
	return data


def latest_on_or_before(
	rows: list[dict],
	target: date,
) -> dict | None:
	eligible = [r for r in rows if parse_date(str(r["date"])) <= target]
	if not eligible:
		return None
	eligible.sort(key=lambda r: r["date"])
	return eligible[-1]


def blended_rates_series(
	base: str,
	quote: str,
	from_date: str | date,
	to_date: str | date,
) -> list[dict]:
	params = urlencode(
		{
			"base": _ccy(base),
			"quotes": _ccy(quote),
			"from": parse_date(from_date).isoformat(),
			"to": parse_date(to_date).isoformat(),
		}
	)
	url = f"{API_ROOT}/rates?{params}"
	try:
		data = fetch_json(url)
	except requests.RequestException:
		return []
	if not isinstance(data, list):
		return []
	return [row for row in data if row.get("rate") is not None]


def resolve_provider_rate(
	base: str,
	quote: str,
	for_date: str | date,
	provider_key: str,
	*,
	lookback_days: int = 14,
) -> dict | None:
	"""Latest provider rate on or before for_date (FBIL-style business rule)."""
	target = parse_date(for_date)
	direct = provider_rate_on_date(base, quote, target, provider_key)
	if direct and parse_date(str(direct["date"])) == target:
		return direct
	start = target - timedelta(days=lookback_days)
	series = provider_rates_series(base, quote, start, target, provider_key)
	row = latest_on_or_before(series, target)
	if row:
		return row
	return direct
