import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class CustomSalesInvoice(SalesInvoice):
	def set_pos_fields(self, for_validate=False):
		# Capture existing values mapped from Sales Order
		mapped_apply_discount_on = self.get("apply_discount_on")
		mapped_discount_amount = self.get("discount_amount")
		mapped_additional_discount_percentage = self.get("additional_discount_percentage")

		# Call standard set_pos_fields
		super().set_pos_fields(for_validate)

		# If mapped from a Sales Order, preserve the discount fields
		if any(item.get("so_detail") for item in self.get("items")):
			if mapped_apply_discount_on:
				self.apply_discount_on = mapped_apply_discount_on
			if mapped_discount_amount:
				self.discount_amount = mapped_discount_amount
			if mapped_additional_discount_percentage:
				self.additional_discount_percentage = mapped_additional_discount_percentage

	def set_missing_item_details(self, for_validate: bool = False):
		# populate defaults first
		super().set_missing_item_details(for_validate)

		# force rates from linked Sales Order Items
		any_so_linked = False
		for item in self.get("items"):
			so_detail = item.get("so_detail")
			if not so_detail:
				continue

			row = frappe.db.get_value(
				"Sales Order Item",
				so_detail,
				[
					"rate",
					"price_list_rate",
					"discount_percentage",
					"discount_amount",
					"item_tax_template",
					"item_tax_rate",
				],
				as_dict=True,
			)
			if not row:
				continue

			if row.rate is not None:
				item.rate = row.rate
			if row.price_list_rate is not None and item.meta.get_field("price_list_rate"):
				item.price_list_rate = row.price_list_rate
			if row.discount_percentage is not None and item.meta.get_field("discount_percentage"):
				item.discount_percentage = row.discount_percentage
			if row.discount_amount is not None and item.meta.get_field("discount_amount"):
				item.discount_amount = row.discount_amount

			any_so_linked = True

		# prevent pricing rules from overriding SO rates
		if any_so_linked and not self.get("ignore_pricing_rule"):
			self.ignore_pricing_rule = 1