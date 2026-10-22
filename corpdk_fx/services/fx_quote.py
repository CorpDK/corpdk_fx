from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FxQuote:
	rate: float
	from_currency: str
	to_currency: str
	posting_date: str
	effective_date: str
	source: str
	provider: str
	pair_name: str = ""

	def audit_line(self) -> str:
		return (
			f"[CorpDK FX] {self.rate} {self.from_currency}/{self.to_currency} · "
			f"effective {self.effective_date} · {self.source} · posting {self.posting_date}"
		)


def parse_date(value: str | date) -> date:
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value)[:10])
