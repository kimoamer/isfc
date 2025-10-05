import frappe
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from erpnext.accounts.party import get_party_account
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
    args = frappe.flags.args
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)

    # 0 qty is accepted, as the qty is uncertain for some items
    has_unit_price_items = frappe.db.get_value("Sales Order", source_name, "has_unit_price_items")

    def is_unit_price_row(source):
        return has_unit_price_items and source.qty == 0

    def postprocess(source, target):
        set_missing_values(source, target)
        # Get the advance paid Journal Entries in Sales Invoice Advance
        if target.get("allocate_advances_automatically"):
            target.set_advances()
        
        

    def set_missing_values(source, target):
        target.flags.ignore_permissions = True
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            # set company address
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

        # set the redeem loyalty points if provided via shopping cart
        if source.loyalty_points and source.order_type == "Shopping Cart":
            target.redeem_loyalty_points = 1

        target.debit_to = get_party_account("Customer", source.customer, source.company)

    def update_item(source, target, source_parent):
        def get_billed_qty(so_item_name):
            from frappe.query_builder.functions import Sum

            table = frappe.qb.DocType("Sales Invoice Item")
            query = (
                frappe.qb.from_(table)
                .select(Sum(table.qty).as_("qty"))
                .where((table.docstatus == 1) & (table.so_detail == so_item_name))
            )
            return query.run(pluck="qty")[0] or 0

        if source_parent.has_unit_price_items:
            # 0 Amount rows (as seen in Unit Price Items) should be mapped as it is
            pending_amount = flt(source.amount) - flt(source.billed_amt)
            target.amount = pending_amount if flt(source.amount) else 0
        else:
            target.amount = flt(source.amount) - flt(source.billed_amt)

        target.base_amount = target.amount * flt(source_parent.conversion_rate)
        target.qty = (
            source.qty - get_billed_qty(source.name)
            if (source.qty and source.billed_amt)
            else (source.qty if is_unit_price_row(source) else source.qty - source.returned_qty)
        )

        if source_parent.project:
            target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
        if target.item_code:
            item = get_item_defaults(target.item_code, source_parent.company)
            item_group = get_item_group_defaults(target.item_code, source_parent.company)
            cost_center = item.get("selling_cost_center") or item_group.get("selling_cost_center")

            if cost_center:
                target.cost_center = cost_center

    def select_item(d):
        filtered_items = args.get("filtered_children", [])
        child_filter = d.name in filtered_items if filtered_items else True
        return child_filter
    field_map = {
                    "party_account_currency": "party_account_currency",
                    "payment_terms_template": "payment_terms_template",
                    "ignore_pricing_rule": "ignore_pricing_rule",
                }

    doclist = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Sales Invoice",
                "field_map": field_map,
                "field_no_map": ["payment_terms_template"],
                "validation": {"docstatus": ["=", 1]},
            },
            "Sales Order Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "name": "so_detail",
                    "parent": "sales_order",
                    "rate": "rate",
                },
                "postprocess": update_item,
                "condition": lambda doc: (
                    True
                    if is_unit_price_row(doc)
                    else (doc.qty and (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)))
                )
                and select_item(doc),
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "reset_value": True,
            },
            "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
        },
        target_doc,
        postprocess,
        ignore_permissions=ignore_permissions,
    )

    automatically_fetch_payment_terms = cint(
        frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
    )
    if automatically_fetch_payment_terms:
        doclist.set_payment_schedule()

    if args.get("pos_profile"):
        doclist.update({"is_pos": 1})
        doclist.update({"pos_profile": args.get("pos_profile")})

    return doclist
