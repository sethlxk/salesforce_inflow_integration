import requests
from inflow import Inflow
from salesforce import SalesForce
import json
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

app = Flask(__name__)
sf = SalesForce()
inflow = Inflow()
inflow.subscribe_to_salesorder_webhook()


def poll_salesforce_for_updated_orders():
    body, is_change_in_order_status = sf.get_latest_order_status_update()
    if is_change_in_order_status == True:
        inflow.create_inflow_order(body)


scheduler = BackgroundScheduler()
scheduler.add_job(poll_salesforce_for_updated_orders, "interval", minutes=1)
scheduler.start()


# This endpoint will be used to receive the webhook notifications
@app.route("/webhook", methods=["POST"])
def webhook():
    raw_data = request.data.decode("utf-8")
    try:
        data = json.loads(raw_data)
        print("Received JSON data", json.dumps(data, indent=2))
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    salesOrderId = data["salesOrderId"]
    response = inflow.get_inflow_order(salesOrderId)
    est = pytz.timezone("US/Eastern")
    now = datetime.now(est)
    shippedDate = response["shippedDate"]
    if shippedDate != None:
        shippedDate = datetime.fromisoformat(f"{shippedDate}")
        time_difference = now - shippedDate
        if response["isCompleted"] == True and time_difference.total_seconds() <= 30:
            sf.update_order_status(sf.order_id)
    return {"status": 200}


if __name__ == "__main__":
    # Run the Flask app on port 5000
    app.run(port=5000)
