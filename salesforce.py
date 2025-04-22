from simple_salesforce import Salesforce
from config import SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN, SALESFORCE_USERNAME
from datetime import datetime, timedelta
import pandas as pd
import pytz
import uuid
from inflow import Inflow
import logging
import requests
from utils import variables_nonetype_conversion_to_string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SalesForce:
    def __init__(self) -> None:
        self.sf = Salesforce(
            username=SALESFORCE_USERNAME,
            password=SALESFORCE_PASSWORD,
            security_token=SALESFORCE_SECURITY_TOKEN,
        )

    def get_latest_order_status_update(self):
        try:
            now = datetime.now(pytz.utc)
            one_minute_ago = now - timedelta(minutes=1)
            one_minute_ago_str = (
                one_minute_ago.strftime("%Y-%m-%dT%H:%M:%S.")
                + f"{one_minute_ago.microsecond // 1000:03d}Z"
            )
            query = f"""
            SELECT Id, AccountId, OrderNumber, Name, Shipping_Date__c, ShippingAddress, ShipToContactId 
            FROM Order 
            WHERE LastModifiedDate >= {one_minute_ago_str}
            AND Status = 'Approved to Ship'
            """
            results = self.sf.query(query)["records"]
            results_df = pd.DataFrame.from_dict(results)
            if len(results_df) == 0:
                logger.info("No latest status updates in orders")
                return {}, False
            results_df.drop("attributes", axis=1, inplace=True)
            account_id = results_df.iloc[0]["AccountId"]
            company_name, website = self.get_company_details(account_id)
            contact_id = results_df.iloc[0]["ShipToContactId"]
            if contact_id is None:
                contact_email, contact_name, contact_phone = "", "", ""
            else:
                contact_email, contact_name, contact_phone = (
                    self.get_customer_contact_details(contact_id)
                )
            inflow = Inflow()
            inflow_customers = inflow.get_inflow_customers()
            customer_id = ""
            if company_name in inflow_customers:
                customer_id = inflow_customers[company_name]
            orderNumber = results_df.iloc[0]["OrderNumber"]
            shipping_address = results_df.iloc[0]["ShippingAddress"]
            order_remarks = ""
            if shipping_address is None:
                address, city, country, postalCode, state = "Hand Carry", "", "", "", ""
                order_remarks = "Hand Carry"
            else:
                address = shipping_address["street"]
                city = shipping_address["city"]
                country = shipping_address["country"]
                postalCode = shipping_address["postalCode"]
                state = shipping_address["state"]
            possible_nonetype_array = [
                website,
                contact_email,
                contact_name,
                contact_phone,
                address,
                city,
                country,
                postalCode,
                state,
            ]
            (
                website,
                contact_email,
                contact_name,
                contact_phone,
                address,
                city,
                country,
                postalCode,
                state,
            ) = variables_nonetype_conversion_to_string(*possible_nonetype_array)
            order_id = results_df.iloc[0]["Id"]
            salesforce_order_products = self.get_order_products(order_id)
            inflow_products = inflow.get_inflow_products()
            salesOrderId = f"{uuid.uuid4()}"
            linesArray = []
            for sf_k in salesforce_order_products:
                matches = [key for key in inflow_products if sf_k in key]
                for match in matches:
                    salesOrderLineId = f"{uuid.uuid4()}"
                    lineBody = {
                        "productId": inflow_products[match]["productId"],
                        "salesOrderLineId": salesOrderLineId,
                        "quantity": {
                            "uomQuantity": str(
                                salesforce_order_products[sf_k]["quantity"]
                            )
                        },
                        "unitPrice": str(salesforce_order_products[sf_k]["listPrice"]),
                    }
                    linesArray.append(lineBody)
            body = {
                "salesOrderId": salesOrderId,
                "contactName": contact_name,
                "customer": {"customerId": customer_id, "website": website},
                "customerId": customer_id,
                "customFields": {"custom1": order_id},
                "email": contact_email,
                "inventoryStatus": "Started",
                "invoicedDate": None,
                "isCompleted": False,
                "lines": linesArray,
                "orderDate": now.strftime("%Y-%m-%d"),
                "orderNumber": f"SO-{orderNumber}",
                "orderRemarks": order_remarks,
                "phone": contact_phone,
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
            }
            return body, True
        except Exception as e:
            logger.error(f"Error getting latest order status update: {e}")
            return {}, False

    def get_company_details(self, account_id):
        query = f""" SELECT Name, Website FROM Account 
        WHERE Id = '{account_id}'"""
        results = self.sf.query(query)["records"]
        results_df = pd.DataFrame.from_dict(results)
        results_df.drop("attributes", axis=1, inplace=True)
        name = results_df.iloc[0]["Name"]
        website = results_df.iloc[0]["Website"]
        return name, website

    def get_order_products(self, order_id):
        query = f""" SELECT ListPrice, Quantity, Product2Id, Product_Code__c, OrderId FROM OrderItem 
        WHERE OrderId = '{order_id}'"""
        results = self.sf.query(query)["records"]
        order_products_df = pd.DataFrame.from_dict(results)
        order_products_df.drop("attributes", axis=1, inplace=True)
        order_products_df = order_products_df.groupby(
            "Product_Code__c", as_index=False
        ).agg(
            {
                "Quantity": "sum",
                "ListPrice": "first",
                "Product2Id": "first",
                "OrderId": "first",
            }
        )
        query = f""" SELECT Id, InFlow__c From Product2 WHERE InFlow__c = True"""
        results = self.sf.query(query)["records"]
        products_df = pd.DataFrame.from_dict(results)
        products_df.drop("attributes", axis=1, inplace=True)
        results_df_final = pd.merge(
            products_df,
            order_products_df,
            left_on="Id",
            right_on="Product2Id",
            how="inner",
        )
        order_products_dict = {}
        for row in results_df_final.itertuples():
            order_products_dict[row.Product_Code__c] = {
                "listPrice": row.ListPrice,
                "quantity": row.Quantity,
                "productId": row.Product2Id,
            }
        return order_products_dict

    def update_order_status(self, order_id, tracking_numbers, order_number):
        order_data = {"Status": "Shipped", "Tracking_Number_s__c": tracking_numbers}
        try:
            url = f"https://{self.sf.sf_instance}/services/data/v59.0/sobjects/Order/{order_id}"
            headers = {
                "Authorization": f"Bearer {self.sf.session_id}",
                "Content-Type": "application/json",
            }
            response = requests.patch(url, headers=headers, json=order_data, timeout=10)
            if response.status_code in [200, 204]:
                logger.info(f"Order {order_number} status updated to 'Shipped'.")
                return True, response.text
            else:
                logger.error(
                    f"Failed to update order {order_number}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False, response.text
        except Exception as e:
            logger.exception(f"Error updating order {order_number}: {e}")

    def get_latest_customer(self):
        try:
            now = datetime.now(pytz.utc)
            one_minute_ago = now - timedelta(minutes=1)
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
                logger.info("No latest creation of customers")
                return {}, False
            results_df.drop("attributes", axis=1, inplace=True)
            name = results_df.iloc[0]["Name"]
            customerId = uuid.uuid4()
            body = {"name": name, "customerId": f"{customerId}"}
            return body, True
        except Exception as e:
            logger.error(f"Error getting latest customer creation: {e}")
            return {}, False

    def create_product(self, body):
        product_data = {
            "Name": body["name"],
            "List_Price__c": body["listPrice"],
            "ProductCode": body["sku"],
        }
        try:
            self.sf.Product2.create(product_data)
            name = body["name"]
            logger.info(f"Product {name} created.")
            return True, name, "success"
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return False, name, e

    def get_customer_contact_details(self, contact_id):
        query = f"""
        SELECT Email, Name, Phone
        FROM Contact 
        WHERE Id = '{contact_id}'
        """
        results = self.sf.query(query)["records"]
        results_df = pd.DataFrame.from_dict(results)
        email = results_df.iloc[0]["Email"]
        name = results_df.iloc[0]["Name"]
        phone = results_df.iloc[0]["Phone"]
        return email, name, phone
