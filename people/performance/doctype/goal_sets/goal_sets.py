# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GoalSets(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.score_factor_scale.score_factor_scale import ScoreFactorScale

		calculation_method: DF.Autocomplete | None
		category_factor_scale: DF.Table[ScoreFactorScale]
		competency_set: DF.Data | None
		item_factor_scale: DF.Table[ScoreFactorScale]
	# end: auto-generated types

	_DOCTYPE_NAME = "Goals Sets"
