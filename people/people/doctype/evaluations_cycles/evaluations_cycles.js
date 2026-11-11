frappe.ui.form.on("Evaluations Cycles", {
	refresh(frm) {
		mark_mapping_duplicates(frm);
		watch_mapping_grid(frm);
		hydrate_evaluators(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Create Evaluations"), () =>
				create_competencies_evaluations(frm)
			);
		}
	},
	before_save(frm) {
		mark_mapping_duplicates(frm);
		hydrate_evaluators(frm);
	},
	validate(frm) {
		let blocked = mark_mapping_duplicates(frm);
		if (check_evaluators_duplicates(frm)) blocked = true;
		if (blocked) frappe.validated = false;
	},
});

frappe.ui.form.on("Evaluations Mapping", {
	emp_id(frm) {
		setTimeout(() => mark_mapping_duplicates(frm), 100);
	},
	evaluation_form(frm) {
		setTimeout(() => mark_mapping_duplicates(frm), 100);
	},
	evaluations_mapping_add(frm) {
		setTimeout(() => mark_mapping_duplicates(frm), 50);
	},
	evaluations_mapping_delete(frm) {
		setTimeout(() => mark_mapping_duplicates(frm), 50);
	},
	evaluations_mapping_remove(frm) {
		setTimeout(() => mark_mapping_duplicates(frm), 50);
	},
	evaluators(frm, cdt, cdn) {
		open_evaluators_dialog(frm, cdt, cdn);
	},
});

function create_competencies_evaluations(frm) {
	frappe.call({
		method: "people.people.doctype.evaluations_cycles.evaluations_cycles.create_evaluations",
		args: { cycle: frm.doc.name },
		freeze: true,
		freeze_message: __("Creating evaluations..."),
	}).then((r) => {
		const m = (r && r.message) || {};
		const emp = m.goals_employee || {};
		const org = m.goals_org || {};
		const goals_total = {
			created: (emp.created || 0) + (org.created || 0),
			skipped: (emp.skipped || 0) + (org.skipped || 0),
			failed: (emp.failed || 0) + (org.failed || 0),
			failed_list: [...(emp.failed_list || []), ...(org.failed_list || [])],
		};
		const row = (label, d) =>
			`<tr><td>${__(label)}</td><td>${d.created || 0}</td><td>${d.skipped || 0}</td><td>${d.failed || 0}</td><td>${((d.failed_list || []).join(", "))}</td></tr>`;
		frappe.msgprint({
			title: __("Create Evaluations"),
			message: `<table class="table table-borderless table-sm" style="font-weight: normal">
				<thead><tr><th style="font-weight: normal"></th><th style="font-weight: normal">${__("Created")}</th><th style="font-weight: normal">${__("Skipped")}</th><th style="font-weight: normal">${__("Failed")}</th><th style="font-weight: normal">${__("Employees")}</th></tr></thead>
				<tbody>
					${row("Evaluation", m.evaluation || {})}
					${row("Competencies Setup", m.competencies || {})}
					${row("Goals", goals_total)}
					${row("&nbsp;&nbsp;&nbsp;Employee", m.goals_employee || {})}
					${row("&nbsp;&nbsp;&nbsp;Organization", m.goals_org || {})}
				</tbody>
			</table>`,
		});
		if ((m.competencies || {}).created || (m.evaluation || {}).created || goals_total.created) {
			frm.reload_doc();
		}
	});
}

function mapping_pair_key(doc) {
	if (!doc || !doc.emp_id || !doc.evaluation_form) return null;
	return doc.emp_id + "|" + doc.evaluation_form;
}

function mark_mapping_duplicates(frm) {
	const grid = frm.fields_dict.evaluations_mapping && frm.fields_dict.evaluations_mapping.grid;
	if (!grid || !grid.grid_rows || !grid.grid_rows.length) return false;
	const data = (grid.get_data && grid.get_data()) || [];
	const live = new Set(data);
	const counts = {};
	data.forEach((d) => {
		const k = mapping_pair_key(d);
		if (!k) return;
		counts[k] = (counts[k] || 0) + 1;
	});
	let duplicated = false;
	grid.grid_rows.forEach((r) => {
		if (!r.doc || !live.has(r.doc)) return;
		const is_dupe = (counts[mapping_pair_key(r.doc)] || 0) > 1;
		["emp_id", "evaluation_form"].forEach((fn) => {
			const cell = r.wrapper.find(`[data-fieldname="${fn}"]`);
			cell.css("background-color", "");
			cell.css("color", "");
			cell.find("a").css("color", "");
			cell.find(".link-btn, .btn-open").css("background-color", "");
			if (is_dupe) {
				cell.css("background-color", "#ffe7e7");
				cell.css("color", "#b41d1d");
				cell.find("a").css("color", "#b41d1d");
				cell.find(".link-btn, .btn-open").css("background-color", "#ffe7e7");
			}
		});
		if (is_dupe) duplicated = true;
	});
	return duplicated;
}

