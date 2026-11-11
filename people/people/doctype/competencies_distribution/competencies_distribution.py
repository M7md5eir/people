# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompetenciesDistribution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.competencies_mapping.competencies_mapping import CompetenciesMapping
		from people.people.doctype.evaluations_calculations.evaluations_calculations import EvaluationsCalculations

		category: DF.Autocomplete | None
		competencies_calc: DF.Table[EvaluationsCalculations]
		competencies_calc_individual: DF.Table[EvaluationsCalculations]
		competencies_mapping: DF.Table[CompetenciesMapping]
		info: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Competencies Distribution"
