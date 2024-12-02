import requests
import json
from config import (
    INFLOW_BASE_URL,
    INFLOW_COMPANY_ID,
    INFLOW_TOKEN,
    INFLOW_WEBHOOK_SUBSCRIPTION_ID,
)
from datetime import datetime
import pytz


class Inflow:
    def __init__(self) -> None:
        self.url = f"{INFLOW_BASE_URL}/{INFLOW_COMPANY_ID}"
        self.request_headers = {
            "Authorization": f"Bearer {INFLOW_TOKEN}",
            "Accept": "application/json;version=2024-03-12",
        }
        self.webhook_subscription_id = INFLOW_WEBHOOK_SUBSCRIPTION_ID

    def get_inflow_products(self):
        try:
            url = f"{self.url}/products"
            products_dict = {}
            count = 100  
            after = None 
            while True:
                params = {
                    "count": count,
                    "after": after, 
                    "includeCount": True,
                }
                response = requests.get(url, headers=self.request_headers, params=params).json()
                if not response:
                    break
                for r in response:
                    products_dict[r["name"]] = {"productId": r["productId"], "timestamp": r["lastModifiedDateTime"], "isFinished": r["customFields"]["custom2"], "unitPrice": r["customFields"]["custom3"]}
                if len(response) < count:
                    break
                after = response[-1]["productId"]
            return products_dict
        except Exception as e:
            print(f"Error getting inflow products: {e}")

    def subscribe_to_salesorder_webhook(self):
        try:
            # TODO: replace with prod url when deploying
            WEBHOOK_URL = "https://9c90-76-24-26-74.ngrok-free.app/webhook"  # Replace with your actual endpoint
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
                print("Successfully subscribed to salesorder.updated webhook.")
                print("Response:", response.json())
            else:
                print("Failed to subscribe to webhook.")
                print("Status Code:", response.status_code)
                print("Error:", response.json())
        except Exception as e:
            print(f"Error subscribing to webhook: {e}")

    def get_inflow_order(self, salesOrderId):
        try:
            url = f"{self.url}/sales-orders/{salesOrderId}"
            payload = {}
            response = requests.request(
                "GET", url, headers=self.request_headers, data=payload
            ).json()
            return response
        except Exception as e:
            print(f"Error getting inflow order: {e}")

    def create_inflow_order(self, body):
        try:
            url = f"{self.url}/sales-orders"
            payload = json.dumps(body)
            response = requests.request(
                "PUT", url, headers=self.request_headers, data=payload
            )
            if response.status_code == 200:
                print("Inflow order successfully created")
            else:
                print(f"Inflow order was not created: {response.status_code}")
                print(f"Inflow order was not created: {response.content}")
        except Exception as e:
            print(f"Error creating inflow order: {e}")
            
    def create_inflow_customer(self, body):
        try:
            url = f"{self.url}/customers"
            payload = json.dumps(body)
            response = requests.request(
                "PUT", url, headers=self.request_headers, data=payload
            )
            if response.status_code == 200:
                print("Inflow customer successfully created")
            else:
                print(f"Inflow customer was not created: {response.status_code}")
                print(f"Inflow customer was not created: {response.content}")
        except Exception as e:
            print(f"Error creating inflow customer: {e}")
        
    def get_inflow_customers(self):
        try:
            url = f"{self.url}/customers"
            customers_dict = {}
            count = 100  
            after = None 
            while True:
                params = {
                    "count": count,
                    "after": after, 
                    "includeCount": True,
                }
                response = requests.get(url, headers=self.request_headers, params=params).json()
                if not response:
                    break
                for r in response:
                    customers_dict[r["name"]] = r["customerId"]
                if len(response) < count:
                    break
                after = response[-1]["customerId"]
            return customers_dict
        except Exception as e:
            print(f"Error in getting inflow customers: {e}")
    
    def get_inflow_latest_product_update(self):
        try:
            products_dict = self.get_inflow_products()
            now = datetime.now(pytz.utc)
            body = {}
            for k,v in products_dict.items():
                ts = v["timestamp"]
                if len(ts) == 31:
                    trimmed_iso_str = ts[:25] + "0" + ts[-6:]
                else:
                    trimmed_iso_str = ts[:26] + ts[-6:]  # Trim to six microseconds
                ts = datetime.fromisoformat(trimmed_iso_str)
                time_difference = now - ts
                if v['isFinished'] == "Yes" and time_difference.total_seconds() <= 60:
                    body = {
                        "name": k,
                        "listPrice": v['unitPrice']
                    }
                    return body, True
            return body, False
        except Exception as e:
            print(f"Error in getting latest inflow product update: {e}")

