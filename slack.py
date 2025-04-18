from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Slack:
    def __init__(self) -> None:
        self.client = WebClient(token=SLACK_BOT_TOKEN)
        self.channel = SLACK_CHANNEL_ID

    def send_inflow_order_created_message(self, order_number):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Inflow Order Created*: {order_number}",
                        },
                    },
                ],
                text="inflow order created message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Inflow Order created slack message: {e}")

    def send_inflow_order_created_error_message(self, order_number, error):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Error creating Inflow Order*: {order_number}\nError Message: {error}",
                        },
                    },
                ],
                text="inflow order error message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Inflow Order slack error message: {e}")

    def send_inflow_customer_created_message(self, customer):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Inflow Customer Created*: {customer}",
                        },
                    },
                ],
                text="inflow customer created message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Inflow Customer created slack message: {e}")

    def send_inflow_customer_created_error_message(self, customer, error):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Error creating Inflow Customer*: {customer}\nError Message: {error}",
                        },
                    },
                ],
                text="inflow customer error message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Inflow Customer slack error message: {e}")

    def send_salesforce_product_created_message(self, product):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Salesforce Product Created*: {product}",
                        },
                    },
                ],
                text="salesforce product created message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Salesforce product created slack message: {e}")

    def send_salesforce_product_created_error_message(self, product, error):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Error creating Salesforce Product*: {product}\nError Message: {error}",
                        },
                    },
                ],
                text="salesforce product error message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Salesforce product slack error message: {e}")

    def send_salesforce_order_updated_message(self, order_number):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Salesforce Order Updated*: {order_number}",
                        },
                    },
                ],
                text="salesforce order updated message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Salesforce order updated slack message: {e}")

    def send_salesforce_order_updated_error_message(self, order_number, error):
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Error updating Salesforce Order*: {order_number}\nError Message: {error}",
                        },
                    },
                ],
                text="salesforce order error message",
            )
        except SlackApiError as e:
            logger.error(f"Error sending Salesforce order slack error message: {e}")
