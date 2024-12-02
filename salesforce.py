from simple_salesforce import Salesforce
from config import SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN, SALESFORCE_USERNAME
import datetime
import pandas as pd
import pytz
import uuid
from inflow import Inflow


class SalesForce:
    def __init__(self) -> None:
        self.sf = Salesforce(
            username=SALESFORCE_USERNAME,
            password=SALESFORCE_PASSWORD,
            security_token=SALESFORCE_SECURITY_TOKEN,
        )
        self.order_id = None

    def get_latest_order_status_update(self):
        try:
            now = datetime.datetime.now(pytz.utc)  # Ensure UTC timezone
            five_minutes_ago = now - datetime.timedelta(minutes=1)
            # Format the time in ISO 8601 format (Salesforce uses this format)
            five_minutes_ago_str = (
                five_minutes_ago.strftime("%Y-%m-%dT%H:%M:%S.")
                + f"{five_minutes_ago.microsecond // 1000:03d}Z"
            )
            query = f"""
            SELECT Id, AccountId, OrderNumber, Name, Shipping_Date__c, ShippingAddress, ShipToContactId, TotalAmount 
            FROM Order 
            WHERE LastModifiedDate >= {five_minutes_ago_str}
            AND Status = 'Approved to Ship'
            """
            results = self.sf.query(query)["records"]
            results_df = pd.DataFrame.from_dict(results)
            if len(results_df) == 0:
                print("No latest status updates in orders")
                return {}, False
            results_df.drop("attributes", axis=1, inplace=True)
            results_df = pd.DataFrame.from_dict(results)
            account_id = results_df.iloc[0]["AccountId"]
            company_name = self.get_company_name(account_id)
            inflow = Inflow()
            inflow_customers = inflow.get_inflow_customers()
            customer_id = ""
            for k,v in inflow_customers.items():
                if company_name == k:
                    customer_id = v
            orderNumber = results_df.iloc[0]["OrderNumber"]
            shipping_address = results_df.iloc[0]["ShippingAddress"]
            address = shipping_address["street"]
            city = shipping_address["city"]
            country = shipping_address["country"]
            postalCode = shipping_address["postalCode"]
            state = shipping_address["state"]
            totalAmount = results_df.iloc[0]["TotalAmount"]
            self.order_id = results_df.iloc[0]["Id"]
            inflow_products = inflow.get_inflow_products()
            salesOrderId = uuid.uuid4()
            body = {
                "salesOrderId": f"{salesOrderId}",
                "contactName": "",
                "customerId": customer_id,
                "email": "",
                "inventoryStatus": "Started",
                "invoicedDate": None,
                "isCompleted": False,
                "lines": [
                    {
                        "productId": "c5c7d68b-4a61-402e-96ed-f375a3e209c5",
                        "salesOrderLineId": f"{salesOrderId}",
                        # TODO: add product quantity and unit price
                    }
                ],
                "orderDate": "2023-11-30T00:00:00-05:00",
                "orderNumber": f"SO-{orderNumber}",
                "phone": "",
                "requestedShipDate": None,
                "shippedDate": None,
                "shippingAddress": {
                    "address1": address,
                    "city": city,
                    "state": state,
                    "country": country,
                    "postalCode": postalCode,
                    "remarks": "",
                },
                "shipRemarks": "",
                "shipToCompanyName": company_name,
                "source": "salesforce",
                "total": totalAmount,
            }
            return body, True
        except Exception as e:
            print(f"Error getting latest order status update: {e}")
            return {}, False

    def get_company_name(self, account_id):
        query = f""" SELECT Name FROM Account 
        WHERE Id = '{account_id}'"""
        results = self.sf.query(query)["records"]
        results_df = pd.DataFrame.from_dict(results)
        results_df.drop("attributes", axis=1, inplace=True)
        name = results_df.iloc[0]["Name"]
        return name

    def get_order_products(self, order_id):
        query = f""" SELECT Product_Code__c, Product2Id, Product_Name__c, OrderId FROM OrderItem 
        WHERE OrderId = '{order_id}'"""
        results = self.sf.query(query)["records"]
        results_df = pd.DataFrame.from_dict(results)
        results_df.drop("attributes", axis=1, inplace=True)
        order_products_dict = {}
        for row in results_df.itertuples():
            order_products_dict["name"] = row.Product_Name__c
            order_products_dict["sku"] = row.Product_Code__c
        return order_products_dict

    def update_order_status(self, order_id):
        order_data = {"Status": "Shipped"}
        try:
            self.sf.Order.update(order_id, order_data)
            print(f"Order {order_id} status updated to 'Shipped'.")
        except Exception as e:
            print(f"Error updating order {order_id}: {e}")
            
    def get_latest_customer(self):
        try:
            now = datetime.datetime.now(pytz.utc)  # Ensure UTC timezone
            one_minute_ago = now - datetime.timedelta(minutes=1)
            # Format the time in ISO 8601 format (Salesforce uses this format)
            one_minute_ago_str = (
                one_minute_ago.strftime("%Y-%m-%dT%H:%M:%S.")
                + f"{one_minute_ago.microsecond // 1000:03d}Z"
            )
            query = f"""
            SELECT Name 
            FROM Account 
            WHERE CreatedDate >= {one_minute_ago_str}
            """
            results = self.sf.query(query)["records"]
            results_df = pd.DataFrame.from_dict(results)
            if len(results_df) == 0:
                print("No latest creation of customers")
                return {}, False
            results_df.drop("attributes", axis=1, inplace=True)
            results_df = pd.DataFrame.from_dict(results)
            name = results_df.iloc[0]["Name"]
            customerId = uuid.uuid4()
            body = {
                "name": name,
                "customerId": f"{customerId}"
            }
            return body, True
        except Exception as e:
            print(f"Error getting latest customer creation: {e}")
            return {}, False

    def create_product(self, body):
        product_data = {"Name": body["name"], "List_Price__c": body["listPrice"]}
        try:
            self.sf.Product2.create(product_data)
            print(f"Product {body['name']} created.")
        except Exception as e:
            print(f"Error creating product: {e}")