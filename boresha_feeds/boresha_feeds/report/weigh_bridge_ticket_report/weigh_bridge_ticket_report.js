// Copyright (c) 2025, kuriakevin06@gmail.com and contributors
// For license information, please see license.txt


frappe.query_reports["Weigh Bridge Ticket Report"] = {
	filters: [
	  {
		fieldname: "weighbridge_ticket_id",
		label: "Weigh Bridge Ticket",
		options: "Weigh Bridge Ticket",
		fieldtype: "Link",
		width: 80,
		reqd: 0,
	  },
	  {
		fieldname: "material",
		label: "Material",
		options: "Item",
		fieldtype: "Link",
		width: 80,
		reqd: 0,
	  },
	  {
		fieldname: "supplier",
		label: "Supplier",
		options: "Supplier",
		fieldtype: "Link",
		width: 80,
		reqd: 0,
	  },
	  {
		"fieldname": "from_date",
		"label": __("From Date"),
		"fieldtype": "Date",
	},
	{
		"fieldname": "to_date",
		"label": __("To Date"),
		"fieldtype": "Date",
	},
	],
  };
  