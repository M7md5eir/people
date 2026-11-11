# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

import ast
import operator
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from people.performance.doctype.competencies.competencies import slice_factor

CHILD_DOCTYPE = "Goals KPIs items"


def get_goals_setup(cycle, emp_id, evaluation_category):
	"""Factor slices from the goals_categories row for one employee, cycle and category."""
	if not (cycle and emp_id and evaluation_category):
		return None
	form = frappe.db.get_value(
		"Evaluation Cycles Participants",
		{
			"parent": cycle,
			"parenttype": "Evaluation Cycles",
			"parentfield": "forms_assignment",
			"emp_id": emp_id,
		},
		"evaluation_form",
		order_by="idx asc",
	)
	if not form:
		return None
	rows = frappe.get_all(
		"Goals Categories",
		filters={
			"parent": form,
			"parenttype": "Evaluation Forms",
			"parentfield": "goals_categories",
			"evaluation_category": evaluation_category,
		},
		fields=["goals_sets"],
		order_by="idx asc",
	)
	goals_set = next((row.goals_sets for row in rows if row.goals_sets), None)
	if not goals_set:
		return None
	return {
		"slices": frappe.db.get_values(
			"Score Factor Scale",
			{
				"parent": goals_set,
				"parenttype": "Evaluation Categorise Sets",
				"parentfield": "items_calculation",
			},
			["score_factor", "min_score"],
			order_by="min_score asc, idx asc",
			as_dict=True,
		),
		"score_formula": frappe.db.get_value(
			"Evaluation Categorise Sets", goals_set, "score_formula"
		),
	}


def achievement_percent(row):
	"""KPI achievement as a percent, honouring reverse KPIs."""
	planned = flt(row.get("planned"))
	achieved = flt(row.get("achieved"))
	if row.get("reverse"):
		return flt(planned / achieved * 100, 2) if achieved else 100.0
	return flt(achieved / planned * 100, 2) if planned else 0.0


# ---------------------------------------------------------------------------
# Score Formula for KPIs
#
#   weight * score_factor
#   weight * (planned/achieved) * score_factor if reverse else weight * (achieved/planned) * score_factor
#   weight * score_factor * ((planned/achieved) if reverse else (achieved/planned))
#
# Fields are used by fieldname (case-insensitive). Values by fieldtype:
#   Percent -> fraction (100% -> 1)     Rating -> 0..1 as stored
#   Check   -> 0 / 1 (use: if reverse else ...)     other -> as is
# Allowed: + - * /  ( )  min max round abs  if/else  and/or/not  > < >= <= == !=
# The result is stored as a percent: 0.8 -> 80
# ---------------------------------------------------------------------------

BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
COMPARE_OPS = {
	ast.Eq: operator.eq, ast.NotEq: operator.ne,
	ast.Lt: operator.lt, ast.LtE: operator.le,
	ast.Gt: operator.gt, ast.GtE: operator.ge,
}
FUNCTIONS = {"min": min, "max": max, "round": round, "abs": abs}
KEYWORDS = {"if", "else", "and", "or", "not", "True", "False"}


def _field_value(df, value):
	value = flt(value)
	if df.fieldtype == "Percent":
		return value / 100
	if df.fieldtype == "Check":
		return 1 if value else 0
	return value  # Rating is already 0..1, numbers as they are


def evaluate_kpi_formula(formula, row, overrides=None):
	"""overrides: {fieldname: value} already in formula scale (fractions), used instead of the row value."""
	if not (formula or "").strip():
		return None
	overrides = overrides or {}

	expr = (
		str(formula).strip()
		.replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
	)
	if re.search(r"[^A-Za-z0-9_+\-*/().,<>=!\s]", expr):
		frappe.throw(_("Score Formula has an invalid character: {0}").format(formula))

	meta = frappe.get_meta(CHILD_DOCTYPE)
	values = {}
	for name in set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)):
		if name in FUNCTIONS or name in KEYWORDS:
			continue
		fieldname = name.lower()
		if fieldname in overrides:
			values[name] = flt(overrides[fieldname])
			continue
		df = meta.get_field(fieldname)
		if not df:
			frappe.throw(
				_("Score Formula uses <b>{0}</b>, which is not a field of {1}").format(name, CHILD_DOCTYPE)
			)
		values[name] = _field_value(df, row.get(fieldname))

	try:
		result = _eval(ast.parse(expr, mode="eval").body, values)
	except ZeroDivisionError:
		frappe.throw(_("Score Formula divides by zero for KPI {0}").format(row.get("kpi") or row.idx))
	except (SyntaxError, ValueError, TypeError):
		frappe.throw(_("Score Formula is not a valid equation: {0}").format(formula))
	return flt(flt(result) * 100, 2)


def _eval(node, v):
	if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool)):
		return node.value
	if isinstance(node, ast.Name):
		if node.id in v:
			return v[node.id]
		raise ValueError(node.id)
	if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
		left, right = _eval(node.left, v), _eval(node.right, v)
		if isinstance(node.op, ast.Div) and not right:
			raise ZeroDivisionError
		return BIN_OPS[type(node.op)](left, right)
	if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
		return UNARY_OPS[type(node.op)](_eval(node.operand, v))
	if isinstance(node, ast.IfExp):  # only the chosen side is evaluated
		return _eval(node.body, v) if _eval(node.test, v) else _eval(node.orelse, v)
	if isinstance(node, ast.Compare):
		left = _eval(node.left, v)
		for op, comp in zip(node.ops, node.comparators):
			if type(op) not in COMPARE_OPS:
				raise ValueError("operator")
			right = _eval(comp, v)
			if not COMPARE_OPS[type(op)](left, right):
				return False
			left = right
		return True
	if isinstance(node, ast.BoolOp):
		if isinstance(node.op, ast.And):
			return all(_eval(x, v) for x in node.values)
		return any(_eval(x, v) for x in node.values)
	if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and not node.keywords:
		return FUNCTIONS[node.func.id](*[_eval(a, v) for a in node.args])
	raise ValueError("unsupported expression")


class Goals(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.performance.doctype.goals_kpis_items.goals_kpis_items import GoalsKPIsitems

		amended_from: DF.Link | None
		cycle: DF.Link | None
		due_date: DF.Date | None
		emp_id: DF.Link | None
		emp_name: DF.Data | None
		emp_organization: DF.Link | None
		employee_job: DF.Link | None
		evaluation_category: DF.Autocomplete | None
		goal: DF.Data | None
		goals_kpis_records: DF.Table[GoalsKPIsitems]
		image: DF.AttachImage | None
		score: DF.Percent
		start_date: DF.Date | None
		status: DF.Literal["Pending", "Withdrawn", "Approved", "Rejected", "Submitted"]
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Goals"

	def validate(self):
		setup = get_goals_setup(self.cycle, self.emp_id, self.evaluation_category)
		slices = (setup or {}).get("slices")
		formula = (setup or {}).get("score_formula")
		for row in self.get("goals_kpis_records") or []:
			achievement = achievement_percent(row)
			row.score_factor = slice_factor(slices, achievement) if slices else 0
			overrides = {
				"rating": achievement / 100,
				"score_factor": flt(row.score_factor) / 100,
			}
			row.score = evaluate_kpi_formula(formula, row, overrides=overrides) if formula else 0