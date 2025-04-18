import threading
from config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN
from inflow import Inflow
from salesforce import SalesForce
import json
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import Slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
sf = SalesForce()
inflow = Inflow()
inflow.subscribe_to_salesorder_webhook()
slack_app = App(token=SLACK_BOT_TOKEN)
slack = Slack()


def poll_salesforce_for_updated_orders():
    body, is_change_in_order_status = sf.get_latest_order_status_update()
    if is_change_in_order_status == True:
        is_successful, order_number, message = inflow.create_inflow_order(body)
        if is_successful:
            slack.send_inflow_order_created_message(order_number)
        else:
            slack.send_inflow_order_created_error_message(order_number, message)


def poll_salesforce_for_customer_creation():
    body, is_new_customer_created = sf.get_latest_customer()
    if is_new_customer_created == True:
        is_successful, name, message = inflow.create_inflow_customer(body)
        if is_successful:
            slack.send_inflow_customer_created_message(name)
        else:
            slack.send_inflow_customer_created_error_message(name, message)


def poll_inflow_for_product_update():
    body, is_update_in_product = inflow.get_inflow_latest_product_update()
    if is_update_in_product == True:
        is_successful, name, message = sf.create_product(body)
        if is_successful:
            slack.send_salesforce_product_created_message(name)
        else:
            slack.send_salesforce_product_created_error_message(name, message)


def poll():
    poll_salesforce_for_updated_orders()
    poll_salesforce_for_customer_creation()
    poll_inflow_for_product_update()


scheduler = BackgroundScheduler()
scheduler.add_job(poll, "interval", minutes=1)
scheduler.start()

salesforce_orders_to_update_set = set()
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
            tracking_numbers = ""
            if len(response["shipLines"]) == 1:
                tracking_numbers = response["shipLines"][0]["trackingNumber"]
            else:
                for shipline in response["shipLines"]:
                    tracking_numbers = (
                        tracking_numbers + shipline["trackingNumber"] + ","
                    )
                tracking_numbers = tracking_numbers[:-1]
            order_id = response["customFields"]["custom1"]
            order_number = response["orderNumber"]
            if order_number in salesforce_orders_to_update_set:
                return {"status": 200}
            else:
                salesforce_orders_to_update_set.add(order_number)
            is_successful, message = sf.update_order_status(
                order_id, tracking_numbers, order_number
            )
            if is_successful:
                slack.send_salesforce_order_updated_message(order_number)
            else:
                slack.send_salesforce_order_updated_error_message(order_number, message)
    return {"status": 200}


def start_slack():
    SocketModeHandler(slack_app, SLACK_APP_TOKEN).start()


def start_slack_and_flask():
    slack_thread = threading.Thread(target=start_slack)
    slack_thread.start()
    app.run(port=5000, use_reloader=False, threaded=True)


if __name__ == "__main__":
    start_slack_and_flask()
