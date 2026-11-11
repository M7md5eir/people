# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model import no_value_fields
from frappe.model.document import Document
from frappe.utils import flt


class EmployeesGoals(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.goals_evaluation_entry.goals_evaluation_entry import GoalsEvaluationEntry

		amended_from: DF.Link | None
		category: DF.Data | None
		emp_id: DF.Link | None
		emp_position: DF.Link | None
		emp_preferred_name: DF.Data | None
		evaluation_cycle: DF.Link | None
		factor: DF.Percent
		goals_evaluation_entry: DF.Table[GoalsEvaluationEntry]
		job: DF.Link | None
		score: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Employees Goals"

	DISTRIBUTION_TABLES = ("goals_evaluation_entry",)
	NESTED_TABLES = {
		"kpis_evaluation_entry": {
			"doctype": "KPIs Evaluation Entry",
			"onload_key": "kpis",
			"parents": ("Goals Evaluation Entry",),
		},
	}

	def onload(self):
		self.load_nested_tables()

	def after_insert(self):
		self.sync_nested_tables()

	def on_update(self):
		self.sync_nested_tables()

	def on_update_after_submit(self):
		self.sync_nested_tables()

	def on_trash(self):
		for row in self.get_distribution_rows():
			for field in self.NESTED_TABLES:
				self.clear_nested_table(row, field)
		for field in self.NESTED_TABLES:
			self.delete_orphan_rows(field)

	def get_distribution_rows(self):
		rows = []
		for table in self.DISTRIBUTION_TABLES:
			rows.extend(self.get(table) or [])
		return rows

	def rows_for(self, field):
		allowed = self.NESTED_TABLES[field]["parents"]
		return [
			r
			for r in self.get_distribution_rows()
			if r.get("name") and r.doctype in allowed
		]

	@staticmethod
	def first_column_field(doctype):
		for df in frappe.get_meta(doctype).fields:
			if df.fieldtype not in no_value_fields:
				return df.fieldname
		return None

	@staticmethod
	def is_empty(value):
		return value is None or (isinstance(value, str) and not value.strip())

	@staticmethod
	def kpis_row_score(d):
		planned = flt(d.get("planned"))
		achieved = flt(d.get("achived"))
		weight = flt(d.get("weight"))
		if not planned or not weight:
			return 0
		if d.get("reverse_calc") and not achieved:
			return flt(weight, 2)
		if d.get("reverse_calc"):
			return flt(planned / achieved * weight, 2) if achieved else 0
		return flt(achieved / planned * weight, 2)

	def load_nested_tables(self):
		onload = self.get("__onload") or frappe._dict()
		for field, cfg in self.NESTED_TABLES.items():
			rows = self.rows_for(field)
			by_row = {r.name: [] for r in rows}
			if rows:
				fields = ["name", "parent", "idx", *self.business_fields(cfg["doctype"])]
				for rec in frappe.get_all(
					cfg["doctype"],
					filters={"parent": ["in", [r.name for r in rows]], "parentfield": field},
					fields=fields,
					order_by="idx asc",
				):
					by_row.setdefault(rec.parent, []).append(rec)
			merged = onload.get(cfg["onload_key"]) or {}
			merged.update(by_row)
			onload[cfg["onload_key"]] = merged
		self.set("__onload", onload)

	def sync_nested_tables(self):
		onload = self.get("__onload") or frappe._dict()
		for field, cfg in self.NESTED_TABLES.items():
			cached = onload.get(cfg["onload_key"]) or {}
			for row in self.rows_for(field):
				wanted = [self.to_dict(d) for d in row.get(field) or []]
				if not wanted and row.get("name") not in cached:
					continue
				self.clear_nested_table(row, field)
				for i, d in enumerate(wanted, start=1):
					values = {k: d.get(k) for k in self.business_fields(cfg["doctype"])}
					if d.get("name") and not str(d.get("name")).startswith("new-"):
						values["name"] = d.get("name")
					values.update(
						{
							"doctype": cfg["doctype"],
							"parent": row.name,
							"parentfield": field,
							"parenttype": row.doctype,
							"idx": i,
						}
					)
					if values.get("name"):
						frappe.get_doc(values).db_insert()
					else:
						frappe.get_doc(values).insert()
			self.delete_orphan_rows(field)

	def clear_nested_table(self, row, field):
		if row.get("name"):
			cfg = self.NESTED_TABLES[field]
			frappe.db.delete(
				cfg["doctype"],
				{"parent": row.name, "parenttype": row.doctype, "parentfield": field},
			)

	@staticmethod
	def to_dict(d):
		if isinstance(d, Document):
			return d.as_dict()
		return dict(d)

	@staticmethod
	def business_fields(doctype):
		return [
		df.fieldname
		for df in frappe.get_meta(doctype).fields
		if df.fieldtype not in no_value_fields
	]

	def delete_orphan_rows(self, field):
		cfg = self.NESTED_TABLES[field]
		sources = " UNION ".join(f"SELECT name FROM `tab{p}`" for p in cfg["parents"])
		frappe.db.sql(
			f"""DELETE FROM `tab{cfg["doctype"]}`
				WHERE parenttype IN %(types)s
				AND parent NOT IN ({sources})""",
			{"types": cfg["parents"]},
		)

	def validate(self):
		from people.people.doctype.goals_evaluation_entry.goals_evaluation_entry import (
			CALCULATION_METHODS,
			entry_score_for_method,
			get_calculation_method,
			get_factor_for_kpis,
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

		for row in self.get_distribution_rows():
			for field, cfg in self.NESTED_TABLES.items():
				if row.doctype not in cfg["parents"]:
					continue
				first = self.first_column_field(cfg["doctype"])
				if not first:
					continue
				rows = row.get(field) or []
				kept = [d for d in rows if not self.is_empty(d.get(first))]
				if len(kept) != len(rows):
					row.set(field, kept)

		rows = self.goals_evaluation_entry or []
		kept = [r for r in rows if r.get("weight") is None or flt(r.get("weight")) != 0]
		if len(kept) != len(rows):
			self.set("goals_evaluation_entry", kept)

		for row in self.goals_evaluation_entry or []:
			nested = row.get("kpis_evaluation_entry") or []
			for d in nested:
				score = self.kpis_row_score(d)
				if isinstance(d, Document):
					d.score = score
				else:
					d["score"] = score
			row.kpis_num = len(nested)
			row.kpis_score = flt(sum(flt(d.get("score") or 0) for d in nested), 2)
			factor = get_factor_for_kpis(
				self.evaluation_cycle, self.category, self.emp_id, row.kpis_score
			)
			if factor is not None:
				row.factor = factor
			row.score = entry_score_for_method(method, row.weight, row.factor, row.kpis_score)

		total = flt(sum(flt(row.score) for row in self.goals_evaluation_entry or []), 2)
		parent_factor = get_factor_for_total(
			self.evaluation_cycle, self.category, self.emp_id, total
		)
		if parent_factor is not None:
			self.factor = parent_factor
		self.score = flt(total * flt(self.factor) / 100, 2)


@frappe.whitelist()
def get_kpis_for_goal(goal: str) -> list:
	"""KPIs mapped to a goal (ordered by idx)."""
	if not goal:
		return []
	return [
		{"kpi": r.kpi}
		for r in frappe.get_all(
			"KPIs Mapping",
			filters={"parent": goal},
			fields=["kpi"],
			order_by="idx asc",
		)
		if r.kpi
	]


@frappe.whitelist()
def compute_goal_scores(
	evaluation_cycle: str | None,
	category: str | None,
	emp_id: str | None,
	rows: list | str,
) -> dict:
	"""Entry + parent factors/scores for dialog save (no DB writes)."""
	from people.people.doctype.goals_evaluation_entry.goals_evaluation_entry import (
		CALCULATION_METHODS,
		entry_score_for_method,
		get_calculation_method,
		get_factor_for_kpis,
		get_factor_for_total,
	)

	method = get_calculation_method(evaluation_cycle, emp_id, category)
	if method not in CALCULATION_METHODS:
		frappe.throw(
			"Calculation Method {0} is not supported for {1}".format(
				frappe.bold(method or frappe._("Empty")),
				frappe.bold(category or ""),
			)
		)

	rows = frappe.parse_json(rows) if isinstance(rows, str) else (rows or [])
	out = []
	for r in rows:
		r = dict(r or {})
		factor = get_factor_for_kpis(
			evaluation_cycle, category, emp_id, r.get("kpis_score")
		)
		if factor is None:
			factor = flt(r.get("factor"))
		score = entry_score_for_method(method, r.get("weight"), factor, r.get("kpis_score"))
		out.append({"factor": factor, "score": score})
	total = flt(sum(flt(r["score"]) for r in out), 2)
	parent_factor = get_factor_for_total(evaluation_cycle, category, emp_id, total)
	if parent_factor is None:
		parent_factor = 0
	return {
		"rows": out,
		"parent_factor": parent_factor,
		"parent_score": flt(total * flt(parent_factor) / 100, 2),
	}
