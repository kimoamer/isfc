import re

import frappe
from frappe import _


def _strip_outer_parentheses(s: str) -> str:
    """Remove parentheses that wrap the entire expression, e.g. (a==1 or b==2)."""
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        fully_wrapped = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                # If the outermost pair closes before the end, it's not a full wrap
                if depth == 0 and i != len(s) - 1:
                    fully_wrapped = False
                    break
        if fully_wrapped and depth == 0:
            s = s[1:-1].strip()
        else:
            break
    return s


def filter_pricing_rule_based_on_condition(pricing_rules, doc=None):
    filtered_pricing_rules = []
    if not doc:
        return pricing_rules

    # Flatten the document fields so bare-field conditions work
    # (e.g. `coupon_code == "X"`), AND expose `doc` itself so conditions
    # written as `doc.field` (e.g. `doc.coupon_code and doc.coupon_code != ""`)
    # resolve too. ERPNext's original only passed the flattened dict, so any
    # rule condition referencing `doc.*` raised NameError and was dropped —
    # which is why coupon rules using `doc.coupon_code` never applied.
    row = doc.as_dict() if hasattr(doc, "as_dict") else dict(doc)
    context = dict(row)
    # Use a frappe._dict so attribute access (`doc.coupon_code`) always works,
    # regardless of whether `doc` came in as a Document or a plain dict.
    context.setdefault("doc", frappe._dict(row))

    for pricing_rule in pricing_rules:
        cond = getattr(pricing_rule, "condition", None)
        if not cond:
            filtered_pricing_rules.append(pricing_rule)
            continue

        # 1) Evaluate the condition as a whole, exactly like ERPNext's original.
        #    This correctly handles compound conditions that mix `and`/`or`
        #    with parentheses, e.g. `a == "x" and (b == "y" or c == "z")`.
        try:
            if frappe.safe_eval(cond, None, context):
                filtered_pricing_rules.append(pricing_rule)
            continue
        except Exception:
            whole_error = frappe.get_traceback()

        # 2) Fallback: some legacy conditions only parse once split on `or`.
        #    Only reached if evaluating the whole condition raised.
        matched = False
        split_error = None
        try:
            cond_str = _strip_outer_parentheses(cond.strip())
            parts = [cond_str]
            if re.search(r"\bor\b", cond_str, flags=re.IGNORECASE):
                parts = [
                    _strip_outer_parentheses(p)
                    for p in re.split(r"\bor\b", cond_str, flags=re.IGNORECASE)
                    if p.strip()
                ]

            for part in parts:
                if frappe.safe_eval(part, None, context):
                    matched = True
                    break
        except Exception:
            split_error = frappe.get_traceback()

        if matched:
            filtered_pricing_rules.append(pricing_rule)
        else:
            # 3) Both attempts failed — surface it instead of swallowing silently,
            #    so a broken condition can be diagnosed rather than dropping the rule.
            frappe.log_error(
                title=_("Pricing Rule condition evaluation failed"),
                message=_(
                    "Pricing Rule: {0}\nCondition: {1}\n\n"
                    "Whole-condition error:\n{2}\n\nSplit-fallback error:\n{3}"
                ).format(
                    getattr(pricing_rule, "name", pricing_rule),
                    cond,
                    whole_error,
                    split_error or _("condition evaluated to a falsy value"),
                ),
            )

    return filtered_pricing_rules