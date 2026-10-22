# corpdk_fx

**ERPNext / Frappe v16** app: configurable currency pairs, **FX Rates** desk page, and Sales Invoice `conversion_rate` on submit.

## Frankfurter API (v2)

All live rates use **[Frankfurter v2](https://frankfurter.dev)** at `https://api.frankfurter.dev/v2` only.

Implementation: [`corpdk_fx/services/frankfurter_v2.py`](corpdk_fx/services/frankfurter_v2.py) (uses Frappe `get_request_session()`; expected HTTP 404s are not logged as integration errors).

## v16 desk integration

- **Apps screen:** `add_to_apps_screen` → `/desk/corpdk-fx-rates`
- **Workspace:** **CorpDK FX** (shortcuts to FX Rates and CorpDK FX Pair)
- **Bench:** `[tool.bench.frappe-dependencies]` requires Frappe `>=16,<17`
- **Guards:** `before_install` / `before_migrate` enforce Frappe and ERPNext 16+

## Install

```bash
bench get-app https://github.com/CorpDK/corpdk_fx
bench --site <site> install-app corpdk_fx
```

CorpDK local bench: cloned in the ERP bench image from this repo ([`CorpDK/ERP`](https://github.com/CorpDK/ERP) `local/Dockerfile`). Rebuild the image and bounce the stack; **`configurator`** runs **`bench migrate`** (`patches.txt`, **`after_migrate`**).

Desk: **CorpDK FX** on Home, or **FX Rates** at `/desk/corpdk-fx-rates`.

**GST Settings** (overseas transactions, e-Waybill, e-invoice, portal API) are configured only in the desk on your site DB — not in this app.

## Export invoice FX (two dates)

| What | FBIL date | ERP |
|------|-----------|-----|
| SOW / service USD amounts | Enter USD directly | Header `conversion_rate` = **`posting_date`** on save/submit (Rule 34(2)) |
| Reimb at cost (INR paid) | **Date X** (payment / supplier invoice) | Line **Reimb INR (paid)** + **Reimb FX date** → USD `rate` = INR ÷ FBIL(date X) |

Holdings policy: [`Export invoice USD-INR rate policy.md`](file:///workspace/Holdings/CorpDK/India/GST/Export%20invoice%20USD-INR%20rate%20policy.md).
