# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Evaluations(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		emp_id: DF.Link | None
		emp_preferred_name: DF.Data | None
		evaluation_cycle: DF.Link | None
		job: DF.Link | None
		position: DF.Link | None
		score: DF.Percent
	# end: auto-generated types

	_DOCTYPE_NAME = "Evaluations"
