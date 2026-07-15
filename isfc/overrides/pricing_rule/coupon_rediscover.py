import frappe

from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
    get_pricing_rule_for_item as _orig_get_pricing_rule_for_item,
)
from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules


def get_pricing_rule_for_item(args, doc=None, for_validate=False):
    """Rediscover pricing rules on server-side validate when a coupon is unapplied.

    ERPNext's original takes a shortcut on validate (for_validate=True): when the
    item already carries a ``pricing_rules`` value it only re-validates THOSE
    rules and never searches for new ones. So a coupon-based rule the browser
    failed to apply is never picked up on save, and the coupon silently never
    stacks (the item stays at its non-coupon discount).

    When a coupon is set and its linked pricing rule is NOT already in the
    item's applied list, force a fresh discovery (the get_pricing_rules() path)
    so the coupon rule is found and applied. Once it IS applied, this becomes a
    no-op and the original fast path runs again -> it fixes the gap, then steps
    aside. ``ignore_pricing_rule`` is honoured by the original (it returns early),
    so B2B/ignore orders are untouched.
    """
    if for_validate and args.get("coupon_code") and args.get("pricing_rules"):
        applied = set(get_applied_pricing_rules(args.get("pricing_rules")) or [])
        coupon_rule = frappe.db.get_value(
            "Coupon Code", args.get("coupon_code"), "pricing_rule"
        )
        if coupon_rule and coupon_rule not in applied:
            for_validate = False

    return _orig_get_pricing_rule_for_item(args, doc=doc, for_validate=for_validate)
