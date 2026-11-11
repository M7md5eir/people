frappe.ui.form.on("Evaluations Forms", {
	refresh(frm) {
		hydrate_nested_tables(frm);
		mark_duplicate_first_column(frm);
		watch_grids_for_duplicates(frm);
		watch_row_buttons(frm);
	},
	before_save(frm) {
		hydrate_nested_tables(frm);
	},
	validate(frm) {
		let blocked = mark_duplicate_first_column(frm);
		if (check_memory_duplicates(frm)) blocked = true;
		if (check_weight_totals(frm)) blocked = true;
		if (paint_weight_split(frm)) blocked = true;
		if (blocked) frappe.validated = false;
	},
	goals_weight(frm) {
		paint_weight_split(frm);
	},
	competencies_weight(frm) {
		paint_weight_split(frm);
	},
});

function paint_weight_split(frm) {
	const gw = frm.doc.goals_weight;
	const cw = frm.doc.competencies_weight;
	const bad =
		(gw !== null && gw !== undefined) ||
		(cw !== null && cw !== undefined)
			? Math.abs(Math.round((flt(gw || 0) + flt(cw || 0)) * 100) / 100 - 100) > 0.01
			: false;
	["goals_weight", "competencies_weight"].forEach((fn) => {
		const control = frm.fields_dict[fn];
		if (!control) return;
		const input = control.$wrapper.find("input");
		input.css("background-color", bad ? "#ffe7e7" : "");
		input.css("color", bad ? "#b41d1d" : "");
	});
	return bad;
}

function first_grid_column(cdt) {
	const skip = ["Section Break", "Column Break", "Tab Break", "Button", "Heading", "HTML"];
	let dfs = [];
	try {
		dfs = frappe.meta.get_docfields(cdt) || [];
	} catch (e) {}
	return dfs.find((df) => df && !skip.includes(df.fieldtype) && df.in_list_view) || null;
}

function dup_check_fields(child_doctype) {
	const fields = [];
	const first = first_grid_column(child_doctype);
	if (first) fields.push(first.fieldname);
	let dfs = [];
	try {
		dfs = frappe.meta.get_docfields(child_doctype) || [];
	} catch (e) {}
	if (
		dfs.some((d) => d && d.fieldname === "score") &&
		(!first || first.fieldname !== "score")
	) {
		fields.push("score");
	}
	return fields;
}

function count_field_dupes(rows, fields) {
	const counts = {};
	fields.forEach((fn) => {
		counts[fn] = {};
	});
	(rows || []).forEach((d) => {
		fields.forEach((fn) => {
			const v = d && d[fn];
			if (v === null || v === undefined || v === "") return;
			counts[fn][v] = (counts[fn][v] || 0) + 1;
		});
	});
	return counts;
}

function counts_have_dupes(counts) {
	return Object.values(counts).some((m) =>
		Object.values(m).some((n) => n > 1)
	);
}

function paint_grid_duplicates(grid, counts_map) {
	if (!grid || !grid.grid_rows || !grid.grid_rows.length) return false;
	const fields = dup_check_fields(grid.doctype);
	if (!fields.length) return false;
	const data = (grid.get_data && grid.get_data()) || [];
	const live = new Set(data);
	const counts = counts_map || count_field_dupes(data, fields);
	let duplicated = false;
	const weights = data
		.filter((d) => d && d.weight !== null && d.weight !== undefined)
		.map((d) => flt(d.weight || 0));
	const bad_total = weights.length
		? Math.abs(Math.round(weights.reduce((a, b) => a + b, 0) * 100) / 100 - 100) > 0.01
		: false;
	grid.grid_rows.forEach((r) => {
		if (!r.doc || !live.has(r.doc)) return;
		fields.forEach((fn) => {
			const v = r.doc[fn];
			const cell = r.wrapper.find(`[data-fieldname="${fn}"]`);
			cell.css("background-color", "");
			cell.css("color", "");
			cell.find("a").css("color", "");
			cell.find(".link-btn, .btn-open").css("background-color", "");
			if (v !== null && v !== undefined && v !== "" && ((counts[fn] || {})[v] || 0) > 1) {
				cell.css("background-color", "#ffe7e7");
				cell.css("color", "#b41d1d");
				cell.find("a").css("color", "#b41d1d");
				cell.find(".link-btn, .btn-open").css("background-color", "#ffe7e7");
				duplicated = true;
			}
		});
		const wcell = r.wrapper.find('[data-fieldname="weight"]');
		wcell.css("background-color", "");
		wcell.css("color", "");
		wcell.find("a").css("color", "");
		if (bad_total && !fields.includes("weight")) {
			wcell.css("background-color", "#ffe7e7");
			wcell.css("color", "#b41d1d");
			wcell.find("a").css("color", "#b41d1d");
			duplicated = true;
		}
	});
	return duplicated;
}

