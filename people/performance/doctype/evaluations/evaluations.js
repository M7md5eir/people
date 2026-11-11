// Copyright (c) 2026, Mohamed Kheir and contributors
// For license information, please see license.txt

(function () {
const METHOD = "people.people.evaluation_result_breakdown.get_result_breakdown";
const NEUTRAL_COLOR = "#8d99a6";

// Frappe exposes flt() as a global, not frappe.utils.flt
function num(value) {
	if (typeof window.flt === "function") return window.flt(value);
	const n = parseFloat(value);
	return Number.isFinite(n) ? n : 0;
}

frappe.ui.form.on("Evaluations", {
	refresh(frm) {
		render_breakdown(frm);
	},
	evaluation_cycle(frm) {
		render_breakdown(frm);
	},
	emp_id(frm) {
		render_breakdown(frm);
	},
});

function render_breakdown(frm) {
	const field = frm.fields_dict.test;
	if (!field || !field.$wrapper) {
		console.warn("[breakdown] HTML field 'test' not found on the form");
		return;
	}
	const wrapper = field.$wrapper;

	const { emp_id, evaluation_cycle } = frm.doc;
	if (frm.is_new() || !emp_id || !evaluation_cycle) {
		wrapper.html(message(__("Select an employee and a cycle to see the breakdown.")));
		return;
	}

	wrapper.html(message(__("Loading…")));
	frappe
		.call({
			method: METHOD,
			args: { evaluation_cycle, emp_id },
		})
		.then((r) => {
			if (!r || !r.message) {
				wrapper.html(message(__("No data returned.")));
				return;
			}
			wrapper.html(render_result(r.message));
			bind_toggles(wrapper);
		})
		.catch((err) => {
			console.error("[breakdown]", err);
			wrapper.html(message(__("Could not load the breakdown. Check the browser console and Error Log.")));
		});
}

function message(text) {
	return `<div class="er-breakdown">${STYLE}<div class="er-empty">${text}</div></div>`;
}

function render_result(data) {
	const rates = (data.rates || [])
		.slice()
		.sort((a, b) => num(a.min_score) - num(b.min_score));
	const categories = data.categories || [];
	const completed = categories.reduce((sum, c) => sum + (c.completed || 0), 0);
	const evaluators = categories.reduce((sum, c) => sum + (c.evaluators_count || 0), 0);

	const body = categories.map((c) => category_row(c, rates) + pivot_row(c, rates)).join("");

	return `<div class="er-breakdown">
		${STYLE}
		<div class="er-table-wrap">
			<table class="er-main">
				<thead>
					<tr>
						<th>${__("Category")}</th>
						<th class="er-num">${__("Weight")}</th>
						<th class="er-num">${__("Evaluators")}</th>
						<th class="er-num">${__("Avg Score")}</th>
						<th class="er-num">${__("Weighted")}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
				<tfoot>
					<tr class="er-foot">
						<td>${__("Competencies Score")}</td>
						<td class="er-num">100%</td>
						<td class="er-num">${completed} ${__("of")} ${evaluators}</td>
						<td class="er-num"></td>
						<td class="er-num">${format_number(data.competencies_score)}%</td>
					</tr>
				</tfoot>
			</table>
		</div>
		${legend_html(rates)}
	</div>`;
}

function category_row(category, rates) {
	const band = band_for(category.avg_score, rates);
	const pending = (category.evaluators_count || 0) - (category.completed || 0);
	const pending_pill =
		pending > 0 ? `<span class="er-pill-pending">${pending} ${__("pending")}</span>` : "";
	return `<tr class="er-cat-row">
		<td class="er-cat-name"><span class="er-chev">▾</span>${escape_html(category.category)}</td>
		<td class="er-num">${format_number(category.weight)}%</td>
		<td class="er-num">${category.completed} ${__("of")} ${category.evaluators_count}${pending_pill}</td>
		<td class="er-num">${score_pill(category.avg_score, band)}</td>
		<td class="er-num">${format_number(category.weighted)}</td>
	</tr>`;
}

// Pivot: rows = evaluators, columns = competencies, last column = Total
function pivot_row(category, rates) {
	const evaluators = category.evaluators;
	if (!evaluators) return ""; // non-HR users: category rows only
	if (!evaluators.length) {
		return `<tr class="er-pivot-row"><td colspan="5"><div class="er-pivot-wrap er-empty-pivot">${__(
			"No evaluators"
		)}</div></td></tr>`;
	}

	const competencies = category.competencies || [];
	const done = evaluators.filter((ev) => ev.status === "Completed");
	const pending = evaluators.filter((ev) => ev.status !== "Completed");
	const show_avg = done.length > 1;

	const head =
		`<th class="er-pivot-name">${__("Evaluator")}</th>` +
		competencies
			.map(
				(c) => `<th class="er-pivot-comp">${escape_html(c.competency)}
					<div class="er-comp-weight">${format_number(c.weight)}%</div></th>`
			)
			.join("") +
		`<th class="er-pivot-total">${__("Total")}</th>`;

	const rows =
		done.map((ev) => evaluator_row(ev, competencies, rates)).join("") +
		pending.map((ev) => pending_row(ev, competencies.length + 1)).join("");

	const avg = show_avg ? avg_row(done, competencies, category, rates) : "";

	return `<tr class="er-pivot-row"><td colspan="5">
		<div class="er-pivot-wrap">
			<table class="er-pivot">
				<thead><tr>${head}</tr></thead>
				<tbody>${rows}${avg}</tbody>
			</table>
		</div>
	</td></tr>`;
}

function rating_of(ev, competency) {
	const ratings = ev.ratings || {};
	const key = competency.key !== undefined ? competency.key : competency.competency;
	return ratings[key];
}

function evaluator_link(ev) {
	const name = escape_html(ev.evaluator_name || ev.evaluator_id);
	if (!ev.doc) return name;
	return `<a href="/desk/competencies/${encodeURIComponent(ev.doc)}" target="_blank">${name}</a>`;
}

function evaluator_row(ev, competencies, rates) {
	const cells = competencies
		.map((c) => {
			const value = rating_of(ev, c);
			if (value === undefined || value === null) return `<td class="er-cell">—</td>`;
			return `<td class="er-cell" style="${cell_style(band_for(value, rates))}">${format_number(value)}%</td>`;
		})
		.join("");
	const total =
		ev.score === null || ev.score === undefined
			? "—"
			: `${format_number(ev.score)}%`;
	return `<tr>
		<th class="er-pivot-name">${evaluator_link(ev)}</th>
		${cells}
		<td class="er-cell er-cell-total">${total}</td>
	</tr>`;
}

function pending_row(ev, colspan) {
	return `<tr>
		<th class="er-pivot-name er-name-pending">${evaluator_link(ev)}</th>
		<td class="er-cell er-cell-pending" colspan="${colspan}">${__("Pending")}</td>
	</tr>`;
}

function avg_row(done, competencies, category, rates) {
	const cells = competencies
		.map((c) => {
			const values = done
				.map((ev) => rating_of(ev, c))
				.filter((v) => v !== undefined && v !== null);
			if (!values.length) return `<td class="er-cell er-cell-avg">—</td>`;
			const avg = values.reduce((s, v) => s + num(v), 0) / values.length;
			return `<td class="er-cell er-cell-avg" style="${cell_style(band_for(avg, rates))}">${format_number(avg)}%</td>`;
		})
		.join("");
	return `<tr class="er-avg-row">
		<th class="er-pivot-name">${__("Avg")}</th>
		${cells}
		<td class="er-cell er-cell-avg">${format_number(category.avg_score)}%</td>
	</tr>`;
}

function legend_html(rates) {
	if (!rates.length) return "";
	const items = rates
		.map((rate, index) => {
			const next = rates[index + 1];
			const range = next
				? `${format_number(rate.min_score)}–${format_number(next.min_score - 1)}%`
				: `${format_number(rate.min_score)}%+`;
			return `<span class="er-legend-item"><span class="er-swatch" style="background:${escape_html(
				rate.color
			)}"></span>${escape_html(rate.rate)} <span class="er-legend-range">${range}</span></span>`;
		})
		.join("");
	return `<div class="er-legend">${items}<span class="er-hint">${__(
		"Click a category to expand or collapse its evaluators"
	)}</span></div>`;
}

function bind_toggles(wrapper) {
	wrapper.find(".er-cat-row").off("click").on("click", function () {
		const row = $(this);
		const pivot = row.next(".er-pivot-row");
		if (!pivot.length) return;
		const is_open = pivot.is(":visible");
		pivot.toggle(!is_open);
		row.find(".er-chev").text(is_open ? "▸" : "▾");
	});
}

function band_for(value, rates) {
	let band = { rate: null, color: NEUTRAL_COLOR };
	rates.forEach((rate) => {
		if (num(value) >= num(rate.min_score)) band = rate;
	});
	return band;
}

function cell_style(band) {
	return `background:${hex_to_rgba(band.color, 0.12)};color:${darken(band.color, 0.45)}`;
}

function score_pill(value, band) {
	return `<span class="er-pill" style="background:${hex_to_rgba(band.color, 0.15)};color:${darken(
		band.color,
		0.35
	)}">${format_number(value)}%</span>`;
}

function format_number(value) {
	const number = num(value);
	return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

function hex_to_rgba(color, alpha) {
	let hex = String(color || "").replace("#", "");
	if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
	if (hex.length !== 6) return `rgba(141,153,166,${alpha})`;
	const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
	return `rgba(${r},${g},${b},${alpha})`;
}

function darken(color, amount) {
	let hex = String(color || "").replace("#", "");
	if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
	if (hex.length !== 6) return "#57606a";
	const factor = 1 - amount;
	const channel = (i) => Math.round(parseInt(hex.slice(i, i + 2), 16) * factor);
	return `rgb(${channel(0)},${channel(2)},${channel(4)})`;
}

function escape_html(value) {
	return frappe.utils.escape_html(value === null || value === undefined ? "" : String(value));
}

const STYLE = `<style>
.er-breakdown { margin-top: 4px; }
.er-breakdown .er-empty { padding: 20px; text-align: center; color: var(--text-muted); }
.er-breakdown .er-table-wrap { overflow-x: auto; border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px); background: var(--card-bg); }
.er-breakdown table.er-main { width: 100%; border-collapse: collapse; font-size: var(--text-sm, 12px); }
.er-breakdown .er-main th, .er-breakdown .er-main td { padding: 8px 12px; border-bottom: 1px solid var(--border-color); text-align: left; vertical-align: middle; }
.er-breakdown .er-main thead th { color: var(--text-muted); font-weight: 500; }
.er-breakdown .er-num { text-align: right !important; font-variant-numeric: tabular-nums; }
.er-breakdown .er-cat-row { cursor: pointer; }
.er-breakdown .er-cat-row:hover { background: var(--subtle-fg); }
.er-breakdown .er-cat-name { font-weight: 600; }
.er-breakdown .er-chev { display: inline-block; width: 16px; color: var(--text-muted); }
.er-breakdown .er-pill { display: inline-block; padding: 1px 8px; border-radius: 5px; font-weight: 600; }
.er-breakdown .er-pill-pending { display: inline-block; margin-left: 6px; padding: 1px 7px; border-radius: 10px; background: var(--orange-100, #fff4e5); color: var(--orange-600, #b7791f); font-size: 11px; }
.er-breakdown .er-pivot-row > td { padding: 0 12px 12px 28px; border-bottom: 1px solid var(--border-color); background: var(--subtle-fg); }
.er-breakdown .er-pivot-wrap { overflow-x: auto; border-left: 2px solid var(--border-color); padding-left: 10px; }
.er-breakdown .er-empty-pivot { color: var(--text-muted); padding: 8px 0; }
.er-breakdown table.er-pivot { width: 100%; border-collapse: collapse; font-size: var(--text-sm, 12px); }
.er-breakdown .er-pivot th, .er-breakdown .er-pivot td { padding: 6px 10px; text-align: center; font-variant-numeric: tabular-nums; border-bottom: 1px solid var(--border-color); }
.er-breakdown .er-pivot thead th { color: var(--text-muted); font-weight: 500; vertical-align: bottom; }
.er-breakdown .er-pivot th.er-pivot-comp { white-space: normal; min-width: 90px; max-width: 140px; }
.er-breakdown .er-comp-weight { color: var(--text-muted); font-weight: 400; font-size: 11px; }
.er-breakdown .er-pivot .er-pivot-name { text-align: left; white-space: nowrap; min-width: 170px; font-weight: 500; }
.er-breakdown .er-pivot a { color: var(--text-color); text-decoration: underline dashed; text-underline-offset: 3px; }
.er-breakdown .er-name-pending, .er-breakdown .er-name-pending a { color: var(--text-muted); font-style: italic; }
.er-breakdown .er-cell-pending { font-style: italic; color: var(--text-muted); background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, var(--border-color) 5px, var(--border-color) 6px); }
.er-breakdown .er-cell-total, .er-breakdown .er-cell-avg { font-weight: 600; }
.er-breakdown .er-avg-row th, .er-breakdown .er-avg-row td { border-top: 2px solid var(--border-color); border-bottom: none; }
.er-breakdown .er-foot td { border-bottom: none; font-weight: 700; }
.er-breakdown .er-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; margin-top: 10px; font-size: 12px; }
.er-breakdown .er-legend-item { display: inline-flex; align-items: center; gap: 6px; }
.er-breakdown .er-legend-range { color: var(--text-muted); }
.er-breakdown .er-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.er-breakdown .er-hint { margin-left: auto; color: var(--text-muted); }
</style>`;
})();