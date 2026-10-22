# Copyright (c) 2026, CorpDK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CorpDKFXPair(Document):
	def validate(self):
		if self.from_currency == self.to_currency:
			frappe.throw("From and To currency must differ")

		if self.provider == "FBIL Frankfurter" and (
			self.from_currency != "USD" or self.to_currency != "INR"
		):
			frappe.throw("FBIL Frankfurter supports USD → INR only")

		if self.provider == "Frankfurter (provider key)" and not (
			self.frankfurter_provider_key or ""
		).strip():
			frappe.throw("Set Frankfurter Provider Key (see https://api.frankfurter.dev/v2/providers)")

		if self.provider == "FBIL Frankfurter" and not self.frankfurter_provider_key:
			self.frankfurter_provider_key = "fbil"
		if self.provider == "ECB Frankfurter" and not self.frankfurter_provider_key:
			self.frankfurter_provider_key = "ecb"

	def before_save(self):
		if not self.policy_label:
			self.policy_label = f"{self.from_currency}/{self.to_currency} via {self.provider}"
