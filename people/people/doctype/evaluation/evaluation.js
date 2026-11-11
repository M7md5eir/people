// Copyright (c) 2026, Mohamed Kheir and contributors
// For license information, please see license.txt

frappe.ui.form.on("Evaluation", {
	refresh(frm) {
		limit_collection_categories(frm);
		refill_collection_rows(frm);
	},
	evaluation_cycle(frm) {
		clear_collection_rows(frm);
		limit_collection_categories(frm);
		refill_collection_rows(frm);
	},
	emp_id(frm) {
		clear_collection_rows(frm);
		limit_collection_categories(frm);
		refill_collection_rows(frm);
	},
});

frappe.ui.form.on("Competencies Collection", {
	competencies_collection_add(frm) {
		limit_collection_categories(frm);
	},
	details(frm, cdt, cdn) {
		open_collection_details(frm, cdt, cdn);
	},
});

function clear_collection_rows(frm) {
	if ((frm.doc.competencies_collection || []).length) {
		frm.doc.competencies_collection = [];
		frm.refresh_field("competencies_collection");
		frm.dirty();
	}
}

function open_collection_details(frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row) return;
	const title = row.category
		? `${row.category} - ${__("Details")}`
		: __("Details");
	const columns = ["name", "evl_id", "evl_name", "evl_position", "evl_job", "docstatus", "factor", "score", "details_btn"];
	const widths = {
		name: 150,
		evl_id: 110,
		evl_name: 160,
		evl_position: 140,
		evl_job: 140,
		docstatus: 90,
		factor: 80,
		score: 80,
		details_btn: 90,
	};
	const labels = {
		name: "ID",
		evl_id: "Evaluator ID",
		evl_name: "Evaluator Name",
		evl_position: "Position",
		evl_job: "Job",
		docstatus: "Status",
		factor: "Factor",
		score: "Score",
		details_btn: "Details",
	};
	frappe.model.with_doctype("Competencies Evaluation", () => {
		const dialog_fields = columns.map((fieldname) => ({
			label: labels[fieldname] || fieldname,
			fieldname: fieldname,
			fieldtype: fieldname === "name" ? "Link" : "Data",
			options: fieldname === "name" ? "Competencies Evaluation" : undefined,
			read_only: 1,
			in_list_view: 1,
			width: widths[fieldname] || 120,
		}));
		frappe.db
			.get_list("Competencies Evaluation", {
				filters: {
					evaluation_cycle: frm.doc.evaluation_cycle,
					emp_id: frm.doc.emp_id,
					category: row.category,
				},
				fields: columns.filter((c) => c !== "details_btn"),
				order_by: "evl_id",
				limit_page_length: 500,
			})
			.catch((e) => {
				frappe.msgprint({
					title: __("Details"),
					message: __("Could not load details: {0}", [
						(e && e.message) || e,
					]),
					indicator: "red",
				});
				return [];
			})
			.then((rows) => {
				const status_text = (s) =>
					s === 1 ? __("Submitted") : s === 2 ? __("Cancelled") : __("Draft");
				const data = (rows || []).map((r) => ({ ...r, docstatus: status_text(r.docstatus) }));
				const dialog = new frappe.ui.Dialog({
					title: title,
					size: "extra-large",
					static: 1,
					fields: [
						{
							fieldname: "details_table",
							fieldtype: "Table",
							cannot_add_rows: 1,
							cannot_delete_rows: 1,
							fields: dialog_fields,
							data: data,
							get_data: () => data,
						},
					],
					secondary_action_label: __("Close"),
					secondary_action() {
						dialog.hide();
					},
				});
				dialog.show();
				restack_modals();
				dialog.$wrapper.on("hidden.bs.modal", () => {
					if (!$(".modal.show").length) {
						$(".modal-backdrop").remove();
						$("body").removeClass("modal-open");
					}
				});
				dialog.$wrapper.find(".modal-dialog").css({ width: "1400px", "max-width": "95%" });
				const paint_details_buttons = () => {
					const grid = dialog.fields_dict.details_table && dialog.fields_dict.details_table.grid;
					if (!grid || !grid.grid_rows) return;
					grid.grid_rows.forEach((grid_row) => {
						if (!grid_row.doc) return;
						const cell = grid_row.wrapper.find('[data-fieldname="details_btn"]');
						if (!cell.length || cell.find("button").length) return;
						const btn = $(`<button class="btn btn-xs btn-default">${__("Details")}</button>`);
						btn.on("click", (e) => {
							e.stopPropagation();
							open_evaluator_entries_dialog(dialog, grid_row.doc.name);
						});
						cell.append(btn);
					});
				};
				paint_details_buttons();
				setTimeout(paint_details_buttons, 500);
			});
	});
}

