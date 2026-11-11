# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model import no_value_fields
from frappe.model.document import Document


class EvaluationsCycles(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.evaluations_mapping.evaluations_mapping import EvaluationsMapping

		evaluation_cycle: DF.Data | None
		evaluations_mapping: DF.Table[EvaluationsMapping]
		status: DF.Autocomplete | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Cycle"

	DISTRIBUTION_TABLES = ("evaluations_mapping",)
	NESTED_TABLES = {
		"evaluators_mapping": {
			"doctype": "Evaluators Mapping",
			"onload_key": "evaluators",
			"parents": ("Evaluations Mapping",),
		},
	}

	def onload(self):
		self.load_nested_tables()

	def validate(self):
		self.remove_empty_first_column_rows()
		self.remove_empty_emp_id_rows()

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

	def remove_empty_first_column_rows(self):
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

	def remove_empty_emp_id_rows(self):
		rows = self.get("evaluations_mapping") or []
		kept = [r for r in rows if not self.is_empty(r.get("emp_id"))]
		if len(kept) != len(rows):
			self.set("evaluations_mapping", kept)

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


@frappe.whitelist()
def create_evaluations(cycle: str) -> dict:
	"""Create evaluation docs for a cycle.

	- One Competencies Evaluation per mapping employee and evaluator.
	- One Goals Evaluation per mapping employee when its form has an
	  Employee Goals distribution.
	- One Organization Goals Evaluation per org-tree ancestor (at the
	  weight-breakdown levels) of each mapping employee when its form has
	  an Organization Goals distribution.
	Existing docs are skipped, failures are collected per doc.
	"""
	cycle_doc = frappe.get_doc("Evaluations Cycles", cycle)
	mappings = [
		m for m in cycle_doc.get("evaluations_mapping") or [] if m.get("emp_id")
	]
	evaluators_by_parent = {}
	if mappings:
		for ev in frappe.get_all(
			"Evaluators Mapping",
			filters={
				"parent": ["in", [m.name for m in mappings]],
				"parenttype": "Evaluations Mapping",
				"parentfield": "evaluators_mapping",
			},
			fields=["parent", "evl_id", "category"],
		):
			if ev.get("evl_id"):
				evaluators_by_parent.setdefault(ev.get("parent"), []).append(ev)
	report = {
		"competencies": {"created": 0, "skipped": 0, "failed": 0, "created_list": [], "skipped_list": [], "failed_list": []},
		"goals_employee": {"created": 0, "skipped": 0, "failed": 0, "created_list": [], "skipped_list": [], "failed_list": []},
		"goals_org": {"created": 0, "skipped": 0, "failed": 0, "created_list": [], "skipped_list": [], "failed_list": []},
		"evaluation": {"created": 0, "skipped": 0, "failed": 0, "created_list": [], "skipped_list": [], "failed_list": []},
	}
	for mapping in mappings:
		_create(
			report["evaluation"],
			"Evaluation",
			{
				"evaluation_cycle": cycle_doc.name,
				"emp_id": mapping.get("emp_id"),
			},
			mapping.get("emp_id"),
			extra_children={
				"competencies_collection": [
					{
						"category": item["category"],
						"weight": item["weight"],
						"doctype": "Competencies Collection",
					}
					for item in _related_categories(
						cycle_doc.name, mapping.get("emp_id")
					)
				]
			},
		)
	for mapping in mappings:
		for evaluator in evaluators_by_parent.get(mapping.name, []):
			_create(
				report["competencies"],
				"Competencies Evaluation",
				{
					"evaluation_cycle": cycle_doc.name,
					"emp_id": mapping.get("emp_id"),
					"evl_id": evaluator.get("evl_id"),
					"category": evaluator.get("category"),
				},
				mapping.get("emp_id"),
			)
		form = mapping.get("evaluation_form")
		if not form:
			continue
		dists = frappe.get_all(
			"Goals Distribution",
			filters={"parent": form},
			fields=["name", "category"],
		)
		for dist in dists:
			category = dist.get("category") or ""
			if "employee goals" in category.lower():
				_create(
					report["goals_employee"],
					"Employees Goals",
					{
						"evaluation_cycle": cycle_doc.name,
						"emp_id": mapping.get("emp_id"),
						"category": dist.get("category"),
					},
					mapping.get("emp_id"),
				)
			if "organization goals" in category.lower():
				levels = {
					p.get("category")
					for p in frappe.get_all(
						"Goals Parts Breakdowns",
						filters={"parent": dist.get("name")},
						fields=["category"],
					)
					if p.get("category")
				}
				if not levels:
					continue
				ancestors = _ancestors_by_level(
					frappe.db.get_value("Employees", mapping.get("emp_id"), "organization")
				)
				for level in levels:
					org_name = ancestors.get(level)
					if not org_name:
						continue
					_create(
						report["goals_org"],
						"Organizations Goals",
						{
							"evaluation_cycle": cycle_doc.name,
							"organization": org_name,
							"category": dist.get("category"),
						},
						org_name,
					)
	return report


def _ancestors_by_level(org):
	"""Map organization_level -> organization name walking up the tree."""
	out = {}
	seen = set()
	while org and org not in seen:
		seen.add(org)
		level, parent = frappe.db.get_value(
			"Organizations", org, ["organization_level", "parent_organizations"]
		) or (None, None)
		if level and level not in out:
			out[level] = org
		org = parent
	return out


def _related_categories(evaluation_cycle, emp_id):
	"""Category + weight behind one employee+cycle, via mapping form."""
	if not (evaluation_cycle and emp_id):
		return []
	form = frappe.db.get_value(
		"Evaluations Mapping",
		{"parent": evaluation_cycle, "emp_id": emp_id},
		"evaluation_form",
		order_by="idx asc",
	)
	if not form:
		return []
	seen = []
	out = []
	for rec in frappe.db.get_values(
		"Competencies Distribution",
		{"parent": form},
		["category", "weight"],
		order_by="idx asc",
		as_dict=True,
	):
		if rec.category and rec.category not in seen:
			seen.append(rec.category)
			out.append({"category": rec.category, "weight": rec.weight})
	return out


def _create(counter, doctype, values, label, extra_children=None):
	"""Insert unless an identical doc exists; count created/skipped/failed."""
	match = {k: v for k, v in values.items() if k != "doctype"}
	if frappe.db.exists(doctype, match):
		counter["skipped"] += 1
		counter["skipped_list"].append(label)
		return
	_create.seq = getattr(_create, "seq", 0) + 1
	save_point = f"create_evaluations_{_create.seq}"
	frappe.db.savepoint(save_point)
	try:
		doc = frappe.get_doc({"doctype": doctype, **values})
		for field, rows in (extra_children or {}).items():
			for row in rows:
				doc.append(field, row)
		doc.insert()
		frappe.db.release_savepoint(save_point)
		counter["created"] += 1
		counter["created_list"].append(label)
	except Exception:
		frappe.db.rollback(save_point=save_point)
		counter["failed"] += 1
		counter["failed_list"].append(label)
