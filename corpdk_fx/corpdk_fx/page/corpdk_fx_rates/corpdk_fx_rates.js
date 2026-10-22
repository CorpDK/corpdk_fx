frappe.pages["corpdk-fx-rates"].on_page_load = function (wrapper) {
	const $page = $(wrapper);
	$page.addClass("corpdk-fx-rates-page");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("FX Rates"),
		single_column: true,
	});

	page.set_primary_action(__("Refresh all"), () => load(true));
	page.add_menu_item(__("CorpDK FX Pair"), () => frappe.set_route("List", "CorpDK FX Pair"));

	const $root = $(`
		<div class="corpdk-fx-rates">
			<p class="corpdk-fx-rates-intro text-muted"></p>
			<div class="corpdk-fx-rates-list frappe-list">
				<div class="list-row-head corpdk-fx-rates-grid">
					<div>${__("Pair")}</div>
					<div>${__("Provider")}</div>
					<div>${__("Company")}</div>
					<div>${__("30-day trend")}</div>
					<div class="text-right">${__("Rate")}</div>
					<div>${__("Effective / feed")}</div>
				</div>
				<div class="corpdk-fx-rates-body"></div>
			</div>
		</div>
	`).appendTo(page.main);

	const pair_link = `<a href="#" class="corpdk-fx-intro-link">${__("CorpDK FX Pair")}</a>`;
	$root
		.find(".corpdk-fx-rates-intro")
		.html(
			__(
				"Live rates for today’s posting date. Manage policies on {0}.",
				[pair_link]
			)
		);

	$root.find(".corpdk-fx-intro-link").on("click", (e) => {
		e.preventDefault();
		frappe.set_route("List", "CorpDK FX Pair");
	});

	const $body = $root.find(".corpdk-fx-rates-body");

	function provider_indicator(provider) {
		const key = (provider || "").toLowerCase();
		if (key.includes("fbil")) return "blue";
		if (key.includes("ecb")) return "green";
		if (key.includes("currency exchange") || key.includes("erpnext")) return "orange";
		if (key.includes("frankfurter")) return "cyan";
		return "gray";
	}

	function format_rate(rate) {
		if (rate == null || rate === "") return "—";
		return frappe.format(rate, { fieldtype: "Float", precision: 4 });
	}

	function open_pair(pair_name) {
		frappe.set_route("Form", "CorpDK FX Pair", pair_name);
	}

	function sparkline_svg(rates) {
		if (!rates || rates.length < 2) {
			return `<span class="corpdk-fx-sparkline-empty text-muted">${__("—")}</span>`;
		}
		const w = 120;
		const h = 32;
		const pad = 2;
		const min = Math.min(...rates);
		const max = Math.max(...rates);
		const span = max - min || 1;
		const pts = rates.map((v, i) => {
			const x = pad + (i / (rates.length - 1)) * (w - pad * 2);
			const y = pad + (1 - (v - min) / span) * (h - pad * 2);
			return { x, y };
		});
		let paths = "";
		for (let i = 1; i < pts.length; i++) {
			const a = pts[i - 1];
			const b = pts[i];
			const down = b.y > a.y;
			const stroke = down ? "var(--red-500, #f87171)" : "var(--green-500, #5ecf8a)";
			paths += `<path d="M${a.x.toFixed(1)} ${a.y.toFixed(1)} L${b.x.toFixed(1)} ${b.y.toFixed(
				1
			)}" stroke="${stroke}" stroke-width="1.75" stroke-linecap="round"/>`;
		}
		return `<svg class="corpdk-fx-sparkline" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-hidden="true">${paths}</svg>`;
	}

	function render_row(row) {
		if (row.error) {
			return $(`
				<div class="corpdk-fx-rate-row">
					<div class="list-row">
						<div class="corpdk-fx-rates-grid">
							<div>
								<span class="bold">${frappe.utils.escape_html(row.pair)}</span>
							</div>
							<div class="text-danger" style="grid-column: span 5">${frappe.utils.escape_html(
								row.error
							)}</div>
						</div>
					</div>
				</div>
			`);
		}

		const ccy =
			row.from_currency && row.to_currency
				? `${row.from_currency} → ${row.to_currency}`
				: "";
		const pill = provider_indicator(row.provider);
		const $row = $(`
			<div class="corpdk-fx-rate-row">
				<div class="list-row">
					<div class="corpdk-fx-rates-grid">
						<div class="corpdk-fx-pair-cell">
							<a href="#" class="corpdk-fx-pair-link">${frappe.utils.escape_html(row.pair)}</a>
							${
								ccy
									? `<div class="corpdk-fx-ccy">${frappe.utils.escape_html(ccy)}</div>`
									: ""
							}
						</div>
						<div>
							<span class="indicator-pill ${pill} filterable ellipsis" title="${frappe.utils.escape_html(
			row.provider || ""
		)}">
								<span class="ellipsis">${frappe.utils.escape_html(row.provider || "—")}</span>
							</span>
						</div>
						<div class="text-muted">${frappe.utils.escape_html(row.company || "—")}</div>
						<div class="corpdk-fx-trend-cell">${sparkline_svg(row.sparkline)}</div>
						<div class="text-right">
							<div class="corpdk-fx-rate-value">${format_rate(row.rate)}</div>
							${
								row.posting_date
									? `<div class="corpdk-fx-rate-meta">${__("Posting")} ${frappe.utils.escape_html(
											row.posting_date
									  )}</div>`
									: ""
							}
						</div>
						<div>
							<div>${frappe.utils.escape_html(row.effective_date || "—")}</div>
							<div class="corpdk-fx-feed">${frappe.utils.escape_html(row.feed || row.source || "")}</div>
						</div>
					</div>
				</div>
			</div>
		`);
		$row.find("a.corpdk-fx-pair-link").on("click", (e) => {
			e.preventDefault();
			open_pair(row.pair);
		});
		return $row;
	}

	function load(refresh) {
		page.set_indicator(__("Loading…"), "orange");
		frappe.call({
			method: refresh ? "corpdk_fx.api.refresh_all_pairs" : "corpdk_fx.api.get_dashboard",
			freeze: true,
			callback(r) {
				page.clear_indicator();
				const rows = r.message || [];
				$body.empty();
				if (!rows.length) {
					$body.append(
						`<div class="corpdk-fx-empty">${__(
							"No enabled pairs. Create a CorpDK FX Pair."
						)}</div>`
					);
					return;
				}
				for (const row of rows) {
					$body.append(render_row(row));
				}
			},
		});
	}

	load(false);
};
