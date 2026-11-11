# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe.utils import flt


def get_evaluation_form(evaluation_cycle, emp_id):
	"""Evaluation Form linked to one employee in one cycle, via evaluations_mapping."""
	if not (evaluation_cycle and emp_id):
		return None
	forms = frappe.db.get_values(
		"Evaluations Mapping",
		{"parent": evaluation_cycle, "emp_id": emp_id},
		"evaluation_form",
		order_by="idx asc",
	)
	for form in forms:
		name = form[0] if isinstance(form, (list, tuple)) else form
		if name:
			return name
	return None


def get_category_slices(evaluation_cycle, category, emp_id, table_field="competencies_calc_individual"):
	"""Score/factor slices behind one employee+category, following:
	cycle -> evaluations_mapping (emp) -> evaluation_form
	-> competencies_distribution (category) -> given calc table rows."""
	form = get_evaluation_form(evaluation_cycle, emp_id)
	if not (form and category):
		return None
	dist = frappe.db.get_value(
		"Competencies Distribution",
		{"parent": form, "category": category},
		"name",
		order_by="idx asc",
	)
	if not dist:
		return None
	return frappe.db.get_values(
		"Evaluations Calculations",
		{"parent": dist, "parentfield": table_field},
		["score", "factor"],
		order_by="score asc",
		as_dict=True,
	) or None


def slice_factor(slices, achievement):
	"""Bracket factor for an achievement: factor of the first slice at or above it."""
	if not slices:
		return 100.0
	if len(slices) == 1:
		return flt(slices[0]["factor"])
	value = flt(achievement) or 0
	for s in slices:
		if value <= (flt(s["score"]) or 0):
			return flt(s["factor"]) or 0
	return flt(slices[-1]["factor"]) or 0


CALCULATION_METHODS = (
	"Weight × Score",
	"Weight × Factor",
	"Weight × Factor × Score",
)


def get_calculation_method(evaluation_cycle, emp_id, category):
	"""Calculation Method on the competencies distribution row behind one employee+category."""
	form = get_evaluation_form(evaluation_cycle, emp_id)
	if not (form and category):
		return None
	return frappe.db.get_value(
		"Competencies Distribution",
		{"parent": form, "category": category},
		"calculation_method",
		order_by="idx asc",
	)


def entry_score_for_method(method, weight, factor, rating):
	"""Entry row score for a calculation method (rating is 0-1); None when unknown."""
	if method == "Weight × Score":
		return flt(flt(weight) * flt(rating), 2)
	if method == "Weight × Factor":
		return flt(flt(weight) * flt(factor) / 100, 2)
	if method == "Weight × Factor × Score":
		return flt(flt(weight) * flt(factor) * flt(rating) / 100, 2)
	return None


def get_factor_for_score(evaluation_cycle, category, emp_id, score):
	"""Factor for one score under one employee+category; None when unresolvable."""
	slices = get_category_slices(evaluation_cycle, category, emp_id)
	if slices is None:
		return None
	return flt(slice_factor(slices, score), 2)


def get_factor_for_rating(evaluation_cycle, category, emp_id, rating):
	"""Factor for one 0-1 rating under one employee+category; None when unresolvable."""
	slices = get_category_slices(evaluation_cycle, category, emp_id)
	if slices is None:
		return None
	return flt(slice_factor(slices, (flt(rating) or 0) * 100), 2)


def get_factor_for_total(evaluation_cycle, category, emp_id, total):
	"""Factor for an aggregate score using the competencies_calc slices; None when unresolvable."""
	slices = get_category_slices(
		evaluation_cycle, category, emp_id, table_field="competencies_calc"
	)
	if slices is None:
		return None
	return flt(slice_factor(slices, total), 2)


class CompetenciesEvaluationEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		competency: DF.Link | None
		factor: DF.Percent
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rating: DF.Rating
		score: DF.Percent
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Competencies Evaluation Entry"
