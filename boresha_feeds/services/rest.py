import frappe
import requests
import random
from dateutil import parser


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


@frappe.whitelist( allow_guest=True, methods="POST" )
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

    role_profile = user.role_profile_name

    frappe.response["message"] = {
        "success_key": 1,
        "message": "Authentication success",
        "sid": frappe.session.sid,
        "api_key": user.api_key,
        "api_secret": api_generate,
        "username": user.username,
        "email": user.email,
        "base_url": frappe.utils.get_url(),
        "role_profile": role_profile
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
        suppliers = frappe.get_all("Supplier", filters={"supplier_group": "Raw Material"}, fields=["name"])
        
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



@frappe.whitelist( allow_guest=True, methods="POST" )
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


        one_time_password_doc = frappe.get_doc({
            "doctype": "One Time Password",
            "mobile_number": mobile_number,
            "one_time_password": otp
        })
        one_time_password_doc.insert(ignore_mandatory= True, ignore_permissions= True)
        frappe.db.commit()

        message = (
            f"Your OTP is {one_time_password_doc.one_time_password}."
        )
                    
        if send_sms(one_time_password_doc.mobile_number, message):
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

        first_weight_time = kwargs.get('first_weight_time')

        if first_weight_time:
            formatted_datetime = parser.parse(first_weight_time).strftime("%Y-%m-%d %H:%M:%S")


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
                "gross_time": formatted_datetime
            })
            weigh_bridge_ticket_doc.insert(ignore_mandatory=True, ignore_permissions=True)
            frappe.db.commit()
            return {'status': 200, 'message': 'Weight bridge created successfully.'}
        else:
            return {'status': 500, 'message': 'First weight time is needed.'}
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
            second_weight_time = kwargs.get('second_weight_time')
            weigh_bridge_ticket_doc  =  frappe.get_doc("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')})
            net_weight  = float(weigh_bridge_ticket_doc.total_weight) - float(kwargs.get('second_weight'))
            if second_weight_time:
                formatted_datetime = parser.parse(second_weight_time).strftime("%Y-%m-%d %H:%M:%S")

                frappe.db.set_value("Weigh Bridge Ticket", {"name": kwargs.get('weigh_bridge_ticket_number')}, {"truck_weight": kwargs.get('second_weight'), "net_weight": net_weight, "tare_time": formatted_datetime})
                frappe.db.commit()
            
                return {'status': 200, 'message': 'Second weight updated successfully.'}
            else:
                return {'status': 500, 'message': 'Second weight time is needed.'}
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
            fields=["name as weigh_brigde_ticket_no", "total_weight as first_weight", "material as raw_material", "driver_name as driver_name", "supplier", "truck_weight as second_weight"],
            filters={"workflow_state": "Draft"},
            order_by="modified desc"
        )

        if not weigh_bridge_tickets:
            return {'status': 404, 'message': 'No tickets found.'}

        for ticket in weigh_bridge_tickets:
            if ticket['second_weight'] < 1:
                ticket['workflow_state'] = "Draft"
            else:
                ticket['workflow_state'] = "Pending Forwarding to Store Clerk"

        return {'status': 200, 'ticket_data': weigh_bridge_tickets}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {'error': str(e)}, 400

    


@frappe.whitelist(methods="POST")
def rest_password(**kwargs):
    try:
        usr = kwargs.get('usr')
        new_password = kwargs.get('new_password')
        otp = kwargs.get('otp')


        if not usr or not new_password:
            return {'error': 'Missing required parameters: usr and new_password'}, 400

        if "@" in usr and "." in usr:
            user = frappe.get_doc("User", {"email": usr})
        else:
            user = frappe.get_doc("User", {"mobile_no": usr})

        if not user:
            return {'error': 'User not found'}, 404
        
        if not validate_otp_exists(usr, otp):
            return {'error': 'Invalid or expired OTP. Please try again.', 'status': 400}

      
        frappe.utils.password.update_password(user.name, new_password)
        frappe.delete_doc("One Time Password", usr)
        frappe.db.commit()
        return {'status': 200, 'message': 'Password successfully recovered.'}

    except frappe.DoesNotExistError:
        return {'error': 'User does not exist'}, 404
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Password Recovery Error: {str(e)}")
        return {'error': str(e)}, 500
    

def validate_otp_exists(usr, otp):
    try:
        return frappe.db.exists("One Time Password", {"name": usr, "one_time_password": otp})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Error in validate_otp_exists {str(e)}")
        return False


