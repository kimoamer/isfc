import frappe
from frappe import _

def filter_pricing_rule_based_on_condition(pricing_rules, doc=None):
    filtered_pricing_rules = []
    if not doc:
        return pricing_rules

    context = doc.as_dict() if hasattr(doc, "as_dict") else doc

    for pricing_rule in pricing_rules:
        cond = getattr(pricing_rule, "condition", None)
        if not cond:
            filtered_pricing_rules.append(pricing_rule)
            continue

        matched = False
        try:
            cond_str = cond.strip()
            # Remove wrapping parentheses around the entire condition, e.g., (a==1 or b==2)
            def _strip_outer_parentheses(s: str) -> str:
                s = s.strip()
                while s.startswith("(") and s.endswith(")"):
                    depth = 0
                    fully_wrapped = True
                    for i, ch in enumerate(s):
                        if ch == "(":
                            depth += 1
                        elif ch == ")":
                            depth -= 1
                            # If outermost pair closes before the end, it's not a full wrap
                            if depth == 0 and i != len(s) - 1:
                                fully_wrapped = False
                                break
                    if fully_wrapped and depth == 0:
                        s = s[1:-1].strip()
                    else:
                        break
                return s

            cond_str = _strip_outer_parentheses(cond_str)
            import re
            parts = [cond_str]
            if re.search(r"\bor\b", cond_str, flags=re.IGNORECASE):
                parts = [
                    _strip_outer_parentheses(p)
                    for p in re.split(r"\bor\b", cond_str, flags=re.IGNORECASE)
                    if p.strip()
                ]

            for part in parts:
                try:
                    if frappe.safe_eval(part, None, context):
                        matched = True
                        break
                except Exception:
                    continue
        except Exception:
            matched = False

        if matched:
            filtered_pricing_rules.append(pricing_rule)

    return filtered_pricing_rules