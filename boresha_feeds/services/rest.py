import frappe
import requests

@frappe.whitelist()
def process_purchase_receipt_workflow(doc, event):
    try:
        if doc.workflow_state == "Pending Admin Approval":
            received_items = doc.items
            
            for received_item in received_items:
                ordered_qty = frappe.db.get_value(
                    "Purchase Order Item", 
                    {"parent": received_item.purchase_order, "item_code": received_item.item_code}, 
                    "qty"
                )

                if ordered_qty and ordered_qty != received_item.qty:
                    difference = received_item.qty - ordered_qty
                    message = (
                        f"Discrepancy detected in Purchase Receipt {doc.name} for Supplier {doc.supplier}.\n\n"
                        f"Item: {received_item.item_code}\n"
                        f"Ordered Quantity: {ordered_qty}\n"
                        f"Received Quantity: {received_item.qty}\n"
                        f"Difference: {'+' if difference > 0 else ''}{difference}"
                    )

                    system_admins = frappe.db.get_all("User", filters={"role_profile_name": "System Admin"}, fields=["mobile_no"])

                    for system_admin in system_admins:
                        receipient_mobile = system_admin.mobile_no

                        if receipient_mobile:
                            send_sms(receipient_mobile, message)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f'{e}')

def send_sms(mobile, message):
    url = "https://sms.textsms.co.ke/api/services/sendsms/"
    data = {
        "apikey": "6bf53f0bda4924760fb1b2e018e2960d",
        "partnerID": "9546",
        "shortcode": "LEGEND SOFT",
        "mobile": format_mobile_number(mobile),
        "message": message
    }
    
    return requests.get(url, params=data)

def format_mobile_number(mobile):
    mobile = mobile.replace(" ", "")
    filtered_mobile = mobile[-9:]
    mobile = "254" + filtered_mobile
    return mobile
