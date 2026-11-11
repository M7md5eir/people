# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EvaluationRates(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Color
		min_score: DF.Percent
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quota: DF.Percent
		rate: DF.Autocomplete
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Rates"
