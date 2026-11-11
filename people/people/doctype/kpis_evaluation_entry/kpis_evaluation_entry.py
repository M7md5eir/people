# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class KPIsEvaluationEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		achived: DF.Percent
		kpi: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		planned: DF.Percent
		reverse_calc: DF.Check
		score: DF.Percent
		uom: DF.Link | None
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "KPIs Entery"