function watch_mapping_grid(frm) {
	const control = frm.fields_dict.evaluations_mapping;
	const target = control && control.grid && control.grid.wrapper.find(".rows")[0];
	if (!target || target._dupe_observer) return;
	let scheduled = false;
	const observer = new MutationObserver(() => {
		if (scheduled) return;
		scheduled = true;
		requestAnimationFrame(() => {
			scheduled = false;
			mark_mapping_duplicates(frm);
		});
	});
	observer.observe(target, { childList: true, subtree: true, characterData: true });
	target._dupe_observer = observer;
	if (control.grid.wrapper && !control.grid.wrapper[0]._dupe_click) {
		control.grid.wrapper[0]._dupe_click = true;
		control.grid.wrapper.on("focusin", () => mark_mapping_duplicates(frm));
	}
}

const EVALUATORS_TABLE = {
	table_field: "evaluators_mapping",
	child_doctype: "Evaluators Mapping",
	onload_key: "evaluators",
};

function hydrate_evaluators(frm) {
	const cache = (frm.doc.__onload && frm.doc.__onload.evaluators) || {};
	(frm.doc.evaluations_mapping || []).forEach((row) => {
		if (
			(!row.evaluators_mapping || !row.evaluators_mapping.length) &&
			(cache[row.name] || []).length
		) {
			row.evaluators_mapping = cache[row.name].map((r) => ({
				...r,
				doctype: "Evaluators Mapping",
			}));
		}
	});
}

function check_evaluators_duplicates(frm) {
	const df = dup_check_fields_eval("Evaluators Mapping");
	if (!df) return false;
	let duplicated = false;
	(frm.doc.evaluations_mapping || []).forEach((row) => {
		const seen = {};
		(row.evaluators_mapping || []).forEach((d) => {
			const v = d && d[df];
			if (v === null || v === undefined || v === "") return;
			if (seen[v]) {
				duplicated = true;
				return;
			}
			seen[v] = true;
		});
	});
	return duplicated;
}

function dup_check_fields_eval(child_doctype) {
	const skip = ["Section Break", "Column Break", "Tab Break", "Button", "Heading", "HTML"];
	let dfs = [];
	try {
		dfs = frappe.meta.get_docfields(child_doctype) || [];
	} catch (e) {}
	const first = dfs.find((df) => df && !skip.includes(df.fieldtype) && df.in_list_view);
	return first ? first.fieldname : null;
}

function paint_evaluators_grid(grid, counts_override) {
	if (!grid || !grid.grid_rows || !grid.grid_rows.length) return false;
	const fn = dup_check_fields_eval(grid.doctype);
	if (!fn) return false;
	const data = (grid.get_data && grid.get_data()) || [];
	const live = new Set(data);
	let counts = counts_override;
	if (!counts) {
		counts = {};
		data.forEach((d) => {
			const v = d && d[fn];
			if (v !== null && v !== undefined && v !== "") {
				counts[v] = (counts[v] || 0) + 1;
			}
		});
	}
	let duplicated = false;
	grid.grid_rows.forEach((r) => {
		if (!r.doc || !live.has(r.doc)) return;
		const v = r.doc[fn];
		const cell = r.wrapper.find(`[data-fieldname="${fn}"]`);
		cell.css("background-color", "");
		cell.css("color", "");
		cell.find("a").css("color", "");
		cell.find(".link-btn, .btn-open").css("background-color", "");
		if (v !== null && v !== undefined && v !== "" && (counts[v] || 0) > 1) {
			cell.css("background-color", "#ffe7e7");
			cell.css("color", "#b41d1d");
			cell.find("a").css("color", "#b41d1d");
			cell.find(".link-btn, .btn-open").css("background-color", "#ffe7e7");
			duplicated = true;
		}
	});
	return duplicated;
}

function open_evaluators_dialog(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const child_doctype = "Evaluators Mapping";

	if (!row.evaluation_form) {
		return;
	}

	frappe.model.with_doctype(child_doctype, () => {
		const fields = frappe.meta
			.get_docfields(child_doctype)
			.filter((df) => !frappe.model.layout_fields.includes(df.fieldtype))
			.map((df) => ({ ...df }));

		const cache = frm.doc.__onload && frm.doc.__onload.evaluators;
		const stored = row.evaluators_mapping && row.evaluators_mapping.length
			? row.evaluators_mapping
			: (cache && cache[row.name]) || [];

		const load_groups = () => {
			if (!row.evaluation_form) return Promise.resolve([]);
			return frappe.db
				.get_doc("Evaluations Forms", row.evaluation_form)
				.then((form) =>
					((form && form.competencies_distribution) || [])
						.map((r) => r.category)
						.filter(Boolean)
				)
				.catch(() => []);
		};
		const load_emp_name = () => {
			if (!row.emp_id) return Promise.resolve("");
			return frappe.db
				.get_value("Employees", row.emp_id, "preferred_name")
				.then((r) => {
					const m = r && r.message;
					return (m && typeof m === "object" ? m.preferred_name : m) || "";
				})
				.catch(() => "");
		};
		Promise.all([load_groups(), load_emp_name()]).then(([listed_categories, emp_name]) => {
			build_evaluators_dialog(frm, row, child_doctype, fields, stored, listed_categories, emp_name);
		});
	});
}