@frappe.whitelist(methods="POST")
def create_fueling_list(**kwargs):
    try:
        date = kwargs.get('date')
        routes = kwargs.get('routes', [])
        vehicle_reg_no = kwargs.get('vehicle_reg_no')
        mileage = kwargs.get('mileage')
        litres = kwargs.get('litres')
        amount = kwargs.get('amount')
        petrol_station_pos_receipt_no = kwargs.get('petrol_station_pos_receipt_no')

        if not date:
            return {'status': 500, 'message': 'Date is required.'}

        formatted_date = parser.parse(date).strftime("%Y-%m-%d")


        route_details = []

        for route in routes:
            route_details.append({
                "route": route['route']
            })

        previous_vehicle_mileage = frappe.db.get_value(
            "Fueling List",
            {"vehicle_reg_no": vehicle_reg_no, "workflow_state": "Approved"},
            ["mileage", "litres"],
            order_by="creation DESC"
        )

        liters_per_kilometer = 0
        if previous_vehicle_mileage:
            prev_mileage, prev_litres = previous_vehicle_mileage
            if mileage is not None and prev_mileage is not None and litres:
                mileage_covered = mileage - prev_mileage
                if mileage_covered > 0 and prev_litres:
                    liters_per_kilometer = litres / mileage_covered

        fueling_list_doc = frappe.get_doc({
            "doctype": "Fueling List",
            "date": formatted_date,
            "vehicle_reg_no": vehicle_reg_no,
            "petrol_station_pos_receipt_no": petrol_station_pos_receipt_no,
            "routes": route_details,
            "mileage": mileage,
            "litres": litres,
            "amount": amount,
            "liters_per_kilometer": liters_per_kilometer
        })
        
        fueling_list_doc.insert(ignore_mandatory=True, ignore_permissions=True)
        frappe.db.commit()

        return {'status': 200, 'message': 'Fueling List created successfully.'}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}'}





@frappe.whitelist( methods="GET" )
def get_fueling_list():
    try:

        fueling_lists = frappe.db.get_all(
            "Fueling List",
            fields=["date", "vehicle_reg_no", "petrol_station_pos_receipt_no", "route", "mileage", "litres", "amount", "workflow_state as status", "name as fueling_list_name", "liters_per_kilometer"],
            filters={"workflow_state": ["in", ["Pending Approval", "Draft"]]},
            order_by="modified desc"
        )

        if not fueling_lists:
            return {'status': 404, 'message': 'No fuel list found.'}

        return {'status': 200, 'fueling_lists': fueling_lists}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {'error': str(e)}, 400


@frappe.whitelist(methods="GET")
def get_fueling_list():
    try:
        fueling_lists_sql = frappe.db.sql("""
            SELECT
                FL.name AS fueling_list_name,
                FL.date AS date,
                FL.vehicle_reg_no AS vehicle_reg_no,
                FL.petrol_station_pos_receipt_no AS petrol_station_pos_receipt_no,
                FL.mileage AS mileage,
                FL.litres AS litres,
                FL.amount AS amount,
                FL.liters_per_kilometer AS liters_per_kilometer,
                FL.workflow_state AS status,
                RD.route AS route
            FROM
                `tabFueling List` FL
            LEFT JOIN
                `tabRoute Details` RD ON RD.parent = FL.name
            WHERE
                FL.workflow_state IN ('Pending Approval', 'Draft')
        """, as_dict=True)

        fueling_records = {}
        for row in fueling_lists_sql:
            fueling_list_name = row["fueling_list_name"]

            if fueling_list_name not in fueling_records:
                fueling_records[fueling_list_name] = {
                    "fueling_list_name": fueling_list_name,
                    "date": row["date"],
                    "vehicle_reg_no": row["vehicle_reg_no"],
                    "petrol_station_pos_receipt_no": row["petrol_station_pos_receipt_no"],
                    "mileage": row["mileage"],
                    "liters_per_kilometer": row["liters_per_kilometer"],
                    "status": row["status"],
                    "litres": row["litres"],
                    "amount": row["amount"],
                    "routes": []
                }

            if row["route"]:
                fueling_records[fueling_list_name]["routes"].append({"route": row["route"]})

        fueling_lists = list(fueling_records.values())

        return {
            "status": 200,
            "fueling_lists": fueling_lists
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"status": 500, "error": str(e)}






