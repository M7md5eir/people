# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class CompetenciesEvaluation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.competencies_evaluation_entry.competencies_evaluation_entry import CompetenciesEvaluationEntry

		amended_from: DF.Link | None
		category: DF.Autocomplete | None
		competencies_evaluation_entry: DF.Table[CompetenciesEvaluationEntry]
		emp_id: DF.Link | None
		emp_position: DF.Link | None
		emp_preferred_name: DF.Data | None
		evaluation_cycle: DF.Link | None
		evl_id: DF.Link | None
		evl_job: DF.Link | None
		evl_name: DF.Data | None
		evl_position: DF.Link | None
		factor: DF.Percent
		job: DF.Link | None
		score: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Competencies Evaluation"

	@staticmethod
	def is_empty(value):
		return value is None or (isinstance(value, str) and not value.strip())

	def validate(self):
		from frappe.utils import flt
		from people.people.doctype.competencies_evaluation_entry.competencies_evaluation_entry import (
			CALCULATION_METHODS,
			entry_score_for_method,
			get_calculation_method,
			get_factor_for_rating,
			get_factor_for_total,
		)

		method = get_calculation_method(self.evaluation_cycle, self.emp_id, self.category)
		if method not in CALCULATION_METHODS:
			frappe.throw(
				"Calculation Method {0} is not supported for {1}".format(
					frappe.bold(method or frappe._("Empty")),
					frappe.bold(self.category or ""),
				)
			)

		rows = self.competencies_evaluation_entry or []
		kept = [
			d
			for d in rows
			if not self.is_empty(d.get("competency"))
			and (d.get("weight") is None or flt(d.get("weight")) != 0)
		]
		if len(kept) != len(rows):
			self.set("competencies_evaluation_entry", kept)

		for row in self.competencies_evaluation_entry or []:
			factor = get_factor_for_rating(
				self.evaluation_cycle, self.category, self.emp_id, row.rating
			)
			if factor is not None:
				row.factor = factor
			row.score = entry_score_for_method(method, row.weight, row.factor, row.rating)

		total = flt(sum(flt(row.score) for row in self.competencies_evaluation_entry or []), 2)
		parent_factor = get_factor_for_total(
			self.evaluation_cycle, self.category, self.emp_id, total
		)
		if parent_factor is not None:
			self.factor = parent_factor
		self.score = flt(total * flt(self.factor) / 100, 2)
