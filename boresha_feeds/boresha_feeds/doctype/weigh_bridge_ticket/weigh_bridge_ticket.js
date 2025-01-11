// Copyright (c) 2025, kuriakevin06@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Weigh Bridge Ticket", {
	refresh(frm) {
        
	},

    total_weight: function(frm) {
        getNetWeight(frm)
    },
    truck_weight: function(frm) {
        getNetWeight(frm)
    }
});


function getNetWeight(frm){
    if (frm.doc.total_weight && frm.doc.truck_weight) {
        frm.set_value('net_weight', frm.doc.total_weight - frm.doc.truck_weight);
    }
}