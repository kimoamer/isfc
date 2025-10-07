// Override the ERPNext Sales Order Controller
frappe.ui.form.on('Sales Order', {
    onload: function(frm) {
        // Extend the existing controller
        if (cur_frm.cscript && cur_frm.cscript.make_sales_invoice) {
            // Store the original method
            cur_frm.cscript._original_make_sales_invoice = cur_frm.cscript.make_sales_invoice;
            
            // Override with our custom implementation
            cur_frm.cscript.make_sales_invoice = function() {
                
                const d = new frappe.ui.Dialog({
                    title: __("Create Sales Invoice"),
                    fields: [
                        {
                            label: __("POS Profile"),
                            fieldname: "pos_profile",
                            fieldtype: "Link",
                            options: "POS Profile",
                        }
                    ],
                    primary_action_label: __("Create"),
                    primary_action(values) {
                        d.hide();
                        frappe.model.open_mapped_doc({
                            method: "isfc.overrides.function_overrides.make_sales_invoice",
                            frm: frm,
                            args: {
                                pos_profile: values.pos_profile
                            },
                            run_link_triggers: true
                        });
                    },
                });

                d.show();
            };
        }
    }
});