function check_memory_duplicates(frm) {
	let duplicated = false;
	NESTED_TABLES.forEach((cfg) => {
		cfg.parents.forEach((parent_table) => {
			(frm.doc[parent_table] || []).forEach((row) => {
				if (counts_have_dupes(count_field_dupes(row[cfg.table_field], dup_check_fields(cfg.child_doctype)))) {
					duplicated = true;
				}
			});
		});
	});
	return duplicated;
}

function check_weight_totals(frm) {
	let blocked = false;
	const check_rows = (rows) => {
		const vals = (rows || [])
			.filter((r) => r.weight !== null && r.weight !== undefined)
			.map((r) => flt(r.weight || 0));
		if (!vals.length) return;
		const total = Math.round(vals.reduce((a, b) => a + b, 0) * 100) / 100;
		if (Math.abs(total - 100) > 0.01) blocked = true;
	};
	["goals_distribution", "competencies_distribution", "evaluations_rates"].forEach((table) => {
		check_rows(frm.doc[table]);
	});
	NESTED_TABLES.forEach((cfg) => {
		cfg.parents.forEach((parent_table) => {
			(frm.doc[parent_table] || []).forEach((row) => {
				check_rows(row[cfg.table_field]);
			});
		});
	});
	return blocked;
}

function mark_duplicate_first_column(frm) {
	let duplicated = false;
	["goals_distribution", "competencies_distribution", "evaluations_rates"].forEach((table) => {
		const grid = frm.fields_dict[table] && frm.fields_dict[table].grid;
		if (paint_grid_duplicates(grid)) duplicated = true;
	});
	return duplicated;
}

function watch_grids_for_duplicates(frm) {
	["goals_distribution", "competencies_distribution", "evaluations_rates"].forEach((table) => {
		const control = frm.fields_dict[table];
		const target = control && control.grid && control.grid.wrapper.find(".rows")[0];
		if (!target || target._dupe_observer) return;
		let scheduled = false;
		const observer = new MutationObserver(() => {
			if (scheduled) return;
			scheduled = true;
			requestAnimationFrame(() => {
				scheduled = false;
				mark_duplicate_first_column(frm);
			});
		});
		observer.observe(target, { childList: true, subtree: true, characterData: true });
		target._dupe_observer = observer;
		if (control.grid.wrapper && !control.grid.wrapper[0]._dupe_click) {
			control.grid.wrapper[0]._dupe_click = true;
			control.grid.wrapper.on("focusin", () => mark_duplicate_first_column(frm));
		}
	});
}

frappe.ui.form.on("Goals Distribution", {
	calculation(frm, cdt, cdn) {
		open_nested_table_dialog(frm, cdt, cdn, goals_calculation_opts());
	},
	weight_breakdown(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const tables = [];
		const part = (row && row.category) || "";
		if (!part.toLowerCase().includes("organiz")) {
			return;
		}
		tables.push({
			table_field: "goals_parts_breakdowns",
			child_doctype: "Goals Parts Breakdowns",
			onload_key: "parts_breakdowns",
		});
		open_nested_table_dialog(frm, cdt, cdn, {
			tables: tables,
			title_suffix: "Weight Breakdown",
		});
	},
});

frappe.ui.form.on("Competencies Distribution", {
	calculation(frm, cdt, cdn) {
		open_nested_table_dialog(frm, cdt, cdn, competencies_calculation_opts());
	},
	competencies(frm, cdt, cdn) {
		open_nested_table_dialog(frm, cdt, cdn, {
			table_field: "competencies_mapping",
			child_doctype: "Competencies Mapping",
			onload_key: "mappings",
			title_suffix: "Competencies Mapping",
		});
	},
});

const NESTED_TABLES = [
	{
		table_field: "goals_calc_individual",
		child_doctype: "Evaluations Calculations",
		onload_key: "calculations",
		parents: ["goals_distribution"],
	},
	{
		table_field: "competencies_calc_individual",
		child_doctype: "Evaluations Calculations",
		onload_key: "calculations",
		parents: ["competencies_distribution"],
	},
	{
		table_field: "goals_calc",
		child_doctype: "Evaluations Calculations",
		onload_key: "breakdowns",
		parents: ["goals_distribution"],
	},
	{
		table_field: "competencies_calc",
		child_doctype: "Evaluations Calculations",
		onload_key: "competencies_calcs",
		parents: ["competencies_distribution"],
	},
	{
		table_field: "goals_parts_breakdowns",
		child_doctype: "Goals Parts Breakdowns",
		onload_key: "parts_breakdowns",
		parents: ["goals_distribution"],
	},
	{
		table_field: "competencies_mapping",
		child_doctype: "Competencies Mapping",
		onload_key: "mappings",
		parents: ["competencies_distribution"],
	},
];

