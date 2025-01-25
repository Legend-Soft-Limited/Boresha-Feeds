# Copyright (c) 2025, kuriakevin06@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import nowdate

class FuelingList(Document):
	def autoname(self):
		year = nowdate().split('-')[0]
		prefix = f"FL-{year}"
		series_number = getseries(prefix, 5)
		self.name = f"{prefix}-{series_number}"