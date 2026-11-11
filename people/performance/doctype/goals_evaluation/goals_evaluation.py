# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GoalsEvaluation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.performance.doctype.goals_evaluation_items.goals_evaluation_items import GoalsEvaluationitems

		amended_from: DF.Link | None
		emp_id: DF.Link | None
		evaluation_cycle: DF.Link | None
		goals_evaluation_records: DF.Table[GoalsEvaluationitems]
	# end: auto-generated types

	_DOCTYPE_NAME = "Goals Evaluation"

	def before_save(self):
		if not (self.evaluation_cycle and self.emp_id):
			return
		existing = {}
		for row in self.goals_evaluation_records or []:
			if row.get("goal") and row.goal not in existing:
				existing[row.goal] = row
		for s in frappe.get_all(
			"Goals",
			filters={"cycle": self.evaluation_cycle, "emp_id": self.emp_id},
			fields=["name", "weight"],
			order_by="creation asc",
		):
			row = existing.get(s.name)
			if row:
				row.weight = s.weight
				continue
			self.append(
				"goals_evaluation_records",
				{"goal": s.name, "weight": s.weight},
			)
