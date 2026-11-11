# Copyright (c) 2026, Mohamed Kheir and contributors
# For license information, please see license.txt

import csv
import io

import frappe
from frappe import _
from frappe.model.document import Document

# اسم نوع التقييم الذاتي كما هو مسجل عندك في Evaluation Categories
SELF_CATEGORY = "Self Evaluation"


class EvaluationCycles(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from people.people.doctype.evaluation_cycles_participants.evaluation_cycles_participants import EvaluationCyclesParticipants
		from people.people.doctype.evaluation_rates.evaluation_rates import EvaluationRates

		evaluation_cycle: DF.Data | None
		evaluation_rates: DF.Table[EvaluationRates]
		forms_assignment: DF.Table[EvaluationCyclesParticipants]
		status: DF.Autocomplete | None
	# end: auto-generated types

	pass


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
@frappe.whitelist()
def create_evaluations(cycle: str) -> dict:
	cycle_doc = frappe.get_doc("Evaluation Cycles", cycle)

	# صلاحيات: لازم يقدر يعدل الدورة ويعمل Competencies
	cycle_doc.check_permission("write")
	frappe.has_permission("Competencies", "create", throw=True)

	jobs, failures = EvaluationsBuilder(cycle_doc).plan()
	participants_count = len({j["emp_id"] for j in jobs} | {f[2].get("emp_id") for f in failures})
	evaluations_count = len(jobs)

	if not participants_count:
		frappe.throw(_("No participants with Employee ID in this cycle"))
	if not evaluations_count:
		frappe.throw(
			_("Nothing to create. All {0} participants have setup problems, check forms and committees.").format(
				len(failures)
			)
		)

	# منع التشغيل مرتين لنفس الدورة في نفس الوقت
	if frappe.db.exists(
		"Background Task",
		{
			"ref_doctype": "Evaluation Cycles",
			"ref_docname": cycle,
			"method": RUN_METHOD,
			"status": ("in", ["Queued", "Running"]),
		},
	):
		frappe.throw(_("Evaluations are already being created for this cycle. Wait until it finishes."))

	employees_label = _("Employee") if participants_count == 1 else _("Employees")
	evaluations_label = _("Evaluation") if evaluations_count == 1 else _("Evaluations")

	task = frappe.enqueue_task(
		run_create_evaluations,
		task_name=_("Create Evaluations: {0} ({1} {2}, {3} {4})").format(
			cycle, participants_count, employees_label, evaluations_count, evaluations_label
		),
		queue="long",
		timeout=3600,
		ref_doctype="Evaluation Cycles",
		ref_docname=cycle,
		show_progress_bar=True,
		allow_user_cancellation=True,
		allow_user_retry=True,
		cycle=cycle,
	)

	return {"task_id": task.task_id, "task_name": task.task_name}


@frappe.whitelist()
def get_evaluations_result(cycle: str, task_id: str | None = None) -> dict | None:
	"""ترجع نتيجة مهمة معينة، أو آخر مهمة خلصت للدورة لو مفيش task_id."""
	frappe.get_doc("Evaluation Cycles", cycle).check_permission("write")

	filters = {"ref_doctype": "Evaluation Cycles", "ref_docname": cycle, "method": RUN_METHOD}
	if task_id:
		filters["task_id"] = task_id
	else:
		filters["status"] = "Completed"

	task = frappe.db.get_value(
		"Background Task",
		filters,
		["task_id", "status", "result", "ended_at"],
		as_dict=True,
		order_by="creation desc",
	)
	if not task:
		return None

	task.result = frappe.parse_json(task.result) if task.result else None
	return task


# ----------------------------------------------------------------------
# Background job
# ----------------------------------------------------------------------
def run_create_evaluations(cycle: str) -> dict:
	cycle_doc = frappe.get_doc("Evaluation Cycles", cycle)
	task = frappe.get_current_task()

	report = EvaluationsBuilder(cycle_doc, task).run()

	# ملف CSV بالنتيجة مرفق على الدورة نفسها
	if task:
		task.update_stage(_("Preparing report file"))
		report["csv_url"] = task.attach_file(
			file_name=f"Evaluations - {cycle} - {frappe.utils.now_datetime():%Y-%m-%d %H-%M}.csv",
			content=_report_to_csv(report),
			is_private=True,
			doctype="Evaluation Cycles",
			docname=cycle,
		)

	# القيمة اللي بترجع بتتخزن أوتوماتيك في result بتاع الـ Background Task
	return report


RUN_METHOD = f"{run_create_evaluations.__module__}.{run_create_evaluations.__qualname__}"


class EvaluationsBuilder:
	def __init__(self, cycle_doc, task=None):
		self.cycle = cycle_doc
		self.task = task
		self.report = {"competencies": _new_counter()}

		# كاش جوه نفس التشغيلة عشان مانحملش نفس الـ document كذا مرة
		self._forms = {}
		self._form_categories = {}
		self._sets = {}
		self._committees = {}

	# ------------------------------------------------------------------
	# Main flow
	# ------------------------------------------------------------------
	def plan(self):
		"""
		تجهز كل التقييمات المطلوبة قبل ما نبدأ ننشئ أي حاجة.
		jobs: كل تقييم هيتعمل (موظف + مقيّم + نوع + كفاءاته)
		failures: مشاكل الإعداد، كل واحدة (label, detail, ctx)
		"""
		jobs, failures = [], []
		for participant in self.cycle.get("forms_assignment") or []:
			if participant.get("emp_id"):
				self.plan_participant(participant, jobs, failures)
		return jobs, failures

	def run(self) -> dict:
		counter = self.report["competencies"]
		jobs, failures = self.plan()

		for label, detail, ctx in failures:
			_add(counter, "failed", label, detail, ctx)

		existing = self.get_existing_keys()
		total = len(jobs)

		for i, job in enumerate(jobs, start=1):
			self.create(counter, job, existing)
			self.publish_progress(i, total)

		return self.report

	def publish_progress(self, done, total):
		# publish_progress فيها throttle داخلي، فمناداتها مع كل تقييم مش مشكلة
		if not self.task or not total:
			return
		self.task.publish_progress(
			round(done / total * 100),
			stage=_("Processed {0} of {1} evaluations").format(done, total),
		)

	def plan_participant(self, participant, jobs, failures):
		emp_id = participant.get("emp_id")
		emp_ctx = {"emp_id": emp_id}

		def fail(detail):
			failures.append((emp_id, detail, emp_ctx))

		form_name = participant.get("evaluation_form")
		if not form_name:
			return fail(_("No evaluation form"))

		form = self.get_form(form_name)
		if not form:
			return fail(_("Evaluation form {0} not found").format(form_name))

		committee_name = participant.get("evaluation_committee")
		if not committee_name:
			return fail(_("No evaluation committee"))

		evaluators = self.get_evaluators(committee_name)
		if evaluators is None:
			return fail(_("Evaluation committee {0} not found").format(committee_name))

		evaluators = self.with_self_evaluation(emp_id, form, evaluators)
		if not evaluators:
			return fail(_("No evaluators in committee {0}").format(committee_name))

		for evaluator_id, category in evaluators:
			label = f"{emp_id} / {evaluator_id} ({category or '-'})"
			ctx = {"emp_id": emp_id, "evaluator_id": evaluator_id, "category": category}

			if evaluator_id == emp_id and category != SELF_CATEGORY:
				failures.append((label, _("Employee cannot evaluate himself as {0}").format(category), ctx))
				continue

			items, error = self.get_competency_items(form, category)
			if error:
				failures.append((label, error, ctx))
				continue

			jobs.append({**ctx, "label": label, "items": items})

	def get_existing_keys(self):
		"""كل التقييمات الموجودة للدورة في query واحدة، بدل exists لكل تقييم."""
		rows = frappe.get_all(
			"Competencies",
			filters={"evaluation_cycle": self.cycle.name},
			fields=["emp_id", "evaluator_id", "evaluation_category"],
		)
		return {(r.emp_id, r.evaluator_id, r.evaluation_category) for r in rows}

	# ------------------------------------------------------------------
	# Evaluators
	# ------------------------------------------------------------------
	def get_evaluators(self, committee_name):
		"""ترجع list من (evaluator_id, category)، أو None لو اللجنة مش موجودة."""
		if committee_name in self._committees:
			return self._committees[committee_name]

		if not frappe.db.exists("Evaluation Committees", committee_name):
			self._committees[committee_name] = None
			return None

		committee = frappe.get_doc("Evaluation Committees", committee_name)
		out, seen = [], set()
		for row in committee.get("evaluation_committees_records") or []:
			evaluator_id = row.get("evaluator_id")
			category = row.get("evaluation_category")
			if not evaluator_id:
				continue
			key = (evaluator_id, category)
			if key in seen:
				continue
			seen.add(key)
			out.append(key)

		self._committees[committee_name] = out
		return out

	def with_self_evaluation(self, emp_id, form, evaluators):
		"""يضيف التقييم الذاتي تلقائي لو الفورم فيها Self ومش موجود في اللجنة."""
		if SELF_CATEGORY not in self.get_form_categories(form):
			return evaluators

		self_key = (emp_id, SELF_CATEGORY)
		if self_key in evaluators:
			return evaluators
		return [self_key, *evaluators]

	# ------------------------------------------------------------------
	# Form & competency sets
	# ------------------------------------------------------------------
	def get_form(self, form_name):
		if form_name not in self._forms:
			self._forms[form_name] = (
				frappe.get_doc("Evaluation Forms", form_name)
				if frappe.db.exists("Evaluation Forms", form_name)
				else None
			)
		return self._forms[form_name]

	def get_form_categories(self, form):
		if form.name not in self._form_categories:
			self._form_categories[form.name] = {
				row.get("evaluation_category"): row
				for row in form.get("competencies_categories") or []
				if row.get("evaluation_category")
			}
		return self._form_categories[form.name]

	def get_set(self, set_name):
		if set_name not in self._sets:
			self._sets[set_name] = (
				frappe.get_doc("Evaluation Categorise Sets", set_name)
				if frappe.db.exists("Evaluation Categorise Sets", set_name)
				else None
			)
		return self._sets[set_name]

	def get_competency_items(self, form, category):
		"""ترجع (items, None) لو تمام، أو (None, error) لو فيه مشكلة."""
		if not category:
			return None, _("Evaluator has no evaluation category")

		row = self.get_form_categories(form).get(category)
		if not row:
			return None, _("Category {0} is not defined in form {1}").format(category, form.name)

		set_name = row.get("competency_sets")
		if not set_name:
			return None, _("No competency set for category {0} in form {1}").format(category, form.name)

		comp_set = self.get_set(set_name)
		if not comp_set:
			return None, _("Competency set {0} not found").format(set_name)

		items = [
			{"competency": it.get("competency"), "weight": it.get("weight")}
			for it in comp_set.get("competency_sets_items") or []
			if it.get("competency")
		]
		if not items:
			return None, _("Competency set {0} has no competencies").format(set_name)

		return items, None

	# ------------------------------------------------------------------
	# Create
	# ------------------------------------------------------------------
	def create(self, counter, job, existing):
		label = job["label"]
		ctx = {k: job[k] for k in ("emp_id", "evaluator_id", "category")}
		key = (job["emp_id"], job["evaluator_id"], job["category"])

		if key in existing:
			return _add(counter, "skipped", label, _("Already exists"), ctx)

		save_point = f"ce_{frappe.generate_hash(length=10)}"
		frappe.db.savepoint(save_point)
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Competencies",
					"evaluation_cycle": self.cycle.name,
					"emp_id": job["emp_id"],
					"evaluator_id": job["evaluator_id"],
					"evaluation_category": job["category"],
				}
			)
			for row in job["items"]:
				doc.append("competencies_records", row)
			doc.insert()
			frappe.db.release_savepoint(save_point)
			existing.add(key)
			_add(counter, "created", label, doc.name, ctx)
		except Exception as e:
			frappe.db.rollback(save_point=save_point)
			frappe.clear_last_message()
			frappe.log_error(
				title=f"Create Evaluation failed: {label}",
				message=frappe.get_traceback(),
				reference_doctype="Evaluation Cycles",
				reference_name=self.cycle.name,
			)
			_add(counter, "failed", label, frappe.utils.strip_html(str(e)) or e.__class__.__name__, ctx)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _new_counter():
	return {
		"created": 0,
		"skipped": 0,
		"failed": 0,
		"created_list": [],
		"skipped_list": [],
		"failed_list": [],
	}


def _add(counter, status, label, detail=None, ctx=None):
	"""ctx: emp_id / evaluator_id / category عشان الواجهة تعرضهم في أعمدة."""
	counter[status] += 1
	counter[f"{status}_list"].append({"label": label, "detail": detail, **(ctx or {})})


def _report_to_csv(report) -> bytes:
	c = report["competencies"]
	buf = io.StringIO()
	writer = csv.writer(buf)
	writer.writerow(["Employee", "Evaluator", "Category", "Status", "Detail"])
	for status in ("failed", "skipped", "created"):
		for r in c[f"{status}_list"]:
			writer.writerow(
				[
					r.get("emp_id") or r.get("label"),
					r.get("evaluator_id") or "",
					r.get("category") or "",
					status.title(),
					r.get("detail") or "",
				]
			)
	# utf-8-sig عشان Excel يقرأ العربي صح
	return buf.getvalue().encode("utf-8-sig")
