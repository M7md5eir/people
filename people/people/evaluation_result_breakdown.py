import frappe
from frappe.utils import flt

NEUTRAL_COLOR = "#8d99a6"
PRIVILEGED_ROLES = ("HR Manager", "System Manager")
COMPLETED = "Completed"
PENDING = "Pending"


@frappe.whitelist()
def get_result_breakdown(evaluation_cycle: str, emp_id: str) -> dict:
	"""Live competencies breakdown for one employee and cycle.

	Nothing is stored: scores are recomputed from submitted Competencies docs.
	Evaluator identities are only returned for HR Manager / System Manager.
	"""
	frappe.has_permission("Evaluations", "read", throw=True)
	if not (evaluation_cycle and emp_id):
		return empty_result()

	docs = get_competency_docs(evaluation_cycle, emp_id)
	records = get_competency_records([doc.name for doc in docs])
	names = get_competency_names(records)
	weights = get_category_weights(evaluation_cycle, emp_id)
	rates = get_rates(evaluation_cycle)

	return build_breakdown(docs, records, names, weights, rates, is_privileged())


def empty_result() -> dict:
	return {"competencies_score": 0.0, "rates": [], "categories": []}


def get_competency_docs(evaluation_cycle, emp_id):
	return frappe.db.get_all(
		"Competencies",
		filters={
			"evaluation_cycle": evaluation_cycle,
			"emp_id": emp_id,
			"docstatus": ("<", 2),
		},
		fields=[
			"name",
			"evaluation_category",
			"evaluator_id",
			"evaluator_name",
			"score",
			"docstatus",
		],
		order_by="name asc",
	)


def get_competency_records(parents):
	if not parents:
		return []
	return frappe.db.get_all(
		"Competencies Records",
		filters={"parent": ("in", parents)},
		fields=["parent", "competency", "weight", "rating", "idx"],
		order_by="idx asc",
	)


def get_competency_names(records):
	keys = list({row.competency for row in records if row.competency})
	if not keys:
		return {}
	rows = frappe.db.get_all(
		"Competency Definitions",
		filters={"name": ("in", keys)},
		fields=["name", "competence"],
	)
	return {row.name: row.competence or row.name for row in rows}


def get_category_weights(evaluation_cycle, emp_id):
	form = frappe.db.get_value(
		"Evaluation Cycles Participants",
		{
			"parent": evaluation_cycle,
			"parentfield": "forms_assignment",
			"emp_id": emp_id,
		},
		"evaluation_form",
		order_by="idx asc",
	)
	if not form:
		return []
	rows = frappe.db.get_all(
		"Competencies Categories",
		filters={"parent": form, "parenttype": "Evaluation Forms"},
		fields=["evaluation_category", "weight"],
		order_by="idx asc",
	)
	return [(row.evaluation_category or "", flt(row.weight)) for row in rows]


def get_rates(evaluation_cycle):
	rows = frappe.db.get_all(
		"Evaluation Rates",
		filters={"parent": evaluation_cycle, "parentfield": "evaluation_rates"},
		fields=["rate", "min_score", "color"],
		order_by="min_score asc",
	)
	return [
		{
			"rate": row.rate,
			"min_score": flt(row.min_score),
			"color": row.color or NEUTRAL_COLOR,
		}
		for row in rows
	]


def is_privileged() -> bool:
	return bool(set(frappe.get_roles()) & set(PRIVILEGED_ROLES))


def build_breakdown(docs, records, names, weights, rates, show_evaluators: bool) -> dict:
	"""Compute the whole breakdown from plain rows (no further queries)."""
	by_parent = {}
	for row in records:
		by_parent.setdefault(row.parent, []).append(row)

	ordered_weights = [category.strip() for category, _ in weights if category.strip()]
	weight_map = {category.strip(): weight for category, weight in weights}

	rows = [
		build_category(category, docs, by_parent, names, weight_map, show_evaluators)
		for category in category_order(docs, ordered_weights)
	]
	redistribute_weights(rows)

	total = 0.0
	for row in rows:
		row["weighted"] = flt(row["avg_score"] * row["effective_weight"] / 100, 2)
		total += row["weighted"]

	return {
		"competencies_score": flt(total, 2),
		"rates": rates,
		"categories": rows,
	}


def category_order(docs, ordered_weights):
	order = list(ordered_weights)
	for doc in docs:
		category = (doc.evaluation_category or "").strip()
		if category and category not in order:
			order.append(category)
	return order


def build_category(category, docs, by_parent, names, weight_map, show_evaluators):
	cat_docs = [doc for doc in docs if (doc.evaluation_category or "").strip() == category]
	completed = [doc for doc in cat_docs if doc.docstatus == 1]

	entry = {
		"category": category,
		"weight": flt(weight_map.get(category, 0)),
		"effective_weight": 0.0,
		"evaluators_count": len(cat_docs),
		"completed": len(completed),
		"avg_score": average([flt(doc.score) for doc in completed]),
		"weighted": 0.0,
		"competencies": build_competencies(cat_docs, by_parent, names),
	}
	if show_evaluators:
		entry["evaluators"] = build_evaluators(cat_docs, by_parent)
	return entry


def build_competencies(docs, by_parent, names):
	order, weights = [], {}
	for doc in docs:
		for row in by_parent.get(doc.name, []):
			if row.competency not in weights:
				weights[row.competency] = flt(row.weight)
				order.append(row.competency)
	return [
		{"key": key, "competency": names.get(key, key), "weight": weights[key]}
		for key in order
	]


def build_evaluators(docs, by_parent):
	evaluators = []
	for doc in docs:
		completed = doc.docstatus == 1
		ratings = {}
		if completed:
			for row in by_parent.get(doc.name, []):
				ratings[row.competency] = flt(flt(row.rating) * 100, 2)
		evaluators.append(
			{
				"evaluator_id": doc.evaluator_id,
				"evaluator_name": doc.evaluator_name or doc.evaluator_id or doc.name,
				"doc": doc.name,
				"status": COMPLETED if completed else PENDING,
				"score": flt(doc.score) if completed else None,
				"ratings": ratings,
			}
		)
	return evaluators


def redistribute_weights(rows):
	"""Spread the weight of categories without a completed doc over the rest."""
	completed_weight = sum(row["weight"] for row in rows if row["completed"])
	for row in rows:
		if row["completed"] and completed_weight:
			row["effective_weight"] = flt(row["weight"] / completed_weight * 100, 2)


def average(values):
	values = [value for value in values if value is not None]
	return flt(sum(values) / len(values), 2) if values else 0.0
