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
		from people.performance.doctype.goals_categories.goals_categories import GoalsCategories

		amended_from: DF.Link | None
		competencies_categories: DF.Table[CompetenciesCategories]
		competencies_weight: DF.Percent
		evaluation_form: DF.Data | None
		goals_categories: DF.Table[GoalsCategories]
		goals_weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Forms"