function build_evaluators_dialog(frm, row, child_doctype, fields, stored, listed, emp_name) {
		const row_cats = [];
		stored.forEach((r) => {
			if (r.category && !listed.includes(r.category) && !row_cats.includes(r.category)) {
				row_cats.push(r.category);
			}
		});
		const groups = [...listed, ...row_cats];
		const fallback_general = !groups.length;
		if (fallback_general) groups.push(__("General"));

		const cat_options = [...listed, ...row_cats];
		if (cat_options.length) {
			fields = fields.map((df) =>
				df.fieldname === "category" ? { ...df, options: cat_options.join("\n") } : df
			);
		}

		const by_category = {};
		groups.forEach((g) => (by_category[g] = []));
		stored.map((r) => ({ ...r })).forEach((r) => {
			const key = by_category[r.category] !== undefined ? r.category : groups[0];
			by_category[key].push(r);
		});

		const dialog_fields = [
			{
				fieldname: "evaluator_tabs",
				fieldtype: "HTML",
			},
		];
		groups.forEach((g, i) => {
			dialog_fields.push({
				fieldname: `evaluators_data_${i}`,
				fieldtype: "Table",
				label: __(child_doctype),
				options: child_doctype,
				fields: fields,
				data: by_category[g] || [],
				get_data: () => by_category[g] || [],
			});
		});

		const paint_open_tables = () => {
			const counts = {};
			groups.forEach((g, i) => {
				const grid = dialog.fields_dict[`evaluators_data_${i}`].grid;
				(grid && grid.get_data() || []).forEach((d) => {
					const v = d && d.evl_id;
					if (v === null || v === undefined || v === "") return;
					counts[v] = (counts[v] || 0) + 1;
				});
			});
			let dup = false;
			groups.forEach((g, i) => {
				const control = dialog.fields_dict[`evaluators_data_${i}`];
				if (!control) return;
				control.$wrapper.find("label.control-label").hide();
				if (control.grid && paint_evaluators_grid(control.grid, counts)) dup = true;
			});
			return dup;
		};

		const dialog = new frappe.ui.Dialog({
			title: [row.emp_id, emp_name].filter(Boolean).join(" ") + " - " + __("Evaluators Mapping"),
			size: "extra-large",
			fields: dialog_fields,
			primary_action_label: __("Save"),
			primary_action() {
				if (document.activeElement) document.activeElement.blur();
				if (paint_open_tables()) return;
				let rows = [];
				groups.forEach((g, i) => {
					const grid = dialog.fields_dict[`evaluators_data_${i}`].grid;
					((grid && grid.get_data()) || []).forEach((r) => {
						if (!r.category && !fallback_general) r.category = g;
						rows.push(r);
					});
				});
				rows.forEach((r, idx) => {
					r.idx = idx + 1;
				});
				rows = rows.filter((r) => {
					const v = r.evl_id;
					return v !== null && v !== undefined && !(typeof v === "string" && !v.trim());
				});
				row.evaluators_mapping = rows.map((r) => ({
					...r,
					doctype: child_doctype,
				}));
				if (row.name && !String(row.name).startsWith("new-")) {
					frm.doc.__onload = frm.doc.__onload || {};
					frm.doc.__onload.evaluators = frm.doc.__onload.evaluators || {};
					frm.doc.__onload.evaluators[row.name] = row.evaluators_mapping.map((r) => ({ ...r }));
				}
				frm.refresh_field("evaluations_mapping");
				frm.dirty();
				dialog.hide();
			},
		});

		const last_link = new WeakMap();
		const fetch_linked_values = () => {
			groups.forEach((g, i) => {
				const grid = dialog.fields_dict[`evaluators_data_${i}`].grid;
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
						if (targets.every((x) => d[x.target] !== null && d[x.target] !== undefined && d[x.target] !== "")) {
							last_link.set(d, current);
							return;
						}
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
								last_link.set(d, current);
								if (changed) grid.refresh();
							});
					});
				});
			});
		};

		dialog.$wrapper.modal({ backdrop: "static", keyboard: false });
		dialog.show();
		dialog.$wrapper.find(".modal-dialog").css({ width: "1400px", "max-width": "95%" });
		paint_open_tables();
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
		groups.forEach((g, i) => {
			const control = dialog.fields_dict[`evaluators_data_${i}`];
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
				control.grid.wrapper.on("focusin", paint_open_tables);
			}
		});

		const switch_tab = (index) => {
			groups.forEach((g, i) => {
				const table = dialog.fields_dict[`evaluators_data_${i}`];
				if (!table) return;
				if (i === index) {
					table.$wrapper.show();
					if (table.grid) table.grid.refresh();
				} else {
					table.$wrapper.hide();
				}
			});
		};
		dialog.fields_dict.evaluator_tabs.$wrapper.append(
			frappe.ui.tab_buttons({
				options: groups.map((g, i) => ({ label: g, value: i })),
				value: 0,
				on_change: (value) => switch_tab(Number(value)),
			})
		);
		dialog.fields_dict.evaluator_tabs.$wrapper.append(
			frappe.ui.divider({}).css("margin", "12px 0 16px")
		);
		switch_tab(0);
}