function open_evaluator_entries_dialog(parent_dialog, eval_name) {
	if (!eval_name) return;
	frappe.db
		.get_list("Competencies Evaluation Entry", {
			filters: { parent: eval_name },
			fields: ["competency", "weight", "rating", "factor", "score"],
			order_by: "idx",
			limit_page_length: 500,
		})
		.then((rows) => {
			const data = (rows || []).map((r) => ({ ...r }));
			const entry_dialog = new frappe.ui.Dialog({
				title: __("{0} - Entries", [eval_name]),
				size: "extra-large",
				static: 1,
				fields: [
					{
						fieldname: "entries_table",
						fieldtype: "Table",
						read_only: 1,
						cannot_add_rows: 1,
						cannot_delete_rows: 1,
						fields: [
							{
								label: "Competency",
								fieldname: "competency",
								fieldtype: "Data",
								read_only: 1,
								in_list_view: 1,
								width: 250,
							},
							{
								label: "Weight",
								fieldname: "weight",
								fieldtype: "Percent",
								read_only: 1,
								in_list_view: 1,
								width: 75,
							},
							{
								label: "Rating",
								fieldname: "rating",
								fieldtype: "Rating",
								options: "5",
								read_only: 1,
								in_list_view: 1,
								width: 100,
							},
							{
								label: "Factor",
								fieldname: "factor",
								fieldtype: "Percent",
								read_only: 1,
								in_list_view: 1,
								width: 75,
							},
							{
								label: "Score",
								fieldname: "score",
								fieldtype: "Percent",
								read_only: 1,
								in_list_view: 1,
								width: 75,
							},
						],
						data: data,
						get_data: () => data,
					},
				],
				secondary_action_label: __("Close"),
				secondary_action() {
					entry_dialog.hide();
				},
			});
			entry_dialog.show();
			restack_modals();
			entry_dialog.$wrapper.on("hidden.bs.modal", () => {
				if (!$(".modal.show").length) {
					$(".modal-backdrop").remove();
					$("body").removeClass("modal-open");
				}
			});
			entry_dialog.$wrapper.find(".modal-dialog").css({ width: "1400px", "max-width": "95%" });
		});
}

function restack_modals() {
	$(".modal.show").each(function (i) {
		$(this).css("z-index", 1050 + i * 20);
	});
	$(".modal-backdrop.show").each(function (i) {
		$(this).css("z-index", 1040 + i * 20);
	});
}

function get_related_categories(cycle, emp_id) {
	if (!cycle || !emp_id) return Promise.resolve([]);
	return frappe.db
		.get_value("Evaluations Mapping", {
			parent: cycle,
			emp_id: emp_id,
		}, "evaluation_form")
		.then((r) => {
			const m = r && r.message;
			return (m && typeof m === "object" ? m.evaluation_form : m) || "";
		})
		.then((form) => {
			if (!form) return [];
			return frappe.db.get_list("Competencies Distribution", {
				filters: { parent: form },
				fields: ["category", "weight"],
				order_by: "idx",
				limit_page_length: 100,
			});
		})
		.then((rows) => {
			const seen = [];
			(rows || []).forEach((r) => {
				if (r.category && !seen.some((s) => s.category === r.category)) {
					seen.push({ category: r.category, weight: r.weight });
				}
			});
			return seen;
		})
		.catch(() => []);
}

function refill_collection_rows(frm) {
	if (!frm.doc.evaluation_cycle || !frm.doc.emp_id) return;
	if ((frm.doc.competencies_collection || []).length) return;
	const cycle = frm.doc.evaluation_cycle;
	const emp_id = frm.doc.emp_id;
	get_related_categories(cycle, emp_id).then((categories) => {
		if (!categories.length) return;
		if (frm.doc.evaluation_cycle !== cycle || frm.doc.emp_id !== emp_id) return;
		if ((frm.doc.competencies_collection || []).length) return;
		frm.doc.competencies_collection = categories.map((r) => ({
			doctype: "Competencies Collection",
			category: r.category,
			weight: r.weight,
		}));
		frm.refresh_field("competencies_collection");
		frm.dirty();
	});
}

function limit_collection_categories(frm) {
	const grid = frm.fields_dict.competencies_collection && frm.fields_dict.competencies_collection.grid;
	if (!grid) return;
	if (!frm.doc.evaluation_cycle || !frm.doc.emp_id) {
		clear_collection_rows(frm);
		return;
	}
	get_related_categories(frm.doc.evaluation_cycle, frm.doc.emp_id).then((items) => {
		const categories = (items || []).map((r) => r.category).filter(Boolean);
		if (!categories.length) return;
		grid.update_docfield_property("category", "options", categories.join("\n"));
		grid.refresh();
	});
}
