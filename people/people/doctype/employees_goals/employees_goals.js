frappe.ui.form.on("Employees Goals", {
	refresh(frm) {
		paint_goal_issues(frm);
		watch_goal_grid(frm);
		hydrate_kpis(frm);
		watch_kpis_buttons(frm);
	},
	before_save(frm) {
		paint_goal_issues(frm);
		hydrate_kpis(frm);
	},
	validate(frm) {
		let blocked = paint_goal_issues(frm);
		if (check_kpis_memory(frm)) blocked = true;
		if (blocked) frappe.validated = false;
	},
});

frappe.ui.form.on("Goals Evaluation Entry", {
	goal(frm, cdt, cdn) {
		setTimeout(() => paint_goal_issues(frm), 100);
		autofill_kpis_from_goal(frm, cdt, cdn);
	},
	weight(frm) {
		setTimeout(() => paint_goal_issues(frm), 100);
	},
	goals_evaluation_entry_add(frm) {
		setTimeout(() => paint_goal_issues(frm), 50);
	},
	goals_evaluation_entry_delete(frm) {
		setTimeout(() => paint_goal_issues(frm), 50);
	},
	goals_evaluation_entry_remove(frm) {
		setTimeout(() => paint_goal_issues(frm), 50);
	},
	kpis(frm, cdt, cdn) {
		open_kpis_dialog(frm, cdt, cdn);
	},
});

const KPIS_NESTED = {
	table_field: "kpis_evaluation_entry",
	child_doctype: "KPIs Evaluation Entry",
	onload_key: "kpis",
	parents: ["goals_evaluation_entry"],
};

function hydrate_kpis(frm) {
	const cache = (frm.doc.__onload && frm.doc.__onload.kpis) || {};
	(frm.doc.goals_evaluation_entry || []).forEach((row) => {
		if (
			(!row.kpis_evaluation_entry || !row.kpis_evaluation_entry.length) &&
			(cache[row.name] || []).length
		) {
			row.kpis_evaluation_entry = cache[row.name].map((r) => ({
				...r,
				doctype: "KPIs Evaluation Entry",
			}));
		}
	});
}

function kpis_check_fields() {
	const skip = ["Section Break", "Column Break", "Tab Break", "Button", "Heading", "HTML"];
	const fields = [];
	try {
		const dfs = frappe.meta.get_docfields("KPIs Evaluation Entry") || [];
		const first = dfs.find((df) => df && !skip.includes(df.fieldtype) && df.in_list_view);
		if (first) fields.push(first.fieldname);
	} catch (e) {}
	return fields;
}

function check_kpis_memory(frm) {
	const fns = kpis_check_fields();
	if (!fns.length) return false;
	let blocked = false;
	const check_rows = (rows) => {
		const seen = {};
		(rows || []).forEach((d) => {
			fns.forEach((fn) => {
				const v = d && d[fn];
				if (v === null || v === undefined || v === "") return;
				const k = fn + "|" + v;
				if (seen[k]) {
					blocked = true;
					return;
				}
				seen[k] = true;
			});
		});
		const vals = (rows || [])
			.filter((r) => r.weight !== null && r.weight !== undefined)
			.map((r) => flt(r.weight || 0));
		if (vals.length && Math.abs(Math.round(vals.reduce((a, b) => a + b, 0) * 100) / 100 - 100) > 0.01) {
			blocked = true;
		}
	};
	(frm.doc.goals_evaluation_entry || []).forEach((row) => {
		check_rows(row.kpis_evaluation_entry);
	});
	return blocked;
}

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

function paint_goal_issues(frm) {
	const grid = frm.fields_dict.goals_evaluation_entry && frm.fields_dict.goals_evaluation_entry.grid;
	if (!grid || !grid.grid_rows || !grid.grid_rows.length) return false;
	const data = (grid.get_data && grid.get_data()) || [];
	const live = new Set(data);
	const counts = {};
	data.forEach((d) => {
		const v = d && d.goal;
		if (v === null || v === undefined || v === "") return;
		counts[v] = (counts[v] || 0) + 1;
	});
	const weights = data
		.filter((d) => d && d.weight !== null && d.weight !== undefined)
		.map((d) => flt(d.weight || 0));
	const bad_total = weights.length
		? Math.abs(Math.round(weights.reduce((a, b) => a + b, 0) * 100) / 100 - 100) > 0.01
		: false;
	let blocked = bad_total;
	grid.grid_rows.forEach((r) => {
		if (!r.doc || !live.has(r.doc)) return;
		const goal_cell = r.wrapper.find('[data-fieldname="goal"]');
		const wcell = r.wrapper.find('[data-fieldname="weight"]');
		clear_cell_paint(goal_cell);
		clear_cell_paint(wcell);
		const v = r.doc.goal;
		if (v !== null && v !== undefined && v !== "" && (counts[v] || 0) > 1) {
			paint_cell_red(goal_cell);
			blocked = true;
		}
		if (bad_total) {
			paint_cell_red(wcell);
			blocked = true;
		}
	});
	return blocked;
}

