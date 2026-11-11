# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EvaluationCategoriseSets(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.score_factor_scale.score_factor_scale import ScoreFactorScale
		from people.performance.doctype.competency_sets_items.competency_sets_items import CompetencySetsItems

		categorise_calculation: DF.Table[ScoreFactorScale]
		category_set: DF.Data | None
		classification: DF.Autocomplete | None
		competency_sets_items: DF.Table[CompetencySetsItems]
		items_calculation: DF.Table[ScoreFactorScale]
		score_formula: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluation Categorise Sets"