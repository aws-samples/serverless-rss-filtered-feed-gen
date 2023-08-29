# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import re
import os
import json
import logging
from feedgen.feed import FeedGenerator
import feedparser

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs_client = boto3.client("sqs")
s3_client = boto3.client("s3")

def genFeed(sf, filter, newfeedtitle):   
    f = FeedGenerator()
    title = sf.channel.title if not newfeedtitle else newfeedtitle
    f.title(title)
    f.managingEditor(sf.channel.author)
    f.link(href=sf.channel.link, rel='alternate')
    f.description(sf.channel.description)
    f.lastBuildDate(sf.channel.updated)
    f.pubDate(sf.channel.published)
    f.docs(sf.channel.docs)
    
    for entry in sf.entries:
        
        if any(re.search(f, entry.description) for f in filter):
            fe = f.add_entry()
            fe.title(entry.title)
            fe.guid(entry.guid)
            fe.link(entry.links)
            fe.description(entry.description)
            fe.pubDate(entry.published)
            fe.category(list_to_category_dict(entry.category))
            fe.author(email=entry.author)
    return f

def list_to_category_dict(rlist):
    return [{'term':k,'scheme':v} for k,v in (pair.split(':') for pair in rlist.split(','))]

# Function handler
def handler(event, context):
    for record in event['Records']:
        try:
            logger.info(f"Received message: {record['body']}")
            sqs_message = json.loads(record["body"])
            source = sqs_message["source"]
            filter = None if not "filter" in sqs_message else sqs_message["filter"]
            newfeedtitle = None if not "newfeedtitle" in sqs_message else sqs_message["newfeedtitle"]
            newfeedname = None if not "newfeedname" in sqs_message else sqs_message["newfeedname"]
            sf = feedparser.parse(source)
            
            nf = genFeed(sf,filter,newfeedtitle)
            logger.info(f'Generated feed xml: {nf.rss_str(pretty=True)}')
            
            logger.info("Write temporary file: rss.xml")
            nf.rss_file('/tmp/rss.xml')
            
            filekey = f"rss/{nf.title().replace(' ','')}" if not newfeedname  else f"feed/{newfeedname}"
            logger.info(f"Upload file to S3: {os.environ['S3_BUCKET']}/{filekey}")
            s3_client.upload_file("/tmp/rss.xml", os.environ['S3_BUCKET'], filekey)
        except Exception as Argument:
            logger.exception("Error occurred while processing rss feed items")
        finally:
            # Always delete message from queue, even in an error (Parsing this RSS source can be tried again later)
            sqs_client.delete_message(
                QueueUrl=os.environ["CHANNEL_QUEUE_URL"],
                ReceiptHandle=record["receiptHandle"]
            )