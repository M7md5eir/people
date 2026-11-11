# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

import frappe
from frappe.model import no_value_fields
from frappe.model.document import Document
from frappe.utils import flt


class EvaluationsForms(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.competencies_distribution.competencies_distribution import CompetenciesDistribution
		from people.people.doctype.evaluations_rates.evaluations_rates import EvaluationsRates
		from people.people.doctype.goals_distribution.goals_distribution import GoalsDistribution

		amended_from: DF.Link | None
		competencies_distribution: DF.Table[CompetenciesDistribution]
		competencies_weight: DF.Percent
		evaluation_form: DF.Data | None
		evaluations_rates: DF.Table[EvaluationsRates]
		goals_distribution: DF.Table[GoalsDistribution]
		goals_weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluations Forms"

	DISTRIBUTION_TABLES = ("goals_distribution", "competencies_distribution")
	NESTED_TABLES = {
		"competencies_calc_individual": {
			"doctype": "Evaluations Calculations",
			"onload_key": "calculations",
			"parents": ("Competencies Distribution",),
		},
		"competencies_calc": {
			"doctype": "Evaluations Calculations",
			"onload_key": "competencies_calcs",
			"parents": ("Competencies Distribution",),
		},
		"goals_calc_individual": {
			"doctype": "Evaluations Calculations",
			"onload_key": "calculations",
			"parents": ("Goals Distribution",),
		},
		"goals_calc": {
			"doctype": "Evaluations Calculations",
			"onload_key": "breakdowns",
			"parents": ("Goals Distribution",),
		},
		"goals_parts_breakdowns": {
			"doctype": "Goals Parts Breakdowns",
			"onload_key": "parts_breakdowns",
			"parents": ("Goals Distribution",),
		},
		"competencies_mapping": {
			"doctype": "Competencies Mapping",
			"onload_key": "mappings",
			"parents": ("Competencies Distribution",),
		},
	}

	def onload(self):
		self.load_nested_tables()

	def validate(self):
		self.remove_empty_first_column_rows()

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
			for r in self.all_rows()
			if r.get("name") and self._row_doctype(r) in allowed
		]

	@staticmethod
	def _row_doctype(row):
		doctype = getattr(row, "doctype", None)
		if doctype:
			return doctype
		if isinstance(row, dict):
			return row.get("doctype")
		return None

	def all_rows(self):
		ordered = []
		seen = set()
		queue = list(self.get_distribution_rows())
		while queue:
			row = queue.pop(0)
			name = row.get("name") if hasattr(row, "get") else None
			if not name or name in seen:
				continue
			seen.add(name)
			ordered.append(row)
			for field in self.NESTED_TABLES:
				children = row.get(field) if hasattr(row, "get") else None
				for child in children or []:
					name = child.get("name") if hasattr(child, "get") else None
					if name and name not in seen:
						queue.append(child)
		return ordered

	@staticmethod
	def first_column_field(doctype):
		for df in frappe.get_meta(doctype).fields:
			if df.fieldtype not in no_value_fields:
				return df.fieldname
		return None

	@staticmethod
	def is_empty(value):
		return value is None or (isinstance(value, str) and not value.strip())

	def iter_tables_with_doctype(self):
		for table in self.DISTRIBUTION_TABLES:
			yield self.meta.get_label(table) or table, self, table, self.meta.get_field(table).options
		for field, cfg in self.NESTED_TABLES.items():
			for row in self.all_rows():
				if self._row_doctype(row) not in cfg["parents"]:
					continue
				yield f"{self._row_doctype(row)} / {cfg['doctype']}", row, field, cfg["doctype"]

	def remove_empty_first_column_rows(self):
		for _label, holder, field, doctype in self.iter_tables_with_doctype():
			rows = holder.get(field) or []
			kept = [d for d in rows if not self.is_blank_row(doctype, d)]
			if len(kept) != len(rows):
				if isinstance(holder, Document):
					holder.set(field, kept)
				else:
					holder[field] = kept

	@staticmethod
	def is_blank_row(doctype, d):
		for df in frappe.get_meta(doctype).fields:
			if df.fieldtype in no_value_fields:
				continue
			if df.fieldtype == "Table":
				if d.get(df.fieldname):
					return False
				continue
			value = d.get(df.fieldname)
			if value is None:
				continue
			if isinstance(value, str) and not value.strip():
				continue
			return False
		return True

	@staticmethod
	def is_zero_weight(d):
		weight = d.get("weight")
		return weight is not None and flt(weight) == 0

	def load_nested_tables(self):
		onload = self.get("__onload") or frappe._dict()
		for field, cfg in self.NESTED_TABLES.items():
			rows = self.rows_for(field)
			by_row = {r.get("name"): [] for r in rows}
			if rows:
				fields = ["name", "parent", "idx", *self.business_fields(cfg["doctype"])]
				for rec in frappe.get_all(
					cfg["doctype"],
					filters={"parent": ["in", [r.get("name") for r in rows]], "parentfield": field},
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
							"parent": row.get("name"),
							"parentfield": field,
							"parenttype": self._row_doctype(row),
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
				{
					"parent": row.get("name"),
					"parenttype": self._row_doctype(row),
					"parentfield": field,
				},
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
