# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_table = boto3.resource('dynamodb').Table(os.environ["DYNAMO_TABLE"])
sqs_client = boto3.client('sqs')

def scan(table, **kwargs):
    response = table.scan(**kwargs)
    yield from response['Items']
    while response.get('LastEvaluatedKey'):
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], **kwargs)
        yield from response['Items']

# Function handler
def handler(event, context):
    items = list(scan(dynamodb_table))
    for item in items:
        logger.info(f'item: {item}')
        try:
            message = {
                "source": item["source"]
            }
            if item.get("newfeedname"):
                message["newfeedname"] = item["newfeedname"]
            if item.get("newfeedtitle"):
                message["newfeedtitle"] = item["newfeedtitle"]
            if item.get("filter"):
                message["filter"] = item["filter"]
            sqs_client.send_message(
                QueueUrl=os.environ["QUEUE_URL"],
                MessageBody=json.dumps(message)
            )
        except Exception as Argument:
            logger.exception("Error occurred while fetching rss sources")