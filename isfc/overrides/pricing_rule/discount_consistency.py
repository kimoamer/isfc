from frappe.utils import flt

import erpnext.accounts.doctype.pricing_rule.pricing_rule as prmod

# Keep a handle on the untouched ERPNext implementation.
_orig_apply_price_discount_rule = prmod.apply_price_discount_rule


def apply_price_discount_rule(pricing_rule, item_details, args):
    """Fix the discount_amount/discount_percentage inconsistency for stacked rules.

    When a pricing rule has ``apply_discount_on_rate`` set, ERPNext compounds the
    ``discount_percentage`` (e.g. 10% then +3% coupon -> 12.7%) but leaves
    ``discount_amount`` at the value from the first rule only (66.9 = 10% of the
    price). The result the server returns is internally inconsistent.

    The client (taxes_and_totals.js) trusts ``discount_amount`` over
    ``discount_percentage``, so it recomputes the rate from the stale 66.9 and
    silently drops the compounded portion (the coupon discount) -> the item ends
    up at 10% instead of 12.7%.

    We re-sync ``discount_amount`` with the compounded ``discount_percentage`` so
    both the browser and the server-side calculation land on the same, correct
    figure. Scoped to percentage rules that use apply_discount_on_rate, so no
    other pricing behaviour changes.
    """
    _orig_apply_price_discount_rule(pricing_rule, item_details, args)

    if (
        pricing_rule.get("rate_or_discount") == "Discount Percentage"
        and pricing_rule.get("apply_discount_on_rate")
        and flt(args.get("price_list_rate"))
        and flt(item_details.get("discount_percentage"))
    ):
        item_details["discount_amount"] = (
            flt(args.get("price_list_rate")) * flt(item_details.get("discount_percentage")) / 100
        )
