# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

import ast
import operator
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

CHILD_DOCTYPE = "Competencies Records"


def stars_of(df):
	"""Number of stars of a Rating field (Frappe default is 5)."""
	return int(flt(df.options)) if df and flt(df.options) else 5


def to_percent(df, value):
	"""Bring a field value to a 0-100 scale using its fieldtype.

	Rating  : stored 0..1 (4 of 5 stars = 0.8)  -> 80
	Percent : stored 0..100                     -> as is
	Other   : as is
	"""
	value = flt(value)
	if df and df.fieldtype == "Rating":
		return value * 100
	return value


def from_percent(df, pct):
	"""Store a 0-100 value back in the field's own scale.

	Rating  : 0..1, and a Rating cannot go above full stars,
	          so anything above 100% is stored as 1 (5 of 5 stars)
	Percent : as is (can go above 100%)
	"""
	pct = flt(pct)
	if df and df.fieldtype == "Rating":
		return flt(min(pct, 100) / 100, 4)
	return flt(pct, 2)


def required_value(row):
	"""Required level exactly as entered."""
	return flt(row.get("required"))


def compute_achieved(row, meta):
	"""achieved = rating / required, as a percent.

	rating is read through its fieldtype (Rating -> fraction).
	required is used exactly as entered; zero gives zero achievement.
	"""
	rating_df = meta.get_field("rating")
	rating_fraction = to_percent(rating_df, row.get("rating")) / 100
	required = required_value(row)
	return flt(rating_fraction / required * 100, 2) if required else 0.0


def to_level(df, value, stars):
	"""Bring rating / required to a level number (1..stars) using the fieldtype.

	Rating  : 0..1      -> x stars   (0.8 with 5 stars -> 4)
	Percent : 0..100    -> / 100 x stars
	Int / Float         -> already a level
	"""
	value = flt(value)
	if df and df.fieldtype == "Rating":
		return value * stars
	if df and df.fieldtype == "Percent":
		return value / 100 * stars
	return value


def compute_gap(row, meta):
	"""gap = rating - required, in levels (stars).

	 0 -> exactly the required level
	+1 -> one level above required
	-2 -> two levels below required
	None when there is no required level for this row.
	"""
	rating_df = meta.get_field("rating")
	required_df = meta.get_field("required")
	if not required_df or not flt(row.get("required")):
		return None
	stars = stars_of(rating_df)
	return flt(to_level(rating_df, row.get("rating"), stars) - to_level(required_df, row.get("required"), stars), 2)


def store_gap(df, gap, stars):
	"""Store the gap in the gap field's own scale.

	Int / Float : levels as they are (-2, 0, +1)
	Percent     : levels as percentage points of the scale (-1 level of 5 -> -20)
	"""
	if df.fieldtype == "Int":
		return int(round(gap))
	if df.fieldtype == "Percent":
		return flt(gap / stars * 100, 2)
	return flt(gap, 2)


def slice_factor(slices, rating):
	"""Factor of the highest min_score bracket at or below the rating.

	Zero when the value is below every bracket.
	"""
	if not slices:
		return None
	value = flt(rating)
	best = None
	for s in slices:
		if value >= flt(s["min_score"]):
			best = s["score_factor"]
	return flt(best) if best is not None else 0.0


def get_rating_slices(evaluation_cycle, emp_id, evaluation_category):
	"""Calculation slices behind one cycle + employee + category, following:
	cycle -> forms_assignment (emp) -> evaluation_form
	-> competencies_categories (category) -> competency_sets
	-> items_calculation rows."""
	setup = get_competency_setup(evaluation_cycle, emp_id, evaluation_category)
	if not setup:
		return None
	return setup["slices"]


