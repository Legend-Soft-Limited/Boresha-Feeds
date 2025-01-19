import frappe
import requests
import random


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


@frappe.whitelist( allow_guest=True )
def login(usr, pwd):
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key":0,
            "message":"Authentication Error!"
        }

        return

    api_generate = generate_keys(frappe.session.user)
    user = frappe.get_doc('User', frappe.session.user)

    frappe.response["message"] = {
        "success_key":1,
        "message":"Authentication success",
        "sid":frappe.session.sid,
        "api_key":user.api_key,
        "api_secret":api_generate,
        "username":user.username,
        "email":user.email,
        "base_url": frappe.utils.get_url()
    }

def generate_keys(user):
    user_details = frappe.get_doc('User', user)
    api_secret = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key

    user_details.api_secret = api_secret
    user_details.save()

    return api_secret


@frappe.whitelist( methods="GET" )
def get_suppliers():
    try:
        suppliers = frappe.get_all("Supplier", fields=["name"])
        
        supplier_list = [{"supplier": supplier["name"]} for supplier in suppliers]
        
        return {'status': 200, 'suppliers': supplier_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400


@frappe.whitelist( methods="GET" )
def get_vehicles():
    try:
        vehicles = frappe.get_all("Vehicle", fields=["name"])
        
        vehicle_list = [{"vehicle": vehicle["name"]} for vehicle in vehicles]
        
        return {'status': 200, 'vehicles': vehicle_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400


@frappe.whitelist( methods="GET" )
def get_raw_materials():
    try:
        raw_materials = frappe.get_all("Item", filters={"item_group": "Raw Material"}, fields=["name"])
        
        raw_material_list = [{"raw_material": raw_material["name"]} for raw_material in raw_materials]
        
        return {'status': 200, 'raw_materials': raw_material_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400



@frappe.whitelist( methods="POST" )
def generate_otp(mobile_number):
    try:
        if frappe.db.exists("User", {"mobile_no": mobile_number}):

            existing_otp = frappe.db.get_value("One Time Password", {"mobile_number": mobile_number}, "name")
            if existing_otp:
                frappe.delete_doc("One Time Password", existing_otp)
                frappe.db.commit()


            if send_opt(mobile_number):
                return {
                    'status': 200,
                    'message': f'OTP sent to {mobile_number}.',
                }
        else:
            return {
                'status': 400,
                'message': 'Mobile number not found. Please try again.',
            }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {
            'status': 500,
            'message': f'An error occurred: {str(e)}',
        }


def send_opt(mobile_number):
    try:
        otp = random.randint(100000, 999999)

        on_time_password_doc = frappe.get_doc({
            "doctype": "One Time Password",
            "mobile_number": mobile_number,
            "one_time_password": otp
        })
        on_time_password_doc.insert(ignore_mandatory= True, ignore_permissions= True)
        frappe.db.commit()

        message = (
            f"Your OTP is {on_time_password_doc.on_time_password}."
        )
                    
        if send_sms(on_time_password_doc.mobile_number, message):
            return {
                    'status': 200,
                    'message': f'OTP sent to {mobile_number}.',
                }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {
            'status': 500,
            'message': f'An error occurred: {str(e)}',
        }


@frappe.whitelist(methods="POST")
def create_weigh_bridge_ticket(**kwargs):
    try:
        driver_name = kwargs.get('driver_name')
        if driver_name:
            driver_name = driver_name.upper()

        external_vehicle_reg_number = kwargs.get('external_vehicle_reg_number')

        if external_vehicle_reg_number:
            external_vehicle_reg_number = external_vehicle_reg_number.upper()

        weigh_bridge_ticket_doc = frappe.get_doc({
            "doctype": "Weigh Bridge Ticket",
            "ticket_no": kwargs.get('ticket_no'),
            "supplier": kwargs.get('supplier'),
            "internal_vehicle": kwargs.get('internal_vehicle'),
            "external_vehicle_reg": external_vehicle_reg_number,
            "internal_vehicle_reg": kwargs.get('internal_vehicle_reg_number'),
            "vehicle_type": kwargs.get('vehicle_type'),
            "driver_name": driver_name,
            "drive_mobile_no": kwargs.get('drive_mobile_no'),
            "driver_identity_number": kwargs.get('driver_identity_number'),
            "material": kwargs.get('raw_material'),
            "total_weight": kwargs.get('first_weight'),
            "gross_time": kwargs.get('first_weight_time')
        })
        weigh_bridge_ticket_doc.insert(ignore_mandatory=True, ignore_permissions=True)
        frappe.db.commit()
        return {'status': 200, 'message': 'Weight bridge created successfully.'}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {
            'status': 500,
            'message': f'An error occurred: {str(e)}',
        }

    

@frappe.whitelist( methods="POST" )
def update_second_weight(**kwargs):
    try:
        if frappe.db.exists("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')}):

            weigh_bridge_ticket_doc  =  frappe.get_doc("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')})
            net_weight  = float(weigh_bridge_ticket_doc.total_weight) - float(kwargs.get('second_weight'))
            frappe.db.set_value("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')}, {"truck_weight": kwargs.get('second_weight'), "net_weight": net_weight})
            frappe.db.commit()
            
            return {'status': 200, 'message': 'Second weight updated successfully.'}
        else:
            return {'error': 'Weigh bridge ticket does not exist'}, 404

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {
            'status': 500,
            'message': f'An error occurred: {str(e)}',
        }
    


@frappe.whitelist( methods="POST" )
def forward_weigh_bridge_ticket_to_store_clerk(**kwargs):
    try:
        if frappe.db.exists("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')}):
            frappe.db.set_value("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')}, {"workflow_state": "Pending Approval by Store Clerk"})
            frappe.db.commit()
            
            return {'status': 200, 'message': 'Ticket fowarded successfully.'}
        else:
            return {'error': 'Weigh bridge ticket does not exist'}, 404

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {
            'status': 500,
            'message': f'An error occurred: {str(e)}',
        }
    



@frappe.whitelist(methods="GET")
def get_weigh_bridge_tickets():
    try:

        weigh_bridge_tickets = frappe.db.get_all(
            "Weigh Bridge Ticket",
            fields=["name as weigh_brigde_ticket_no", "total_weight as first_weight", "material as raw_material", "driver_name as driver_name", "supplier"],
            filters={"workflow_state": "Draft"},
            order_by="modified desc"
        )

        if not weigh_bridge_tickets:
            return {'status': 404, 'message': 'No tickets found.'}


        return {'status': 200, 'ticket_data': weigh_bridge_tickets}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {'error': str(e)}, 400