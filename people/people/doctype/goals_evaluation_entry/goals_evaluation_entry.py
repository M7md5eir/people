# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from people.people.doctype.competencies_evaluation_entry.competencies_evaluation_entry import (
	get_evaluation_form,
	slice_factor,
)


def get_goals_slices(evaluation_cycle, category, emp_id, table_field="goals_calc_individual"):
	"""Score/factor slices behind one employee+category, following:
	cycle -> evaluations_mapping (emp) -> evaluation_form
	-> goals_distribution (category) -> given calc table rows."""
	form = get_evaluation_form(evaluation_cycle, emp_id)
	if not (form and category):
		return None
	dist = frappe.db.get_value(
		"Goals Distribution",
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


CALCULATION_METHODS = (
	"Weight × Score",
	"Weight × Factor",
	"Weight × Factor × Score",
)


def entry_score_for_method(method, weight, factor, kpis_score):
	"""Entry row score for a calculation method; None when unknown."""
	if method == "Weight × Score":
		return flt(flt(weight) * flt(kpis_score) / 100, 2)
	if method == "Weight × Factor":
		return flt(flt(weight) * flt(factor) / 100, 2)
	if method == "Weight × Factor × Score":
		return flt(flt(weight) * flt(factor) * flt(kpis_score) / 10000, 2)
	return None


def get_calculation_method(evaluation_cycle, emp_id, category):
	"""Calculation Method on the goals distribution row behind one employee+category."""
	form = get_evaluation_form(evaluation_cycle, emp_id)
	if not (form and category):
		return None
	return frappe.db.get_value(
		"Goals Distribution",
		{"parent": form, "category": category},
		"calculation_method",
		order_by="idx asc",
	)


def get_factor_for_kpis(evaluation_cycle, category, emp_id, kpis_score):
	"""Factor for one kpis_score under one employee+category; None when unresolvable."""
	slices = get_goals_slices(evaluation_cycle, category, emp_id)
	if slices is None:
		return None
	return flt(slice_factor(slices, kpis_score), 2)


def get_factor_for_total(evaluation_cycle, category, emp_id, total):
	"""Factor for an aggregate score using the goals_calc slices; None when unresolvable."""
	slices = get_goals_slices(evaluation_cycle, category, emp_id, table_field="goals_calc")
	if slices is None:
		return None
	return flt(slice_factor(slices, total), 2)


class GoalsEvaluationEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.kpis_evaluation_entry.kpis_evaluation_entry import KPIsEvaluationEntry

		factor: DF.Percent
		goal: DF.Link | None
		kpis_evaluation_entry: DF.Table[KPIsEvaluationEntry]
		kpis_num: DF.Int
		kpis_score: DF.Percent
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		score: DF.Percent
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Goals Evaluation Entry"
