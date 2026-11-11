# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EvaluationsMapping(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.evaluators_mapping.evaluators_mapping import EvaluatorsMapping

		emp_id: DF.Link | None
		evaluation_form: DF.Link | None
		evaluators_mapping: DF.Table[EvaluatorsMapping]
		job: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		position: DF.Link | None
		preferred_name: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluations Mapping"