@frappe.whitelist(methods="POST")
def update_fueling_list(**kwargs):
    try:
        fueling_list_name = kwargs.get('fueling_list_name')
        if not fueling_list_name:
            return {'status': 400, 'message': 'The "fueling_list_name" field is required to update the Fueling List.'}

        # Fetch the existing Fueling List document
        fueling_list_doc = frappe.get_doc("Fueling List", fueling_list_name)

        # Extract incoming data
        date = kwargs.get('date')
        vehicle_reg_no = kwargs.get('vehicle_reg_no')
        mileage = kwargs.get('mileage')
        litres = kwargs.get('litres')
        amount = kwargs.get('amount')
        routes = kwargs.get('routes')
        petrol_station_pos_receipt_no = kwargs.get('petrol_station_pos_receipt_no')

        # Update basic fields if provided
        if date:
            fueling_list_doc.date = parser.parse(date).strftime("%Y-%m-%d")

        if vehicle_reg_no:
            fueling_list_doc.vehicle_reg_no = vehicle_reg_no

        if petrol_station_pos_receipt_no:
            fueling_list_doc.petrol_station_pos_receipt_no = petrol_station_pos_receipt_no

        if mileage:
            fueling_list_doc.mileage = mileage

        if litres:
            fueling_list_doc.litres = litres

        if amount:
            fueling_list_doc.amount = amount

        if routes:
            fueling_list_doc.set("routes", [])
            for route in routes:
                fueling_list_doc.append("routes", {
                    "route": route.get('route')
                })

        previous_vehicle_data = frappe.db.get_value(
            "Fueling List",
            {"vehicle_reg_no": vehicle_reg_no, "workflow_state": "Approved"},
            ["mileage", "litres"],
            order_by="creation DESC"
        )

        liters_per_kilometer = 0
        if previous_vehicle_data:
            prev_mileage, prev_litres = previous_vehicle_data
            if mileage and prev_mileage and prev_litres:
                mileage_covered = mileage - prev_mileage
                liters_per_kilometer = mileage_covered / prev_litres if prev_litres > 0 else 0

        fueling_list_doc.liters_per_kilometer = liters_per_kilometer

        fueling_list_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {'status': 200, 'message': 'Fueling List updated successfully.'}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        return {'status': 500, 'message': f'An error occurred: {str(e)}'}





@frappe.whitelist( methods="POST" )
def forward_fuel_list_for_approval(**kwargs):
    try:
        if frappe.db.exists("Fueling List", {"name": kwargs.get('fuel_list_number')}):

            frappe.db.set_value("Fueling List", {"name": kwargs.get('fuel_list_number')}, {"workflow_state": "Pending Approval"})
            frappe.db.commit()
            
            return {'status': 200, 'message': 'Record forwarded successfully.'}
        else:
            return {'error': 'Record does not exist'}, 404

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}',}
    


@frappe.whitelist( methods="POST" )
def create_expense(**kwargs):
    try:
        expense_items = kwargs.get('expense_items')
        date = kwargs.get('date')
        if date:
            formatted_date = parser.parse(date).strftime("%Y-%m-%d")

            expense_details = []
            total_amount = 0

            for expense_item in expense_items:
                expense_details.append({
                    "item": expense_item['item'],
                    "amount": expense_item['amount'],
                })
                total_amount += float(expense_item['amount'])

            expense_doc = frappe.get_doc({
                "doctype": "Expense",
                "expense_type": kwargs.get('expense_type'),
                "supplier": kwargs.get('supplier'),
                "expense_details": expense_details,
                "description": kwargs.get('description'),
                "date": formatted_date,
                "total_amount": total_amount
            })
            expense_doc.insert(ignore_mandatory=True, ignore_permissions=True)
            frappe.db.commit()
            return {'status': 200, 'message': 'Expense created successfully.'}
        else:
            return {'status': 500, 'message': 'Date is needed.'}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}'}



@frappe.whitelist(methods="GET")
def get_expenses():
    try:
        expense_data = frappe.db.sql("""
            SELECT
                E.name AS expense_name,
                E.expense_type AS expense_type,
                E.supplier AS supplier,
                E.date AS date,
                E.total_amount AS total_amount,
                ED.item AS item,
                ED.amount AS item_amount,
                E.workflow_state AS status
            FROM
                `tabExpense Details` ED
            JOIN
                `tabExpense` E ON ED.parent = E.name
            WHERE
                E.workflow_state IN ('Pending Approval', 'Draft')
        """, as_dict=True)

        expenses = {}
        for row in expense_data:
            expense_name = row.pop("expense_name")
            
            if expense_name not in expenses:
                expenses[expense_name] = {
                    "expense_type": row["expense_type"],
                    "supplier": row["supplier"],
                    "date": row["date"],
                    "total_amount": row["total_amount"],
                    "status": row["status"],
                    "details": []
                }

            expenses[expense_name]["details"].append({
                "item": row["item"],
                "amount": row["item_amount"]
            })

        expenses_list = [
            {"expense_name": name, **details}
            for name, details in expenses.items()
        ]

        return {
            "status": 200,
            "expenses": expenses_list
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"error": str(e)}, 400



