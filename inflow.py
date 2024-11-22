import requests
import json
from config import INFLOW_BASE_URL, INFLOW_COMPANY_ID, INFLOW_TOKEN, INFLOW_WEBHOOK_SUBSCRIPTION_ID

class Inflow:
    def __init__(self) -> None:
        self.url = f"{INFLOW_BASE_URL}/{INFLOW_COMPANY_ID}"
        self.request_headers = {
            'Authorization': f'Bearer {INFLOW_TOKEN}',
            'Accept': 'application/json;version=2024-03-12'
            }
        self.webhook_subscription_id = INFLOW_WEBHOOK_SUBSCRIPTION_ID
    def get_inflow_products(self):
        try:
            url = f"{self.url}/products"
            payload = {}
            response = requests.request("GET", url, headers=self.request_headers, data=payload).json()
            products_dict = {}
            for r in response:
                products_dict['name'] = r['name']
                products_dict['sku'] = r['sku']
                products_dict['productId'] = r['productId']
            return products_dict
        except Exception as e:
            print(f"Error getting inflow products: {e}")

    def subscribe_to_salesorder_webhook(self):
        try:
            #TODO: replace with prod url when deploying
            WEBHOOK_URL = "https://9b50-76-24-26-74.ngrok-free.app/webhook"  # Replace with your actual endpoint
            WEBHOOK_URL_INFLOW = f"{self.url}/webhooks"
            webhook_data = {
                "url": WEBHOOK_URL,
                "events": ["salesorder.updated"],
                "webHookSubscriptionId": self.webhook_subscription_id
            }
            response = requests.put(WEBHOOK_URL_INFLOW, headers=self.request_headers, data=json.dumps(webhook_data))
            if response.status_code == 200:
                print("Successfully subscribed to salesorder.updated webhook.")
                print("Response:", response.json())
            else:
                print("Failed to subscribe to webhook.")
                print("Status Code:", response.status_code)
        except Exception as e:
            print(f"Error subscribing to webhook: {e}")

    def get_inflow_order(self, salesOrderId):
        try:
            url = f"{self.url}/sales-orders/{salesOrderId}"
            payload = {}
            response = requests.request("GET", url, headers=self.request_headers, data=payload).json()
            return response
        except Exception as e:
            print(f"Error getting inflow order: {e}")