def get_competency_setup(evaluation_cycle, emp_id, evaluation_category):
	"""Slices + score formula behind one cycle + employee + category."""
	if not (evaluation_cycle and emp_id and evaluation_category):
		return None
	form = frappe.db.get_value(
		"Evaluation Cycles Participants",
		{
			"parent": evaluation_cycle,
			"parenttype": "Evaluation Cycles",
			"parentfield": "forms_assignment",
			"emp_id": emp_id,
		},
		"evaluation_form",
		order_by="idx asc",
	)
	if not form:
		return None
	competency_set = frappe.db.get_value(
		"Competencies Categories",
		{
			"parent": form,
			"parenttype": "Evaluation Forms",
			"parentfield": "competencies_categories",
			"evaluation_category": evaluation_category,
		},
		"competency_sets",
		order_by="idx asc",
	)
	if not competency_set:
		return None
	slices = frappe.db.get_values(
		"Score Factor Scale",
		{
			"parent": competency_set,
			"parenttype": "Evaluation Categorise Sets",
			"parentfield": "items_calculation",
		},
		["score_factor", "min_score"],
		order_by="min_score asc, idx asc",
		as_dict=True,
	)
	total_slices = frappe.db.get_values(
		"Score Factor Scale",
		{
			"parent": competency_set,
			"parenttype": "Evaluation Categorise Sets",
			"parentfield": "categorise_calculation",
		},
		["score_factor", "min_score"],
		order_by="min_score asc, idx asc",
		as_dict=True,
	)
	return {
		"slices": slices,
		"total_slices": total_slices,
		"score_formula": frappe.db.get_value(
			"Evaluation Categorise Sets", competency_set, "score_formula"
		),
	}


BIN_OPS = {
	ast.Add: operator.add,
	ast.Sub: operator.sub,
	ast.Mult: operator.mul,
	ast.Div: operator.truediv,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
COMPARE_OPS = {
	ast.Eq: operator.eq,
	ast.NotEq: operator.ne,
	ast.Lt: operator.lt,
	ast.LtE: operator.le,
	ast.Gt: operator.gt,
	ast.GtE: operator.ge,
}

FUNCTIONS = {"min": min, "max": max, "round": round, "abs": abs}

# words of the formula language, not field names
KEYWORDS = {"if", "else", "and", "or", "not", "True", "False"}

# old names still accepted
ALIASES = {"score": "rating", "factor": "score_factor"}


def evaluate_equation(formula, row, doctype=None, overrides=None):
	"""Evaluate Score Formula over the row's fields, by fieldname.

	- Any field of the child doctype can be used by its fieldname (case-insensitive).
	- Rating fields are first turned into a percent (x100): 4 of 5 stars -> 80%
	- Every percent (Rating, Percent: weight, achieved, score_factor ...) is then
	  used as a fraction, so they mix correctly: 80% -> 0.8, 20% -> 0.2
	- Check fields are 0 or 1:  ... if reverse else ...
	- Other numbers (Int / Float) are used as they are.
	- Functions: min, max, round, abs.  Signs: + - * / ( ) and also × ÷
	- Conditions: a if condition else b, and / or / not, > < >= <= == !=
	  (only the chosen side of if/else is calculated)
	- The result is stored as a percent: 0.16 -> 16
	- `doctype` defaults to Competencies Records; `overrides` supplies values
	  (already in fraction scale) for fields or aliases resolved before the row.
	Raises a clear error instead of silently skipping the score.
	"""
	if not (formula or "").strip():
		return None

	expr = (
		str(formula).strip()
		.replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
		.replace("≥", ">=").replace("≤", "<=").replace("≠", "!=")
	)
	if re.search(r"[^A-Za-z0-9_+\-*/().,<>=!\s]", expr):
		frappe.throw(_("Score Formula has an invalid character: {0}").format(formula))

	meta = frappe.get_meta(doctype or CHILD_DOCTYPE)
	overrides = {key.lower(): value for key, value in (overrides or {}).items()}
	values = {}
	for name in set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)):
		if name in FUNCTIONS or name in KEYWORDS:
			continue
		fieldname = ALIASES.get(name.lower(), name.lower())
		if fieldname in overrides:
			values[name] = overrides[fieldname]
			continue
		df = meta.get_field(fieldname)
		if not df:
			frappe.throw(
				_("Score Formula uses <b>{0}</b>, which is not a field of {1}").format(
					name, doctype or CHILD_DOCTYPE
				)
			)
		value = flt(row.get(fieldname))
		if df.fieldtype in ("Percent", "Rating"):
			# Rating x100 -> percent, then every percent is used as a fraction: 80% -> 0.8
			value = to_percent(df, value) / 100
		elif df.fieldtype == "Check":
			value = 1 if value else 0
		values[name] = value

	try:
		result = _eval_node(ast.parse(expr, mode="eval").body, values)
	except ZeroDivisionError:
		frappe.throw(
			_("Score Formula divides by zero for {0}").format(
				row.get("competency") or row.get("kpi") or _("a row")
			)
		)
	except (SyntaxError, ValueError, TypeError):
		frappe.throw(_("Score Formula is not a valid equation: {0}").format(formula))
	return flt(flt(result) * 100, 2)


