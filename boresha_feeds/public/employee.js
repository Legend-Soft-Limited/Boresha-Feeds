frappe.ui.form.on('Employee', {
    validate: function(frm) {
        if (frm.is_new() && frm.doc.custom_salary_structure && frm.doc.custom_basic_salary) {
            // Ensure fields are filled
            frappe.call({
                method: 'frappe.client.submit',
                args: {
                    doc: {
                        doctype: 'Salary Structure Assignment',
                        employee: frm.doc.name,
                        salary_structure: frm.doc.custom_salary_structure,
                        base: frm.doc.custom_basic_salary,
                        from_date: frappe.datetime.get_today(),
                    },
                },
                callback: function(response) {
                    
                                if (!response.exc) {
                                    frappe.msgprint(__('Employee Salary Structure Assignment submitted successfully.'));
                                } else {
                                    frappe.msgprint(__('Error while submitting Employee Salary Structure Assignment.'));
                                }
                            },
                   
                
            });
        } else if (!frm.is_new()) {
            frappe.msgprint(__('Salary Structure Assignment is only created for new employees.'));
        } else {
            frappe.throw(__('Please ensure Salary Structure and Basic Salary are filled.'));
        }
    },
});
