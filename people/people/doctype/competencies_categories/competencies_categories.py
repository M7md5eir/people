# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompetenciesCategories(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		competency_sets: DF.Link | None
		evaluation_category: DF.Autocomplete | None
		info: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Form Competencies"
