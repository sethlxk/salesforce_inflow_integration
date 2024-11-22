import requests
from inflow import Inflow
from salesforce import SalesForce
import json
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

sf = SalesForce()
app = Flask(__name__)

# def create_inflow_order(body):
#     url = "https://cloudapi.inflowinventory.com/d9459195-8733-4198-a0a9-2e7a86dc8d99/sales-orders"
#     payload = json.dumps(body)
#     headers = {
#     'Authorization': 'Bearer 21A50ADE0E9BC774E0535B8A4A8B5748D7CEB66EDC0484C78FFB8969FD64A676-1',
#     'Accept': 'application/json;version=2024-03-12',
#     }
#     response = requests.request("PUT", url, headers=headers, data=payload)
#     print(response.text)

# def poll_salesforce_for_updated_orders():
#     body = sf.get_latest_order()
#     create_inflow_order(body)

# scheduler = BackgroundScheduler()
# scheduler.add_job(poll_salesforce_for_updated_orders, 'interval', minutes=1)  # Run every minute
# scheduler.start()
inflow = Inflow()
inflow.subscribe_to_salesorder_webhook()

# This endpoint will be used to receive the webhook notifications
@app.route('/webhook', methods=['POST'])
def webhook():
    raw_data = request.data.decode('utf-8')
    try:
        data = json.loads(raw_data)
        print("Received JSON data", json.dumps(data, indent=2))
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    salesOrderId = data['salesOrderId']
    response = inflow.get_inflow_order(salesOrderId)
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    shippedDate = f"{response['shippedDate']}"
    if shippedDate != None:
        shippedDate = datetime.fromisoformat(shippedDate)
        time_difference = now - shippedDate
        if response['isCompleted'] == True and time_difference.total_seconds() <= 5:
            sf.update_order_status(sf.order_id)
            print('order status updated to shipped')
    # else:
    #     print(f'shipped date is None: {shippedDate}')
    return {'status': 200}
    
if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(port=5000)
