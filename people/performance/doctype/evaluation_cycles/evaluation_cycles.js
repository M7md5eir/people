// Copyright (c) 2026, Mohamed Kheir and contributors
// For license information, please see license.txt

const EVAL_METHODS = {
	create: "people.performance.doctype.evaluation_cycles.evaluation_cycles.create_evaluations",
	result: "people.performance.doctype.evaluation_cycles.evaluation_cycles.get_evaluations_result",
};

// المهام اللي اتشغلت من الشاشة دي: task_id -> cycle
const pending_eval_tasks = {};

// handler واحد بس لكل الصفحة. ومهم نشيله بالـ handler نفسه
// عشان مانشيلش الـ listener بتاع Frappe على نفس الـ event
function on_eval_task_update(msg) {
	const cycle = pending_eval_tasks[msg.task_id];
	if (!cycle || !["Completed", "Failed", "Cancelled"].includes(msg.status)) return;

	delete pending_eval_tasks[msg.task_id];

	if (msg.status === "Completed") {
		fetch_and_show_result(cycle, msg.task_id);
		if (cur_frm && cur_frm.doctype === "Evaluation Cycles" && cur_frm.doc.name === cycle) {
			cur_frm.reload_doc();
		}
	} else if (msg.status === "Failed") {
		frappe.msgprint({
			title: __("Creating evaluations failed"),
			indicator: "red",
			message: __("The task stopped with an error. Open {0} to see the details.", [
				`<a href="/app/background-task?task_id=${encodeURIComponent(msg.task_id)}">${__("Background Task")}</a>`,
			]),
		});
	}
}

frappe.ui.form.on("Evaluation Cycles", {
	onload() {
		frappe.realtime.off("task_update", on_eval_task_update);
		frappe.realtime.on("task_update", on_eval_task_update);
	},

	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Create Evaluations"), () => {
			frappe
				.call({
					method: EVAL_METHODS.create,
					args: { cycle: frm.doc.name },
					freeze: true,
					freeze_message: __("Starting..."),
				})
				.then((r) => {
					const res = r.message || {};
					if (!res.task_id) return;
					pending_eval_tasks[res.task_id] = frm.doc.name;
					frappe.show_alert({
						message: __("Started. You can keep working, the result will show up when it's done."),
						indicator: "blue",
					});
				});
		});

		frm.add_custom_button(
			__("Last Result"),
			() => fetch_and_show_result(frm.doc.name),
			__("Evaluations")
		);
	},
});

function fetch_and_show_result(cycle, task_id) {
	frappe
		.call({ method: EVAL_METHODS.result, args: { cycle, task_id: task_id || null } })
		.then((r) => {
			const task = r.message;
			if (!task || !task.result) {
				frappe.msgprint(__("No completed run found for this cycle yet."));
				return;
			}
			show_evaluations_report(cycle, task.result, task.ended_at);
		});
}

