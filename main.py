import requests
from salesforce import SalesForce
import json

sf = SalesForce()
body = sf.get_latest_order()

def create_inflow_order(body):
    url = "https://cloudapi.inflowinventory.com/d9459195-8733-4198-a0a9-2e7a86dc8d99/sales-orders"
    payload = json.dumps(body)
    headers = {
    'Authorization': 'Bearer 21A50ADE0E9BC774E0535B8A4A8B5748D7CEB66EDC0484C78FFB8969FD64A676-1',
    'Accept': 'application/json;version=2024-03-12',
    }
    response = requests.request("PUT", url, headers=headers, data=payload)
    print(response.text)

create_inflow_order(body)