function hydrate_nested_tables(frm) {
	const cache = frm.doc.__onload || {};
	NESTED_TABLES.forEach((cfg) => {
		const stored = cache[cfg.onload_key] || {};
		cfg.parents.forEach((parent_table) => {
			(frm.doc[parent_table] || []).forEach((row) => {
				if (
					(!row[cfg.table_field] || !row[cfg.table_field].length) &&
					(stored[row.name] || []).length
				) {
					row[cfg.table_field] = stored[row.name].map((r) => ({
						...r,
						doctype: cfg.child_doctype,
					}));
				}
			});
		});
	});
}

function goals_calculation_opts() {
	return {
		table_field: "goals_calc_individual",
		child_doctype: "Evaluations Calculations",
		onload_key: "calculations",
		title_suffix: "Calculation Factors",
		checkbox_field: "overachievement",
		method_field: "calculation_method",
		extra_tables: [
			{
				table_field: "goals_calc",
				child_doctype: "Evaluations Calculations",
				onload_key: "breakdowns",
			},
		],
	};
}

function competencies_calculation_opts() {
	return {
		table_field: "competencies_calc_individual",
		child_doctype: "Evaluations Calculations",
		onload_key: "calculations",
		title_suffix: "Calculation Factors",
		method_field: "calculation_method",
		extra_tables: [
			{
				table_field: "competencies_calc",
				child_doctype: "Evaluations Calculations",
				onload_key: "competencies_calcs",
			},
		],
	};
}

// Frappe hides grid Button controls when the grid is not editable, so the
// row buttons vanish after submit. Inject same-labelled buttons into the
// same cells so one button serves both edit and preview.
const ROW_DIALOG_BUTTONS = {
	"Goals Distribution": ["calculation", "weight_breakdown"],
	"Competencies Distribution": ["calculation", "competencies"],
};

function inject_row_buttons(frm, grid_row) {
	if (!grid_row || !grid_row.doc) return;
	const fields = ROW_DIALOG_BUTTONS[grid_row.doc.doctype];
	if (!fields) return;
	fields.forEach((fieldname) => {
		const cell = grid_row.wrapper.find(`[data-fieldname="${fieldname}"]`);
		if (!cell.length || cell.find("button").length) return;
		const df = frappe.meta.get_docfield(grid_row.doc.doctype, fieldname) || {};
		const btn = $(`<button class="btn btn-xs btn-default">${__(df.label || fieldname)}</button>`);
		btn.on("click", (e) => {
			e.stopPropagation();
			frm.script_manager.trigger(fieldname, grid_row.doc.doctype, grid_row.doc.name);
		});
		cell.append(btn);
	});
}

function sweep_row_buttons(frm) {
	if (frm.doc.docstatus !== 1) return;
	["goals_distribution", "competencies_distribution"].forEach((table) => {
		const grid = frm.fields_dict[table] && frm.fields_dict[table].grid;
		(grid && grid.grid_rows || []).forEach((grid_row) =>
			inject_row_buttons(frm, grid_row)
		);
	});
}

function watch_row_buttons(frm) {
	sweep_row_buttons(frm);
	if (frm.wrapper._row_buttons_bound) return;
	frm.wrapper._row_buttons_bound = true;
	$(frm.wrapper).on("grid-row-render", (e, grid_row) => {
		if (frm.doc.docstatus !== 1) return;
		inject_row_buttons(frm, grid_row);
	});
	setTimeout(() => sweep_row_buttons(frm), 500);
}

function dialog_is_preview(frm, cdt) {
	if (frm.doc.docstatus !== 1) return false;
	const parent_table =
		cdt === "Goals Distribution"
			? "goals_distribution"
			: cdt === "Competencies Distribution"
				? "competencies_distribution"
				: "goals_distribution";
	const df = frappe.meta.get_docfield("Evaluations Forms", parent_table);
	return !(df && df.allow_on_submit);
}

const OPEN_TABLE_DIALOGS = [];