// ----------------------------------------------------------------------
// Report dialog (failures first)
// ----------------------------------------------------------------------
function show_evaluations_report(cycle, report, ended_at) {
	const c = (report && report.competencies) || {};
	const created = c.created_list || [];
	const skipped = c.skipped_list || [];
	const failed = c.failed_list || [];
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	const d = new frappe.ui.Dialog({
		title: __("Evaluations Result"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
	});

	const when = ended_at
		? `<div class="text-muted small" style="margin-bottom:8px">${__("Finished")} ${frappe.datetime.comment_when(ended_at)}</div>`
		: "";

	d.fields_dict.body.$wrapper.html(`
		${when}
		<p style="font-size:14px;margin-bottom:12px">
			${summary_sentence(created.length, skipped.length, failed.length)}
		</p>
		${failed.length ? failures_html(failed, esc) : ""}
		<div class="eval-all" style="display:none;margin-top:16px">${all_rows_table(created, skipped, failed, esc)}</div>
		<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
			${failed.length ? `<button class="btn btn-default btn-sm" data-action="errors">${__("Open Error Log")}</button>` : ""}
			<button class="btn btn-default btn-sm" data-action="csv">${__("Download CSV")}</button>
			<button class="btn btn-default btn-sm" data-action="all">${__("View All")}</button>
		</div>
	`);

	const $w = d.fields_dict.body.$wrapper;

	$w.find('[data-action="errors"]').on("click", () => {
		d.hide();
		frappe.set_route("List", "Error Log", {
			reference_doctype: "Evaluation Cycles",
			reference_name: cycle,
		});
	});

	$w.find('[data-action="csv"]').on("click", () => {
		if (report.csv_url) {
			window.open(report.csv_url, "_blank");
		} else {
			download_csv(cycle, created, skipped, failed);
		}
	});

	$w.find('[data-action="all"]').on("click", function () {
		const $all = $w.find(".eval-all");
		const open = $all.is(":visible");
		$all.toggle(!open);
		$(this).text(open ? __("View All") : __("Hide Details"));
	});

	d.show();
}

function summary_sentence(created, skipped, failed) {
	const parts = [];
	if (created) parts.push(__("{0} evaluations created", [created]));
	if (skipped) parts.push(__("{0} already existed", [skipped]));

	let text = parts.length ? parts.join(__(" and ")) + "." : __("Nothing was created.");
	if (failed) {
		text += ` <span class="text-danger">${__("{0} need your attention.", [failed])}</span>`;
	} else {
		text += ` <span class="text-success">${__("Everything went fine.")}</span>`;
	}
	return text;
}

function failures_html(failed, esc) {
	const items = failed
		.map((f) => {
			const who = f.evaluator_id
				? `${esc(f.emp_id)} / ${esc(f.evaluator_id)} (${esc(f.category || "-")})`
				: esc(f.label);
			return `
				<div style="padding:8px 0;border-bottom:1px solid var(--red-100)">
					<div style="font-weight:500">${who}</div>
					<div style="font-size:12px">${esc(f.detail)}</div>
				</div>`;
		})
		.join("");

	return `
		<div style="border:1px solid var(--red-200);background:var(--red-50);color:var(--red-700);
			border-radius:var(--border-radius-md);padding:4px 12px;max-height:280px;overflow-y:auto">
			${items}
		</div>`;
}

function all_rows_table(created, skipped, failed, esc) {
	const pill = { Created: "green", Skipped: "gray", Failed: "red" };
	const rows = [
		...failed.map((r) => ({ ...r, status: "Failed" })),
		...skipped.map((r) => ({ ...r, status: "Skipped" })),
		...created.map((r) => ({ ...r, status: "Created" })),
	];

	const body = rows
		.map((r) => {
			const detail =
				r.status === "Created" && r.detail
					? `<a href="/app/competencies/${encodeURIComponent(r.detail)}">${esc(r.detail)}</a>`
					: esc(r.detail);
			return `
				<tr>
					<td>${esc(r.emp_id || r.label)}</td>
					<td>${esc(r.evaluator_id || "-")}</td>
					<td>${esc(r.category || "-")}</td>
					<td><span class="indicator-pill ${pill[r.status]}">${__(r.status)}</span></td>
					<td class="text-muted">${detail}</td>
				</tr>`;
		})
		.join("");

	return `
		<div style="max-height:360px;overflow-y:auto">
			<table class="table table-bordered table-sm" style="margin:0">
				<thead><tr>
					<th>${__("Employee")}</th><th>${__("Evaluator")}</th><th>${__("Category")}</th>
					<th>${__("Status")}</th><th>${__("Detail")}</th>
				</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>`;
}

// احتياطي لو الملف ماتعملش على السيرفر
function download_csv(cycle, created, skipped, failed) {
	const data = [["Employee", "Evaluator", "Category", "Status", "Detail"]];
	const push = (list, status) =>
		list.forEach((r) =>
			data.push([r.emp_id || r.label, r.evaluator_id || "", r.category || "", status, r.detail || ""])
		);
	push(failed, "Failed");
	push(skipped, "Skipped");
	push(created, "Created");

	frappe.tools.downloadify(data, null, `Evaluations - ${cycle}`);
}
