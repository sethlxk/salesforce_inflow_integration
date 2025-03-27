from inflow import Inflow
from salesforce import SalesForce
import json
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
sf = SalesForce()
inflow = Inflow()
inflow.subscribe_to_salesorder_webhook()


def poll_salesforce_for_updated_orders():
    body, is_change_in_order_status = sf.get_latest_order_status_update()
    if is_change_in_order_status == True:
        inflow.create_inflow_order(body)


def poll_salesforce_for_customer_creation():
    body, is_new_customer_created = sf.get_latest_customer()
    if is_new_customer_created == True:
        inflow.create_inflow_customer(body)


def poll_inflow_for_product_update():
    body, is_update_in_product = inflow.get_inflow_latest_product_update()
    if is_update_in_product == True:
        sf.create_product(body)


def poll():
    poll_salesforce_for_updated_orders()
    poll_salesforce_for_customer_creation()
    poll_inflow_for_product_update()


scheduler = BackgroundScheduler()
scheduler.add_job(poll, "interval", minutes=1)
scheduler.start()


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_data = request.data.decode("utf-8")
    try:
        data = json.loads(raw_data)
        logger.info(f"Received JSON data: {json.dumps(data, indent=2)}")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON received: {raw_data}")
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
            order_id = response["customFields"]["custom1"]
            sf.update_order_status(order_id)
    return {"status": 200}


if __name__ == "__main__":
    app.run(port=5000)
