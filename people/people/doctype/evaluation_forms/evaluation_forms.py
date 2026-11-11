# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EvaluationForms(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.competencies_categories.competencies_categories import CompetenciesCategories
		from people.people.doctype.evaluation_rates.evaluation_rates import EvaluationRates

		amended_from: DF.Link | None
		competencies_weight: DF.Percent
		evaluation_form: DF.Data | None
		evaluation_form_competencies: DF.Table[CompetenciesCategories]
		evaluation_rates: DF.Table[EvaluationRates]
		goals_weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Forms"
