# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class Evaluation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.competencies_collection.competencies_collection import CompetenciesCollection

		amended_from: DF.Link | None
		competencies_collection: DF.Table[CompetenciesCollection]
		emp_id: DF.Link | None
		emp_preferred_name: DF.Data | None
		evaluation_cycle: DF.Link | None
		job: DF.Link | None
		position: DF.Link | None
		score: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation"

	def validate(self):
		if (
			self.evaluation_cycle
			and self.emp_id
			and not self.get("competencies_collection")
		):
			form = frappe.db.get_value(
				"Evaluations Mapping",
				{"parent": self.evaluation_cycle, "emp_id": self.emp_id},
				"evaluation_form",
				order_by="idx asc",
			)
			if form:
				seen = []
				weights = {}
				for rec in frappe.db.get_values(
					"Competencies Distribution",
					{"parent": form},
					["category", "weight"],
					order_by="idx asc",
					as_dict=True,
				):
					if rec.category and rec.category not in seen:
						seen.append(rec.category)
						weights[rec.category] = rec.weight
				for category in seen:
					self.append(
						"competencies_collection",
						{"category": category, "weight": weights.get(category)},
					)
