import frappe
from erpnext.selling.page.point_of_sale.point_of_sale import get_items as original_get_items

@frappe.whitelist()
def custom_get_items(*args, **kwargs):
	# Frappe's RPC handler injects 'cmd' into kwargs; the original function doesn't accept it
	kwargs.pop("cmd", None)
	result = original_get_items(*args, **kwargs)
	if result and result.get("items"):
		item_codes = [item.get("item_code") for item in result.get("items") if item.get("item_code")]
		if item_codes:
			# Query database to find which of the retrieved items are disabled
			disabled_items = set(
				frappe.get_all("Item", filters={"name": ["in", item_codes], "disabled": 1}, pluck="name")
			)
			if disabled_items:
				result["items"] = [
					item for item in result.get("items") if item.get("item_code") not in disabled_items
				]
	return result




