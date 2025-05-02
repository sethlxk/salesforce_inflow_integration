import requests
import json
from config import (
    INFLOW_BASE_URL,
    INFLOW_COMPANY_ID,
    INFLOW_TOKEN,
    INFLOW_WEBHOOK_SUBSCRIPTION_ID,
    SERVER_URL,
)
from datetime import datetime
import pytz
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Inflow:
    def __init__(self) -> None:
        self.url = f"{INFLOW_BASE_URL}/{INFLOW_COMPANY_ID}"
        self.request_headers = {
            "Authorization": f"Bearer {INFLOW_TOKEN}",
            "Accept": "application/json;version=2024-03-12",
        }
        self.webhook_subscription_id = INFLOW_WEBHOOK_SUBSCRIPTION_ID
        self.products_state = self.get_inflow_products()

    def get_inflow_products(self):
        try:
            url = f"{self.url}/products"
            products_dict = {}
            count = 100
            after = None
            session = requests.Session()
            while True:
                params = {
                    "count": count,
                    "after": after,
                    "includeCount": True,
                }
                response = session.get(
                    url, headers=self.request_headers, params=params, timeout=10
                ).json()
                if not response:
                    break
                for r in response:
                    products_dict[r["sku"]] = {
                        "name": r["name"],
                        "productId": r["productId"],
                        "timestamp": r["lastModifiedDateTime"],
                        "isFinished": r["customFields"]["custom2"],
                        "unitPrice": r["customFields"]["custom3"],
                        "activeRevision": r["customFields"]["custom6"]
                    }
                if len(response) < count:
                    break
                after = response[-1]["productId"]
            return products_dict
        except Exception as e:
            logger.error(f"Error getting inflow products: {e}")

    def subscribe_to_salesorder_webhook(self):
        try:
            WEBHOOK_URL = f"{SERVER_URL}/webhook"
            WEBHOOK_URL_INFLOW = f"{self.url}/webhooks"
            webhook_data = {
                "url": WEBHOOK_URL,
                "events": ["salesorder.updated"],
                "webHookSubscriptionId": self.webhook_subscription_id,
            }
            response = requests.put(
                WEBHOOK_URL_INFLOW,
                headers=self.request_headers,
                data=json.dumps(webhook_data),
            )
            if response.status_code == 200:
                logger.info("Successfully subscribed to salesorder.updated webhook.")
                logger.info(f"Response: {response.json()}")
            else:
                logger.error("Failed to subscribe to webhook.")
                logger.error(f"Status Code: {response.status_code}")
                logger.error(f"Error: {response.json()}")
        except Exception as e:
            logger.error(f"Error subscribing to webhook: {e}")

    def get_inflow_order(self, salesOrderId):
        try:
            url = f"{self.url}/sales-orders/{salesOrderId}?include=shipLines"
            payload = {}
            response = requests.request(
                "GET", url, headers=self.request_headers, data=payload
            ).json()
            return response
        except Exception as e:
            logger.error(f"Error getting inflow order: {e}")

    def create_inflow_order(self, body):
        try:
            url = f"{self.url}/sales-orders"
            payload = json.dumps(body)
            response = requests.request(
                "PUT", url, headers=self.request_headers, data=payload
            )
            order_number = body["orderNumber"]
            if response.status_code == 200:
                logger.info(f"Inflow order successfully created: {order_number}")
                return True, order_number, response.content
            else:
                logger.error(f"Inflow order was not created: {response.status_code}")
                logger.error(f"Inflow order was not created: {response.content}")
                return False, order_number, response.content
        except Exception as e:
            logger.error(f"Error creating inflow order: {e}")

    def create_inflow_customer(self, body):
        try:
            url = f"{self.url}/customers"
            payload = json.dumps(body)
            response = requests.request(
                "PUT", url, headers=self.request_headers, data=payload
            )
            name = body["name"]
            if response.status_code == 200:
                logger.info(f"Inflow customer successfully created: {name}")
                return True, name, response.content
            else:
                logger.error(f"Inflow customer was not created: {response.status_code}")
                logger.error(f"Inflow customer was not created: {response.content}")
                return False, name, response.content
        except Exception as e:
            logger.error(f"Error creating inflow customer: {e}")

    def get_inflow_customers(self):
        try:
            url = f"{self.url}/customers"
            customers_dict = {}
            count = 100
            after = None
            session = requests.Session()
            while True:
                params = {
                    "count": count,
                    "after": after,
                    "includeCount": True,
                }
                response = session.get(
                    url, headers=self.request_headers, params=params, timeout=10
                ).json()
                if not response:
                    break
                for r in response:
                    customers_dict[r["name"]] = r["customerId"]
                if len(response) < count:
                    break
                after = response[-1]["customerId"]
            return customers_dict
        except Exception as e:
            logger.error(f"Error in getting inflow customers: {e}")

    def get_inflow_latest_product_update(self):
        try:
            products_dict = self.get_inflow_products()
            now = datetime.now(pytz.utc)
            body = {}
            for k, v in products_dict.items():
                ts = v["timestamp"]
                if len(ts) == 31:
                    trimmed_iso_str = ts[:25] + "0" + ts[-6:]
                else:
                    trimmed_iso_str = ts[:26] + ts[-6:]
                ts = datetime.fromisoformat(trimmed_iso_str)
                time_difference = now - ts
                if (
                    self.products_state[k]["isFinished"] == ""
                    and v["isFinished"] == "Yes"
                    and time_difference.total_seconds() <= 60
                ):
                    body = {"name": v["name"], "listPrice": v["unitPrice"], "sku": k}
                    self.products_state[k]["isFinished"] = "Yes"
                    return body, True
            logger.info("No latest creation of finished products")
            return body, False
        except Exception as e:
            logger.error(f"Error in getting latest inflow product update: {e}")