function use_live_row(frm, cdt, cdn) {
	if (locals[cdt] && locals[cdt][cdn]) return locals[cdt][cdn];
	const hit = find_row_in_grids(frm, cdt, cdn);
	if (hit) {
		locals[cdt] = locals[cdt] || {};
		locals[cdt][cdn] = hit;
		return hit;
	}
	const cache = frm.doc.__onload || {};
	for (const key of Object.keys(cache)) {
		for (const rows of Object.values(cache[key] || {})) {
			for (const d of rows || []) {
				if (d && d.name === cdn) {
					locals[cdt] = locals[cdt] || {};
					locals[cdt][cdn] = d;
					return d;
				}
			}
		}
	}
	return null;
}

function find_row_in_grids(frm, cdt, cdn) {
	for (let i = OPEN_TABLE_DIALOGS.length - 1; i >= 0; i--) {
		const entry = OPEN_TABLE_DIALOGS[i];
		for (const t of entry.table_cfgs || []) {
			const grid = entry.dialog.fields_dict[t.table_field] && entry.dialog.fields_dict[t.table_field].grid;
			for (const grid_row of (grid && grid.grid_rows) || []) {
				if (grid_row.doc && grid_row.doc.name === cdn && (!cdt || grid_row.doc.doctype === cdt)) {
					return grid_row.doc;
				}
			}
		}
	}
	for (const control of Object.values(frm.fields_dict || {})) {
		for (const grid_row of (control.grid && control.grid.grid_rows) || []) {
			if (grid_row.doc && grid_row.doc.doctype === cdt && grid_row.doc.name === cdn) {
				return grid_row.doc;
			}
		}
	}
	return null;
}

function restack_modals() {
	$(".modal.show").each(function (i) {
		$(this).css("z-index", 1050 + i * 20);
	});
	$(".modal-backdrop.show").each(function (i) {
		$(this).css("z-index", 1040 + i * 20);
	});
}

function is_blank_dialog_row(t, r) {
	return !(t.dialog_fields || []).some((df) => {
		if (!df || frappe.model.layout_fields.includes(df.fieldtype)) return false;
		if (df.fieldtype === "Table") return (r[df.fieldname] || []).length > 0;
		const v = r[df.fieldname];
		return !(v === null || v === undefined || (typeof v === "string" && !v.trim()));
	});
}

