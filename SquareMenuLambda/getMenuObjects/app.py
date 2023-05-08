import json
from square.client import Client
import json
import os
import locale
import boto3
import urllib3
from botocore.exceptions import ClientError

locale.setlocale( locale.LC_ALL, 'en_US' )

aws_session_token = os.environ['AWS_SESSION_TOKEN']
creds_path = os.environ['SQUARE_ACCESS_TOKEN']

def retrieve_extension_value(url): 
    http = urllib3.PoolManager()
    url = ('http://localhost:2773' + url)
    headers = { "X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN') }
    response = http.request("GET", url, headers=headers)
    response = json.loads(response.data)   
    return response 

class MenuItem:
    def __init__(self, client, objectId, variationName=None):
        self.client = client
        self.objectId = objectId
        self.variationName = variationName
        self.price = None
        self.name = None
        self.imageUrl = None
        self.variations = {}
        self.values = {}
        self.menuObject = {}
        try:
            self.menuObjectApi = self.client.catalog.retrieve_catalog_object(object_id = self.objectId)
        except:
            print("Error")

        if self.menuObjectApi.is_success():
            self.menuObject = json.loads(self.menuObjectApi.text)

        self.name = self.menuObject['object']['item_data']['name']

        if self.menuObject['object']['item_data']['image_ids'] != []:
            self.imageUrl = self.menuItem_get_variation_imageUrl(self.menuObject['object']['item_data']['image_ids'][0])

        if self.variationName != None:
            for variation in self.menuObject['object']['item_data']['variations']:
                if variation['type'] == "ITEM_VARIATION" and "price_money" in variation['item_variation_data'] and variation['item_variation_data']['name'] == variationName:
                    self.price = locale.currency(variation['item_variation_data']['price_money']['amount'] * 0.01)
        
        self.values[0] = {'Name': self.name, 'Price': self.price, 'ImageUrl': self.imageUrl}
        self.variations = self.get_variations()

    def menuItem_get_variation_imageUrl(self,variationImageId):
        try:
            variationImage = self.client.catalog.retrieve_catalog_object(object_id = variationImageId)
        except:
            print("Error")
        if variationImage.is_success():
            variationImageUrl = json.loads(variationImage.text)['object']['image_data']['url']
            return variationImageUrl
        
    def get_variations(self):
        x = 0
        for variation in self.menuObject['object']['item_data']['variations']:
            if variation['type'] == "ITEM_VARIATION" and "price_money" in variation['item_variation_data'] and "image_ids" in variation['item_variation_data']:
                self.variations[x] = {'Name': variation['item_variation_data']['name'], 'Price': locale.currency(variation['item_variation_data']['price_money']['amount'] * 0.01), 'ImageUrl': self.menuItem_get_variation_imageUrl(variation['item_variation_data']['image_ids'][0])}
                x+=1
        return self.variations


def lambda_handler(event, context):

    if os.environ.get("AWS_SAM_LOCAL") != "true" and os.environ.get("AWS_EXECUTION_ENV") != None:
        secrets_url = ('/systemsmanager/parameters/get?withDecryption=true&name=' + creds_path)
        client = Client(
            access_token=retrieve_extension_value(secrets_url)['Parameter']['Value'],
            environment='production')
    else:
        client = Client(
            access_token=os.environ['SQUARE_ACCESS_TOKEN'],
            environment='production')
    
    if 'queryStringParameters' in event and 'variationName' in event['queryStringParameters'] and 'objectId' in event['queryStringParameters']:
        returnData = MenuItem(client, event["queryStringParameters"]['objectId'], event["queryStringParameters"]['variationName'])
        print(returnData.values)
        return {
        'statusCode': 200,
        'headers': { "Access-Control-Allow-Origin": "*",
                    'Content-Type': 'application/json' },
        'body': json.dumps(returnData.values)
        }

    elif 'queryStringParameters' in event and 'objectId' in event['queryStringParameters']:
        returnData = MenuItem(client, event["queryStringParameters"]['objectId'])
        print(returnData.variations)
        return {
        'statusCode': 200,
        'headers': { "Access-Control-Allow-Origin": "*",
                    'Content-Type': 'application/json' },
        'body': json.dumps(returnData.variations)
        }