function watch_goal_grid(frm) {
	const control = frm.fields_dict.goals_evaluation_entry;
	const target = control && control.grid && control.grid.wrapper.find(".rows")[0];
	if (!target || target._dupe_observer) return;
	let scheduled = false;
	const observer = new MutationObserver(() => {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			paint_goal_issues(frm);
		});
	});
	observer.observe(target, { childList: true, subtree: true, characterData: true });
	target._dupe_observer = observer;
	if (control.grid.wrapper && !control.grid.wrapper[0]._dupe_click) {
		control.grid.wrapper[0]._dupe_click = true;
		control.grid.wrapper.on("focusin", () => paint_goal_issues(frm));
	}
}

function kpis_row_score(r) {
	const planned = flt(r.planned);
	const achieved = flt(r.achived);
	const weight = flt(r.weight);
	if (!planned || !weight) return 0;
	if (r.reverse_calc && !achieved) return flt(weight, 2);
	if (r.reverse_calc) return achieved ? flt(planned / achieved * weight, 2) : 0;
	return flt(achieved / planned * weight, 2);
}

function watch_kpis_buttons(frm) {
	sweep_kpis_buttons(frm);
	if (frm.wrapper._kpis_buttons_bound) return;
	frm.wrapper._kpis_buttons_bound = true;
	$(frm.wrapper).on("grid-row-render", (e, grid_row) => {
		if (frm.doc.docstatus !== 1) return;
		inject_kpis_button(frm, grid_row);
	});
	setTimeout(() => sweep_kpis_buttons(frm), 500);
}

function sweep_kpis_buttons(frm) {
	if (frm.doc.docstatus !== 1) return;
	const grid = frm.fields_dict.goals_evaluation_entry && frm.fields_dict.goals_evaluation_entry.grid;
	(grid && grid.grid_rows || []).forEach((grid_row) =>
		inject_kpis_button(frm, grid_row)
	);
}

function inject_kpis_button(frm, grid_row) {
	if (!grid_row || !grid_row.doc || grid_row.doc.doctype !== "Goals Evaluation Entry") return;
	const cell = grid_row.wrapper.find('[data-fieldname="kpis"]');
	if (!cell.length || cell.find("button").length) return;
	const df = frappe.meta.get_docfield("Goals Evaluation Entry", "kpis") || {};
	const btn = $(`<button class="btn btn-xs btn-default">${__(df.label || "KPIs")}</button>`);
	btn.on("click", (e) => {
		e.stopPropagation();
		frm.script_manager.trigger("kpis", grid_row.doc.doctype, grid_row.doc.name);
	});
	cell.append(btn);
}

function fetch_mapped_kpis(goal) {
	if (!goal) return Promise.resolve([]);
	return frappe
		.call({
			method: "people.people.doctype.employees_goals.employees_goals.get_kpis_for_goal",
			args: { goal: goal },
		})
		.then((r) => (r && r.message) || [])
		.catch(() => []);
}

function autofill_kpis_from_goal(frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row) return;
	if (!row.goal) {
		if ((row.kpis_evaluation_entry || []).length) {
			row.kpis_evaluation_entry = [];
			row.kpis_num = 0;
			frm.refresh_field("goals_evaluation_entry");
			frm.dirty();
		}
		return;
	}
	const goal = row.goal;
	fetch_mapped_kpis(goal).then((mapped) => {
		const current = locals[cdt] && locals[cdt][cdn];
		if (!current || current.goal !== goal) return;
		current.kpis_evaluation_entry = mapped.map((r) => ({
			...r,
			doctype: "KPIs Evaluation Entry",
		}));
		current.kpis_num = current.kpis_evaluation_entry.length;
		if (current.name) {
			frm.doc.__onload = frm.doc.__onload || {};
			frm.doc.__onload.kpis = frm.doc.__onload.kpis || {};
			frm.doc.__onload.kpis[current.name] = current.kpis_evaluation_entry.map((r) => ({
				...r,
			}));
		}
		frm.refresh_field("goals_evaluation_entry");
		frm.dirty();
	});
}

