__version__ = "0.0.1"

from isfc.overrides.pricing_rule.utils import filter_pricing_rule_based_on_condition as filter_based_on_condition
import erpnext.accounts.doctype.pricing_rule.utils


erpnext.accounts.doctype.pricing_rule.utils.filter_pricing_rule_based_on_condition = filter_based_on_condition