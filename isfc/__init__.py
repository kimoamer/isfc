__version__ = "0.0.1"

from isfc.overrides.pricing_rule.utils import filter_pricing_rule_based_on_condition as filter_based_on_condition
import erpnext.accounts.doctype.pricing_rule.utils


erpnext.accounts.doctype.pricing_rule.utils.filter_pricing_rule_based_on_condition = filter_based_on_condition

# Monkey patch point of sale get_items
from isfc.overrides.point_of_sale import custom_get_items
import erpnext.selling.page.point_of_sale.point_of_sale

erpnext.selling.page.point_of_sale.point_of_sale.get_items = custom_get_items

# Monkey patch: keep discount_amount consistent with the compounded
# discount_percentage when pricing rules stack (apply_discount_on_rate), so the
# client doesn't drop the coupon discount by trusting a stale discount_amount.
from isfc.overrides.pricing_rule import discount_consistency
import erpnext.accounts.doctype.pricing_rule.pricing_rule as _prmod

_prmod.apply_price_discount_rule = discount_consistency.apply_price_discount_rule

# Monkey patch: on server-side validate, rediscover pricing rules when a coupon
# is set but its rule isn't in the item's applied list, so the coupon stacks on
# save even if the browser never applied it. Patched on get_item_details because
# that module imports the name at load time and drives the save/validate path.
from isfc.overrides.pricing_rule import coupon_rediscover
import erpnext.stock.get_item_details as _gid

_gid.get_pricing_rule_for_item = coupon_rediscover.get_pricing_rule_for_item