app_name = "corpdk_fx"
app_title = "CorpDK FX"
app_publisher = "CorpDK"
app_description = "Currency pair policies, live rates, and invoice conversion on submit"
app_email = "ops@corpdk.local"
app_license = "MIT"
app_home = "/desk/corpdk-fx-rates"

required_apps = ["frappe/erpnext"]

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/corpdk_fx/images/corpdk-fx.svg",
		"title": app_title,
		"route": app_home,
		"has_permission": "corpdk_fx.permissions.has_app_permission",
	},
]

app_include_css = "/assets/corpdk_fx/css/corpdk_fx_rates.css"

before_install = "corpdk_fx.patches.check_version_compatibility.execute"
before_migrate = "corpdk_fx.patches.check_version_compatibility.execute"

doc_events = {
	"Sales Invoice": {
		"before_save": "corpdk_fx.invoice.before_save",
		"before_submit": "corpdk_fx.invoice.before_submit",
	},
}

after_install = "corpdk_fx.install.after_install"
after_migrate = "corpdk_fx.install.after_migrate"

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Sales Invoice-export_usd_inr_policy",
					"Sales Invoice-export_usd_inr_effective_date",
					"Sales Invoice-export_usd_inr_rate_source",
					"Sales Invoice Item-reimb_inr_amount",
					"Sales Invoice Item-reimb_fx_date",
				],
			]
		],
	},
]
