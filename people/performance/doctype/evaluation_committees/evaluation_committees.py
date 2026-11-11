# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EvaluationCommittees(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.performance.doctype.evaluation_committees_items.evaluation_committees_items import EvaluationCommitteesitems

		emp_id: DF.Link | None
		evaluation_committees_records: DF.Table[EvaluationCommitteesitems]
		evaluation_cycle: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Committees Members"