function open_nested_table_dialog(frm, cdt, cdn, opts) {
	const row = use_live_row(frm, cdt, cdn);
	if (!row) return;
	const table_cfgs = opts.tables || [
		{
			table_field: opts.table_field,
			child_doctype: opts.child_doctype,
			onload_key: opts.onload_key,
		},
		...(opts.extra_tables || []),
	];
	const preview = dialog_is_preview(frm, cdt);

	Promise.all(table_cfgs.map((t) => frappe.model.with_doctype(t.child_doctype))).then(() => {
		const cache = frm.doc.__onload || {};
		table_cfgs.forEach((t) => {
			const tfields = frappe.meta
				.get_docfields(t.child_doctype)
				.filter((df) => !frappe.model.layout_fields.includes(df.fieldtype))
				.map((df) => ({ ...df }));
			const tcache = cache[t.onload_key];
			const tstored = row[t.table_field] && row[t.table_field].length
				? row[t.table_field]
				: (tcache && tcache[row.name]) || [];
			t.dialog_fields = tfields;
			t.first_field = tfields.length ? tfields[0].fieldname : null;
			t.data = tstored.map((r) => ({ ...r }));
		});

		const category = row.category || "";
		const title = category ? `${category} - ${opts.title_suffix}` : __(opts.title_suffix);

		const dialog_fields = [];
		if (opts.checkbox_field) {
			const checkbox_df = frappe.meta.get_docfield(cdt, opts.checkbox_field) || {};
			dialog_fields.push({
				fieldname: opts.checkbox_field,
				fieldtype: "Check",
				label: __(checkbox_df.label || opts.checkbox_field),
				description: __(checkbox_df.description || ""),
				default: row[opts.checkbox_field] ? 1 : 0,
				read_only: preview ? 1 : 0,
			});
		}
		if (opts.method_field) {
			const method_df = frappe.meta.get_docfield(cdt, opts.method_field) || {};
			dialog_fields.push({
				fieldname: opts.method_field,
				fieldtype: "Autocomplete",
				label: __(method_df.label || opts.method_field),
				options: (method_df.options || "").split("\n"),
				default: row[opts.method_field] || method_df.default || "",
				placeholder: __(method_df.placeholder || ""),
				description: __(method_df.description || ""),
				read_only: preview ? 1 : 0,
			});
		}
		if (opts.checkbox_field || opts.method_field) {
			dialog_fields.push({ fieldtype: "Column Break" });
		}
		table_cfgs.forEach((t) => {
			dialog_fields.push({
				fieldname: t.table_field,
				fieldtype: "Table",
				label: __(t.child_doctype),
				options: t.child_doctype,
				fields: t.dialog_fields,
				data: t.data,
				read_only: preview ? 1 : 0,
			});
		});

		const dialog = new frappe.ui.Dialog({
			title: title,
			size: "large",
			fields: dialog_fields,
			primary_action_label: preview ? __("Close") : __("Save"),
			primary_action() {
				if (preview) {
					dialog.hide();
					return;
				}
				if (document.activeElement) document.activeElement.blur();
				if (opts.method_field) {
					const method_val = dialog.get_value(opts.method_field);
					const method_control = dialog.fields_dict[opts.method_field];
					const method_input = method_control && method_control.$wrapper.find("input");
					if (!method_val || method_val === "0") {
						if (method_input) {
							method_input.css("background-color", "#ffe7e7");
							method_input.css("color", "#b41d1d");
						}
						return;
					}
					if (method_input) {
						method_input.css("background-color", "");
						method_input.css("color", "");
					}
				}
				if (dialog_has_duplicates()) return;
				if (opts.method_field) {
					row[opts.method_field] = dialog.get_value(opts.method_field) || "";
				}
				if (opts.checkbox_field) {
					row[opts.checkbox_field] = dialog.get_value(opts.checkbox_field) ? 1 : 0;
				}
				table_cfgs.forEach((t) => {
					const grid = dialog.fields_dict[t.table_field].grid;
					const rows = (grid && grid.get_data()) || [];
					row[t.table_field] = rows.filter((r) => !is_blank_dialog_row(t, r)).map((r) => ({
						...r,
						doctype: t.child_doctype,
					}));
					row[t.table_field] = rows.map((r) => ({
						...r,
						doctype: t.child_doctype,
					}));
					if (row.name) {
						frm.doc.__onload = frm.doc.__onload || {};
						frm.doc.__onload[t.onload_key] = frm.doc.__onload[t.onload_key] || {};
						frm.doc.__onload[t.onload_key][row.name] = row[t.table_field].map((r) => ({ ...r }));
					}
				});
				frm.refresh_field(row.parentfield);
				frm.dirty();
				dialog.hide();
			},
		});

		dialog.$wrapper.modal({ backdrop: "static", keyboard: false });
		dialog.show();
		restack_modals();
		dialog.$wrapper.on("shown.bs.modal", () => restack_modals());
		const entry = { dialog: dialog, table_cfgs: table_cfgs };
		OPEN_TABLE_DIALOGS.push(entry);
		dialog.$wrapper.on("hidden.bs.modal", () => {
			const at = OPEN_TABLE_DIALOGS.indexOf(entry);
			if (at !== -1) OPEN_TABLE_DIALOGS.splice(at, 1);
			if (!$(".modal.show").length) {
				$(".modal-backdrop").remove();
				$("body").removeClass("modal-open");
			}
		});
		const dialog_has_duplicates = () => {
			let dup = false;
			table_cfgs.forEach((t) => {
				const grid = dialog.fields_dict[t.table_field] && dialog.fields_dict[t.table_field].grid;
				if (grid && paint_grid_duplicates(grid)) dup = true;
			});
			return dup;
		};
		const paint_open_tables = () => {
			table_cfgs.forEach((t) => {
				const control = dialog.fields_dict[t.table_field];
				if (control) {
					control.$wrapper.find("label.control-label").hide();
					if (control.grid) paint_grid_duplicates(control.grid);
				}
			});
		};
		paint_open_tables();
		table_cfgs.forEach((t) => {
			const control = dialog.fields_dict[t.table_field];
			const target = control && control.grid && control.grid.wrapper.find(".rows")[0];
			if (!target || target._dupe_observer) return;
			let scheduled = false;
			const observer = new MutationObserver(() => {
				if (scheduled) return;
				scheduled = true;
				requestAnimationFrame(() => {
					scheduled = false;
					paint_open_tables();
				});
			});
			observer.observe(target, { childList: true, subtree: true, characterData: true });
			target._dupe_observer = observer;
			if (control.grid.wrapper && !control.grid.wrapper[0]._dupe_click) {
				control.grid.wrapper[0]._dupe_click = true;
				control.grid.wrapper.on("focusin", () => paint_open_tables());
			}
		});
	});
}
