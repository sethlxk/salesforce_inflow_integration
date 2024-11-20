from simple_salesforce import Salesforce
from config import SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN, SALESFORCE_USERNAME
import datetime
import pandas as pd
import pytz

class SalesForce:
    def __init__(self) -> None:
        self.sf = Salesforce(username=SALESFORCE_USERNAME, 
                        password=SALESFORCE_PASSWORD, 
                        security_token=SALESFORCE_SECURITY_TOKEN)
    def get_latest_order(self):
        try:
            now = datetime.datetime.now(pytz.utc)  # Ensure UTC timezone
            five_minutes_ago = now - datetime.timedelta(minutes=5)
            # Convert the timestamp to your local time zone (for example, US/Pacific)
            local_timezone = pytz.timezone('US/Pacific')
            five_minutes_ago_local = five_minutes_ago.astimezone(local_timezone)
            five_minutes_ago_str = five_minutes_ago.strftime('%Y-%m-%dT%H:%M:%S.') + f"{five_minutes_ago.microsecond // 1000:03d}Z"
            query = f""" SELECT Id, AccountId, OrderNumber, Name, Shipping_Date__c, ShippingAddress, ShipToContactId, TotalAmount FROM Order WHERE CreatedDate >= {five_minutes_ago_str}"""
            results = self.sf.query(query)['records']
            results_df = pd.DataFrame.from_dict(results)
            results_df.drop('attributes', axis=1, inplace=True)
            results_df = pd.DataFrame.from_dict(results)
            shipping_address = results_df.iloc[0]['ShippingAddress']
            address = shipping_address["street"]
            city = shipping_address["city"]
            country = shipping_address["country"]
            postalCode = shipping_address["postalCode"]
            state = shipping_address["state"]
            totalAmount = results_df.iloc[0]['TotalAmount']
            body = {
                "salesOrderId": "eac030ff-883d-4cc8-b49d-f51c7d261069",
                "contactName": "",
                "customerId": "fe64ce31-cdac-47ce-a0c1-ce12883a3a96",
                "email": "",
                "inventoryStatus": "Started",
                "invoicedDate": None,
                "isCompleted": False,
                "lines": [
                    {
                        "productId": "c5c7d68b-4a61-402e-96ed-f375a3e209c5",
                        "salesOrderLineId": "eac030ff-883d-4cc8-b49d-f51c7d261069"
                    }
                ],
                "orderDate": "2023-11-30T00:00:00-05:00",
                "orderNumber": "SO-000002",
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
                "shipToCompanyName": "",
                "source": "",
                "total": totalAmount
            }
            return body
        except Exception as e:
            print(f"Error getting order: {e}")