# Copyright (c) 2024, Upeosoft Limited
# For license information, please see license.txt


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Weigh Bridge Ticket", "fieldname": "weighbridge_ticket_id", "fieldtype": "Link", "options": "Weigh Bridge Ticket", "width": 170},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 240},
        {"label": "Ticket No", "fieldname": "ticket_no", "fieldtype": "Data", "width": 100},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Data", "width": 150},
        {"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Data", "width": 100},
        {"label": "Vehicle Type", "fieldname": "vehicle_type", "fieldtype": "Data", "width": 120},
        {"label": "Driver", "fieldname": "driver_name", "fieldtype": "Data", "width": 120},
        {"label": "Material", "fieldname": "material", "fieldtype": "Data", "width": 150},
        {"label": "Net Weight (Kg)", "fieldname": "net_weight", "fieldtype": "Float", "precision": 2, "width": 140},
        {"label": "First Weight (Kg)", "fieldname": "total_weight", "fieldtype": "Float", "precision": 2, "width": 140},
        {"label": "Second Weight (Kg)", "fieldname": "truck_weight", "fieldtype": "Float", "precision": 2, "width": 160},
    ]

def get_data(filters):
    conditions = ""
    if filters and filters.get('from_date'):
        conditions += f"AND posting_date >= '{filters.get('from_date')}' "

    if filters and filters.get('to_date'):
        conditions += f"AND posting_date <= '{filters.get('to_date')}' "
    if filters and filters.get('weighbridge_ticket_id'):
        conditions += f"AND name = '{filters.get('weighbridge_ticket_id')}' "
    if filters and filters.get('material'):
        conditions += f"AND material = '{filters.get('material')}' "
    if filters and filters.get('supplier'):
        conditions += f"AND supplier= '{filters.get('supplier')}' "

    # SQL Query
    query = f"""
        SELECT 
            name AS weighbridge_ticket_id,
            posting_date AS date,
            ticket_no,
            supplier,
            CASE 
                WHEN internal_vehicle = 'Yes' THEN internal_vehicle_reg 
                ELSE external_vehicle_reg 
            END AS vehicle,
            vehicle_type,
            driver_name,
            material,
            total_weight,
            truck_weight,
            net_weight,
            workflow_state AS status
        FROM 
            `tabWeigh Bridge Ticket`
        WHERE 1=1 {conditions}
        ORDER BY modified DESC
    """

    # Execute query
    data = frappe.db.sql(query, filters, as_dict=True)
    return data
