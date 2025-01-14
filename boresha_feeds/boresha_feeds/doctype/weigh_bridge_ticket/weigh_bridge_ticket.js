// Copyright (c) 2025, kuriakevin06@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Weigh Bridge Ticket", {
	refresh(frm) {
        
	},

    total_weight: function(frm) {
        if(frm.doc.total_weight >= frm.doc.truck_weight){
            frm.set_value("truck_weight", "")
        }{
            frm.set_value("gross_time", frappe.datetime.now_datetime());
            getNetWeight(frm)
        }
    },

    truck_weight: function(frm) {
        if(frm.doc.truck_weight >= frm.doc.total_weight){
            frm.set_value("truck_weight", "")
        }else{
            frm.set_value("tare_time", frappe.datetime.now_datetime());
            getNetWeight(frm)
        }
    },

    no_of_bags(frm){
        let average_weight_per_bag = frm.doc.net_weight/frm.doc.no_of_bags
        frm.set_value("average_weight_per_bag", average_weight_per_bag)
    }
});


function getNetWeight(frm){
    if (frm.doc.total_weight && frm.doc.truck_weight) {
        frm.set_value('net_weight', frm.doc.total_weight - frm.doc.truck_weight);
    }
}