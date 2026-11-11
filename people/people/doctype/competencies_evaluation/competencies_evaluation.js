// Copyright (c) 2026, Mohamed Kheir and contributors
// For license information, please see license.txt

frappe.ui.form.on("Competencies Evaluation", {
	refresh(frm) {
		paint_competency_issues(frm);
		watch_competency_grid(frm);
	},
	validate(frm) {
		let blocked = paint_competency_issues(frm);
		if (check_competency_memory(frm)) blocked = true;
		if (blocked) frappe.validated = false;
	},
});

function paint_cell_red(cell) {
	cell.css("background-color", "#ffe7e7");
	cell.css("color", "#b41d1d");
	cell.find("a").css("color", "#b41d1d");
	cell.find(".link-btn, .btn-open").css("background-color", "#ffe7e7");
}

function clear_cell_paint(cell) {
	cell.css("background-color", "");
	cell.css("color", "");
	cell.find("a").css("color", "");
	cell.find(".link-btn, .btn-open").css("background-color", "");
}

function competency_weight_bad(rows) {
	const weights = (rows || [])
		.filter((r) => r.weight !== null && r.weight !== undefined)
		.map((r) => flt(r.weight || 0));
	if (!weights.length) return false;
	return Math.abs(Math.round(weights.reduce((a, b) => a + b, 0) * 100) / 100 - 100) > 0.01;
}

function paint_competency_issues(frm) {
	const grid =
		frm.fields_dict.competencies_evaluation_entry &&
		frm.fields_dict.competencies_evaluation_entry.grid;
	if (!grid || !grid.grid_rows || !grid.grid_rows.length) return false;
	const data = (grid.get_data && grid.get_data()) || [];
	const live = new Set(data);
	const counts = {};
	data.forEach((d) => {
		const v = d && d.competency;
		if (v === null || v === undefined || v === "") return;
		counts[v] = (counts[v] || 0) + 1;
	});
	const bad_total = competency_weight_bad(data);
	let blocked = bad_total;
	grid.grid_rows.forEach((r) => {
		if (!r.doc || !live.has(r.doc)) return;
		const competency_cell = r.wrapper.find('[data-fieldname="competency"]');
		const wcell = r.wrapper.find('[data-fieldname="weight"]');
		clear_cell_paint(competency_cell);
		clear_cell_paint(wcell);
		const v = r.doc.competency;
		if (v !== null && v !== undefined && v !== "" && (counts[v] || 0) > 1) {
			paint_cell_red(competency_cell);
			blocked = true;
		}
		if (bad_total) {
			paint_cell_red(wcell);
			blocked = true;
		}
	});
	return blocked;
}

function check_competency_memory(frm) {
	const rows = frm.doc.competencies_evaluation_entry || [];
	const seen = {};
	let blocked = false;
	rows.forEach((d) => {
		const v = d && d.competency;
		if (v === null || v === undefined || v === "") return;
		if (seen[v]) blocked = true;
		seen[v] = true;
	});
	if (competency_weight_bad(rows)) blocked = true;
	return blocked;
}

function watch_competency_grid(frm) {
	const control = frm.fields_dict.competencies_evaluation_entry;
	const target = control && control.grid && control.grid.wrapper.find(".rows")[0];
	if (!target || target._dupe_observer) return;
	let scheduled = false;
	const observer = new MutationObserver(() => {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			paint_competency_issues(frm);
		});
	});
	observer.observe(target, { childList: true, subtree: true, characterData: true });
	target._dupe_observer = observer;
	if (control.grid.wrapper && !control.grid.wrapper[0]._dupe_click) {
		control.grid.wrapper[0]._dupe_click = true;
		control.grid.wrapper.on("focusin", () => paint_competency_issues(frm));
	}
}