def _eval_node(node, values):
	if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool)):
		return node.value
	if isinstance(node, ast.Name):
		if node.id in values:
			return values[node.id]
		if node.id in ("True", "False"):
			return node.id == "True"
		raise ValueError(node.id)
	if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
		left = _eval_node(node.left, values)
		right = _eval_node(node.right, values)
		if isinstance(node.op, ast.Div) and not right:
			raise ZeroDivisionError
		return BIN_OPS[type(node.op)](left, right)
	if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
		return UNARY_OPS[type(node.op)](_eval_node(node.operand, values))
	# a if condition else b -> only the chosen side is calculated
	if isinstance(node, ast.IfExp):
		chosen = node.body if _eval_node(node.test, values) else node.orelse
		return _eval_node(chosen, values)
	if isinstance(node, ast.Compare):
		left = _eval_node(node.left, values)
		for op, comparator in zip(node.ops, node.comparators):
			if type(op) not in COMPARE_OPS:
				raise ValueError("unsupported comparison")
			right = _eval_node(comparator, values)
			if not COMPARE_OPS[type(op)](left, right):
				return False
			left = right
		return True
	if isinstance(node, ast.BoolOp):
		if isinstance(node.op, ast.And):
			return all(_eval_node(v, values) for v in node.values)
		return any(_eval_node(v, values) for v in node.values)
	if (
		isinstance(node, ast.Call)
		and isinstance(node.func, ast.Name)
		and node.func.id in FUNCTIONS
		and not node.keywords
	):
		return FUNCTIONS[node.func.id](*[_eval_node(a, values) for a in node.args])
	raise ValueError("unsupported expression")


class Competencies(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.performance.doctype.competencies_records.competencies_records import CompetenciesRecords

		amended_from: DF.Link | None
		competencies_records: DF.Table[CompetenciesRecords]
		emp_id: DF.Link | None
		emp_name: DF.Data | None
		employee_job: DF.Link | None
		evaluation_category: DF.Autocomplete | None
		evaluation_cycle: DF.Link | None
		evaluator_id: DF.Link | None
		evaluator_job: DF.Link | None
		evaluator_name: DF.Data | None
		evaluator_organization: DF.Link | None
		score_factor: DF.Percent
		image: DF.AttachImage | None
		organization: DF.Link | None
		score: DF.Percent
		status: DF.Autocomplete | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Competencies"

	def validate(self):
		setup = get_competency_setup(
			self.evaluation_cycle, self.emp_id, self.evaluation_category
		)
		if not setup:
			return
		slices = setup["slices"]
		formula = setup["score_formula"]
		meta = frappe.get_meta(CHILD_DOCTYPE)
		rating_df = meta.get_field("rating")
		for row in self.get("competencies_records") or []:
			achieved_df = meta.get_field("achieved")
			if achieved_df:
				row.achieved = from_percent(achieved_df, compute_achieved(row, meta))
			gap_df = meta.get_field("gap")
			if gap_df:
				gap = compute_gap(row, meta)
				row.gap = None if gap is None else store_gap(gap_df, gap, stars_of(rating_df))
			required = required_value(row)
			if not required:
				row.score_factor = 0
				row.score = 0
				continue
			# min_score is a percent, so compare rating / required as a percent
			factor = slice_factor(slices, compute_achieved(row, meta))
			if factor is not None:
				row.score_factor = factor
			score = evaluate_equation(formula, row, overrides={"required": required})
			if score is not None:
				row.score = score

		total = flt(sum(flt(row.get("score") or 0) for row in self.get("competencies_records") or []), 2)
		parent_factor = slice_factor(setup["total_slices"], total)
		if parent_factor is not None:
			self.score_factor = parent_factor
		self.score = flt(total * flt(self.score_factor) / 100, 2)