@frappe.whitelist( methods="GET" )
def get_expense_suppliers():
    try:
        suppliers = frappe.get_all("Supplier", filters={"supplier_group": "Expense"}, fields=["name"])
        
        supplier_list = [{"supplier": supplier["name"]} for supplier in suppliers]
        
        return {'status': 200, 'suppliers': supplier_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400
    


@frappe.whitelist( methods="POST" )
def forward_expense_for_approval(**kwargs):
    try:
        if frappe.db.exists("Expense", {"name": kwargs.get('expense_name')}):

            frappe.db.set_value("Expense", {"name": kwargs.get('expense_name')}, {"workflow_state": "Pending Approval"})
            frappe.db.commit()
            
            return {'status': 200, 'message': 'Record forwarded successfully.'}
        else:
            return {'error': 'Record does not exist'}, 404
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}',}
    

@frappe.whitelist( methods="GET" )
def get_expense_types():
    try:
        expense_types = frappe.get_all("Expense Type", fields=["name"])
        
        expense_type_list = [{"expense_type": expense_type["name"]} for expense_type in expense_types]
        
        return {'status': 200, 'expense_types': expense_type_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400


@frappe.whitelist( methods="GET" )
def get_expense_items():
    try:
        expense_items = frappe.get_all("Item", filters={"item_group": "Expense"}, fields=["name"]) 
        expense_item_list = [{"expense_item": expense_item["name"]} for expense_item in expense_items]
        
        return {'status': 200, 'expense_item_list': expense_item_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400



@frappe.whitelist( methods="GET" )
def get_routes():
    try:
        routes = frappe.get_all("Route", fields=["name"])
        
        route_list = [{"route": route["name"]} for route in routes]
        
        return {'status': 200, 'routes': route_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400



@frappe.whitelist( methods="GET" )
def get_customers():
    try:
        customers = frappe.get_all("Customer", fields=["name"])
        
        customer_list = [{"customer": customer["name"]} for customer in customers]
        
        return {'status': 200, 'customer': customer_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400


@frappe.whitelist( methods="GET" )
def get_sales_items():
    try:
        items = frappe.get_all("Item", filters={"item_group": "Products"}, fields=["name"])
        
        item_list = [{"item": item["name"]} for item in items]
        
        return {'status': 200, 'item': item_list}

    except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"{e}")
            return {'error': str(e)}, 400



@frappe.whitelist(methods="POST")
def create_sales_order(**kwargs):
    try:
        sales_order_items = kwargs.get('sales_order_items')
        delivery_date = kwargs.get('delivery_date')
        customer = kwargs.get('customer')
        sales_order_name = kwargs.get('sales_order_name')

        if not delivery_date:
            return {'status': 500, 'message': 'Date is needed.'}

        formatted_date = parser.parse(delivery_date).strftime("%Y-%m-%d")
        sales_order_items_details = []
        total_amount = 0

        credit_balance, credit_limit_set = check_customer_credit_limit(customer)

        if not credit_limit_set:
            return {'status': 500, 'message': 'Customer credit limit is not set. Please set a credit limit first.'}

        for sales_order_item in sales_order_items:
            rate = frappe.db.get_value("Item Price", 
                {"item_code": sales_order_item['item_code'], "price_list": "Standard Selling"}, 
                "price_list_rate") or 0
            line_total = sales_order_item['quantity'] * rate
            total_amount += line_total

            sales_order_items_details.append({
                "item_code": sales_order_item['item_code'],
                "delivery_date": formatted_date,
                "qty": sales_order_item['quantity'],
                "rate": rate
            })

        if credit_balance < total_amount:
            exceeded_amount = total_amount - credit_balance
            return {'status': 500, 'message': f'Sales amount exceeds customer credit balance by {exceeded_amount:,.2f}.'}


        if sales_order_name:
            if frappe.db.exists("Sales Order", {"name": sales_order_name}):
                sales_order_doc = frappe.get_doc("Sales Order", sales_order_name)
                sales_order_doc.delivery_date = formatted_date
                sales_order_doc.customer = customer

                sales_order_doc.items = [] 

                for item in sales_order_items_details:
                    sales_order_doc.append("items", item)

                sales_order_doc.save(ignore_permissions=True)
                frappe.db.commit()

                return {'status': 200, 'message': 'Sales order updated successfully.'}
            else:
                return {'status': 404, 'message': 'Sales order not found.'}

        else:

            sales_order_doc = frappe.get_doc({
                "doctype": "Sales Order",
                "customer": customer,
                "delivery_date": formatted_date,
                "items": sales_order_items_details
            })

            sales_order_doc.insert(ignore_mandatory=True, ignore_permissions=True)
            frappe.db.commit()
            return {'status': 200, 'message': 'Sales order created successfully.'}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}'}




def check_customer_credit_limit(customer):
    try:
        credit_limit = frappe.db.get_value("Customer Credit Limit", {"parent": customer}, "credit_limit")
        
        if credit_limit is None:
            return 0, False

        outstanding_customer_amount = frappe.db.sql(
            """
            SELECT SUM(outstanding_amount) 
            FROM `tabSales Invoice` 
            WHERE customer = %s AND docstatus = 1
            """, (customer,))[0][0] or 0
        
        credit_balance = credit_limit - outstanding_customer_amount
        return credit_balance, True
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return 0, False




@frappe.whitelist(methods="GET")
def get_sales_orders():
    try:
        sales_orders = {}
        
        sales_orders_data = frappe.db.sql("""
            SELECT
                SO.name AS sales_order_name,
                SO.customer AS customer,
                SO.delivery_date AS delivery_date,
                SO.rounded_total AS total_amount,
                SO.workflow_state AS status,
                SOI.item_code AS item_code,
                SOI.qty AS quantity,
                SOI.rate AS unit_price,
                SOI.amount AS amount
            FROM
                `tabSales Order` SO
            JOIN
                `tabSales Order Item` SOI ON SOI.parent = SO.name
            WHERE
                SO.docstatus != 2
        """, as_dict=True)

        for row in sales_orders_data:
            sales_order_name = row.pop("sales_order_name")
            
            if sales_order_name not in sales_orders:
                sales_orders[sales_order_name] = {
                    "customer": row["customer"],
                    "delivery_date": row["delivery_date"],
                    "total_amount": row["total_amount"],
                    "status": row["status"],
                    "items": []
                }

            sales_orders[sales_order_name]["items"].append({
                "item_code": row["item_code"],
                "quantity": row["quantity"],
                "unit_price": row["unit_price"],
                "amount": row["amount"]
            })

        sales_orders_list = [
            {"sales_order_name": name, **details}
            for name, details in sales_orders.items()
        ]

        return {
            "status": 200,
            "sales_orders": sales_orders_list
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"error": str(e)}, 400



@frappe.whitelist( methods="POST" )
def forward_sales_order_for_approval(**kwargs):
    try:
        if frappe.db.exists("Sales Order", {"name": kwargs.get('sales_order_name')}):

            frappe.db.set_value("Sales Order", {"name": kwargs.get('sales_order_name')}, {"workflow_state": "Pending Approval by Store Manager"})
            frappe.db.commit()
            
            return {'status': 200, 'message': 'Sales Order forwarded successfully.'}
        else:
            return {'status': 404, 'message': 'Sales Order does not exist'}    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}'}



@frappe.whitelist( methods="POST" )
def confirm_order_receival(**kwargs):
    try:
        sales_order_name = kwargs.get('sales_order_name')

        if not sales_order_name:
            return {'status': 400, 'message': 'Sales Order name is required.'}

        if frappe.db.exists("Sales Order", {"name": sales_order_name}):
            sales_order_doc = frappe.get_doc("Sales Order", sales_order_name)
            if sales_order_doc.docstatus == 1:
                return {'status': 200, 'message': 'Sales Order is already submitted.'}
            sales_order_doc.submit()
            frappe.db.set_value("Sales Order", sales_order_name, "workflow_state", "Completed")
            frappe.db.commit()

            return {'status': 200, 'message': 'Sales Order submitted successfully and marked as Completed.'}

        else:
            return {'status': 404, 'message': 'Sales Order does not exist'}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{str(e)}")
        return {'status': 500, 'message': f'An error occurred: {str(e)}'}
