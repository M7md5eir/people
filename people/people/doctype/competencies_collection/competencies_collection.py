# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompetenciesCollection(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Autocomplete | None
		category_score: DF.Percent
		factor: DF.Percent
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		score: DF.Percent
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Competencies Collection"
