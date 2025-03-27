from simple_salesforce import Salesforce
from config import SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN, SALESFORCE_USERNAME
from datetime import datetime, timedelta
import pandas as pd
import pytz
import uuid
from inflow import Inflow
import logging
import requests

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
            SELECT Id, AccountId, OrderNumber, Name, Shipping_Date__c, ShippingAddress, ShipToContactId, TotalAmount 
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
            results_df = pd.DataFrame.from_dict(results)
            account_id = results_df.iloc[0]["AccountId"]
            company_name = self.get_company_name(account_id)
            inflow = Inflow()
            inflow_customers = inflow.get_inflow_customers()
            customer_id = ""
            if company_name in inflow_customers:
                customer_id = inflow_customers[company_name]
            orderNumber = results_df.iloc[0]["OrderNumber"]
            shipping_address = results_df.iloc[0]["ShippingAddress"]
            address = shipping_address["street"]
            city = shipping_address["city"]
            country = shipping_address["country"]
            postalCode = shipping_address["postalCode"]
            state = shipping_address["state"]
            totalAmount = results_df.iloc[0]["TotalAmount"]
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
                "contactName": "",
                "customerId": customer_id,
                "customFields": {"custom1": order_id},
                "email": "",
                "inventoryStatus": "Started",
                "invoicedDate": None,
                "isCompleted": False,
                "lines": linesArray,
                "orderDate": now.strftime("%Y-%m-%d"),
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
            logger.error(f"Error getting latest order status update: {e}")
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
        query = f""" SELECT ListPrice, Quantity, Product2Id, Product_Code__c, OrderId FROM OrderItem 
        WHERE OrderId = '{order_id}'"""
        results = self.sf.query(query)["records"]
        order_products_df = pd.DataFrame.from_dict(results)
        order_products_df.drop("attributes", axis=1, inplace=True)
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

    def update_order_status(self, order_id):
        order_data = {"Status": "Shipped"}
        try:
            url = f"https://{self.sf.sf_instance}/services/data/v59.0/sobjects/Order/{order_id}"
            headers = {
                "Authorization": f"Bearer {self.sf.session_id}",
                "Content-Type": "application/json",
                "X-HTTP-Method-Override": "PATCH"
            }
            logger.info(url)
            logger.info(headers)
            response = requests.post(url, headers=headers, json=order_data, timeout=10)
            if response.status_code in [200, 204]:
                logger.info(f"Order {order_id} status updated to 'Shipped'.")
            else:
                logger.error(
                    f"Failed to update order {order_id}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            logger.exception(f"Error updating order {order_id}: {e}")

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
            results_df = pd.DataFrame.from_dict(results)
            name = results_df.iloc[0]["Name"]
            customerId = uuid.uuid4()
            body = {"name": name, "customerId": f"{customerId}"}
            return body, True
        except Exception as e:
            logger.error(f"Error getting latest customer creation: {e}")
            return {}, False

    def create_product(self, body):
        product_data = {"Name": body["name"], "List_Price__c": body["listPrice"]}
        try:
            self.sf.Product2.create(product_data)
            logger.info(f"Product {body['name']} created.")
        except Exception as e:
            logger.error(f"Error creating product: {e}")
