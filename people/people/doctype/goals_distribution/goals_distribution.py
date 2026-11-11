# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GoalsDistribution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.evaluations_calculations.evaluations_calculations import EvaluationsCalculations
		from people.people.doctype.goals_parts_breakdowns.goals_parts_breakdowns import GoalsPartsBreakdowns

		calculation_method: DF.Autocomplete | None
		category: DF.Autocomplete | None
		goals_calc: DF.Table[EvaluationsCalculations]
		goals_calc_individual: DF.Table[EvaluationsCalculations]
		goals_parts_breakdowns: DF.Table[GoalsPartsBreakdowns]
		overachievement: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		weight: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Goals Distribution"