function open_kpis_dialog(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const child_doctype = "KPIs Evaluation Entry";
	const df = frappe.meta.get_docfield("Employees Goals", "goals_evaluation_entry") || {};
	const preview = frm.doc.docstatus === 1 && !df.allow_on_submit;

	const cache = frm.doc.__onload && frm.doc.__onload.kpis;
	const stored = row.kpis_evaluation_entry && row.kpis_evaluation_entry.length
		? row.kpis_evaluation_entry
		: (cache && cache[row.name]) || [];
	if (stored.length) {
		build_kpis_dialog(frm, row, child_doctype, preview, stored);
		return;
	}
	fetch_mapped_kpis(row.goal).then((mapped) => {
		if (mapped.length) {
			row.kpis_evaluation_entry = mapped.map((r) => ({ ...r, doctype: child_doctype }));
			row.kpis_num = row.kpis_evaluation_entry.length;
			frm.refresh_field("goals_evaluation_entry");
			frm.dirty();
		}
		build_kpis_dialog(frm, row, child_doctype, preview, row.kpis_evaluation_entry || []);
	});
}

function build_kpis_dialog(frm, row, child_doctype, preview, stored) {
	frappe.model.with_doctype(child_doctype, () => {
		const fields = frappe.meta
			.get_docfields(child_doctype)
			.filter((df) => !frappe.model.layout_fields.includes(df.fieldtype))
			.map((df) => ({ ...df }));

		const data = stored.map((r) => ({ ...r }));
		const title = row.goal ? `${row.goal} - KPIs` : __("KPIs");

		const paint_dialog_grid = (grid) => {
			if (!grid || !grid.grid_rows || !grid.grid_rows.length) return false;
			const fns = kpis_check_fields();
			if (!fns.length) return false;
			const gdata = (grid.get_data && grid.get_data()) || [];
			const live = new Set(gdata);
			const counts = {};
			fns.forEach((fn) => {
				counts[fn] = {};
			});
			gdata.forEach((d) => {
				fns.forEach((fn) => {
					const v = d && d[fn];
					if (v === null || v === undefined || v === "") return;
					counts[fn][v] = (counts[fn][v] || 0) + 1;
				});
			});
			const weights = gdata
				.filter((d) => d && d.weight !== null && d.weight !== undefined)
				.map((d) => flt(d.weight || 0));
			const bad_total = weights.length
				? Math.abs(Math.round(weights.reduce((a, b) => a + b, 0) * 100) / 100 - 100) > 0.01
				: false;
			let dup = bad_total;
			grid.grid_rows.forEach((r) => {
				if (!r.doc || !live.has(r.doc)) return;
				fns.forEach((fn) => {
					const v = r.doc[fn];
					const cell = r.wrapper.find(`[data-fieldname="${fn}"]`);
					cell.css("background-color", "");
					cell.css("color", "");
					cell.find("a").css("color", "");
					cell.find(".link-btn, .btn-open").css("background-color", "");
					if (v !== null && v !== undefined && v !== "" && (counts[fn][v] || 0) > 1) {
						cell.css("background-color", "#ffe7e7");
						cell.css("color", "#b41d1d");
						cell.find("a").css("color", "#b41d1d");
						cell.find(".link-btn, .btn-open").css("background-color", "#ffe7e7");
						dup = true;
					}
				});
				const wcell = r.wrapper.find('[data-fieldname="weight"]');
				wcell.css("background-color", "");
				wcell.css("color", "");
				if (bad_total && !fns.includes("weight")) {
					wcell.css("background-color", "#ffe7e7");
					wcell.css("color", "#b41d1d");
					dup = true;
				}
			});
			return dup;
		};

		const dialog = new frappe.ui.Dialog({
			title: title,
			size: "extra-large",
			fields: [
				{
					fieldname: "kpis_evaluation_entry",
					fieldtype: "Table",
					label: __(child_doctype),
					options: child_doctype,
					fields: fields,
					data: data,
					read_only: preview ? 1 : 0,
				},
			],
			primary_action_label: preview ? __("Close") : __("Save"),
			primary_action() {
				if (preview) {
					dialog.hide();
					return;
				}
				if (document.activeElement) document.activeElement.blur();
				const grid = dialog.fields_dict.kpis_evaluation_entry.grid;
				if (paint_dialog_grid(grid)) return;
				const first = kpis_check_fields()[0];
				let rows = (grid && grid.get_data()) || [];
				rows = rows.filter((r) => {
					if (!first) return true;
					const v = r[first];
					return v !== null && v !== undefined && !(typeof v === "string" && !v.trim());
				});
				row.kpis_evaluation_entry = rows.map((r) => ({
					...r,
					doctype: child_doctype,
				}));
				row.kpis_evaluation_entry.forEach((r) => {
					r.score = kpis_row_score(r);
				});
				row.kpis_num = row.kpis_evaluation_entry.length;
				row.kpis_score = flt(
					row.kpis_evaluation_entry.reduce((a, r) => a + flt(r.score || 0), 0),
					2
				);
				if (row.name) {
					frm.doc.__onload = frm.doc.__onload || {};
					frm.doc.__onload.kpis = frm.doc.__onload.kpis || {};
					frm.doc.__onload.kpis[row.name] = row.kpis_evaluation_entry.map((r) => ({ ...r }));
				}
				frm.refresh_field("goals_evaluation_entry");
				frm.dirty();
				dialog.hide();
				frappe.call({
					method: "people.people.doctype.employees_goals.employees_goals.compute_goal_scores",
					args: {
						evaluation_cycle: frm.doc.evaluation_cycle,
						category: frm.doc.category,
						emp_id: frm.doc.emp_id,
						rows: (frm.doc.goals_evaluation_entry || []).map((g) => ({
							kpis_score: g.kpis_score,
							weight: g.weight,
						})),
					},
				}).then((r) => {
					const m = (r && r.message) || {};
					(m.rows || []).forEach((rr, i) => {
						const grow = (frm.doc.goals_evaluation_entry || [])[i];
						if (!grow) return;
						if (rr.factor !== undefined) grow.factor = rr.factor;
						if (rr.score !== undefined) grow.score = rr.score;
					});
					if (m.parent_factor !== undefined) frm.doc.factor = m.parent_factor;
					if (m.parent_score !== undefined) frm.doc.score = m.parent_score;
					frm.refresh_field("goals_evaluation_entry");
					frm.refresh_field("factor");
					frm.refresh_field("score");
					frm.dirty();
				});
			},
		});

		const last_link = new WeakMap();
		const fetch_linked_values = () => {
			const grid = dialog.fields_dict.kpis_evaluation_entry.grid;
			if (!grid) return;
			let fields = [];
			try {
				fields = frappe.meta.get_docfields(child_doctype) || [];
			} catch (e) {}
			const links = {};
			fields.forEach((df) => {
				if (df && df.fetch_from && df.fetch_from.includes(".")) {
					const parts = df.fetch_from.split(".");
					(links[parts[0]] = links[parts[0]] || []).push({
						target: df.fieldname,
						source: parts.slice(1).join("."),
					});
				}
			});
			const link_doctype = (ln) => {
				const ldf = fields.find((df) => df && df.fieldname === ln);
				return ldf && ldf.options;
			};
			(grid.get_data() || []).forEach((d) => {
				Object.entries(links).forEach(([lnk, targets]) => {
					const current = d[lnk] || null;
					const prev = last_link.has(d) ? last_link.get(d) : "unseen";
					if (current !== prev) {
						let cleared = false;
						targets.forEach((x) => {
							if (d[x.target] !== null && d[x.target] !== undefined && d[x.target] !== "") {
								d[x.target] = null;
								cleared = true;
							}
						});
						last_link.set(d, current);
						if (cleared) grid.refresh();
					}
					if (!current) return;
					if (targets.every((x) => d[x.target] !== null && d[x.target] !== undefined && d[x.target] !== "")) return;
					const ldt = link_doctype(lnk);
					if (!ldt) return;
					frappe.db
						.get_value(ldt, current, targets.map((x) => x.source))
						.then((r) => {
							if ((d[lnk] || null) !== current) return;
							const m = (r && r.message) || {};
							let changed = false;
							targets.forEach((x) => {
								if (m[x.source] !== undefined && d[x.target] !== m[x.source]) {
									d[x.target] = m[x.source];
									changed = true;
								}
							});
							if (changed) grid.refresh();
						});
				});
			});
		};

		dialog.$wrapper.modal({ backdrop: "static", keyboard: false });
		dialog.show();
		const paint_open = () => {
			const control = dialog.fields_dict.kpis_evaluation_entry;
			if (control) {
				control.$wrapper.find("label.control-label").hide();
				if (control.grid) paint_dialog_grid(control.grid);
			}
		};
		paint_open();
		const control = dialog.fields_dict.kpis_evaluation_entry;
		const target = control && control.grid && control.grid.wrapper.find(".rows")[0];
		if (target && !target._dupe_observer) {
			let scheduled = false;
			const observer = new MutationObserver(() => {
				if (scheduled) return;
				scheduled = true;
				requestAnimationFrame(() => {
					scheduled = false;
		paint_open();
		fetch_linked_values();
		let fetch_scheduled = false;
		const schedule_fetch = () => {
			if (fetch_scheduled) return;
			fetch_scheduled = true;
			setTimeout(() => {
				fetch_scheduled = false;
				fetch_linked_values();
			}, 400);
		};
		dialog.$wrapper.on("change", schedule_fetch);
		dialog.$wrapper.on("awesomplete-selectcomplete", schedule_fetch);
				});
			});
			observer.observe(target, { childList: true, subtree: true, characterData: true });
			target._dupe_observer = observer;
			if (control.grid.wrapper && !control.grid.wrapper[0]._dupe_click) {
				control.grid.wrapper[0]._dupe_click = true;
				control.grid.wrapper.on("focusin", paint_open);
			}
		}
	});
}
