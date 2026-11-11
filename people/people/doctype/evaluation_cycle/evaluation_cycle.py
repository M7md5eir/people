# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EvaluationCycle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.evaluations_mapping.evaluations_mapping import EvaluationsMapping

		evaluation_cycle: DF.Data | None
		evaluations_mapping: DF.Table[EvaluationsMapping]
		status: DF.Autocomplete | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Cycle"
