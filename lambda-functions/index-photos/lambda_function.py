"""LF1 - index-photos

Triggered by an S3 PUT on the photos bucket (B2).
1. Reads custom labels from the x-amz-meta-customLabels metadata (headObject).
2. Detects labels with Rekognition detectLabels.
3. Stores {objectKey, bucket, createdTimestamp, labels} in the OpenSearch "photos" index.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

import boto3

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition")

ES_ENDPOINT = os.environ["ES_ENDPOINT"]  # e.g. search-photos-xxxx.us-east-1.es.amazonaws.com
ES_INDEX = os.environ.get("ES_INDEX", "photos")
_AUTH = base64.b64encode(
    f"{os.environ['ES_USER']}:{os.environ['ES_PASS']}".encode()
).decode()


def es_request(method, path, body=None):
    req = urllib.request.Request(
        f"https://{ES_ENDPOINT}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", "Authorization": f"Basic {_AUTH}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def lambda_handler(event, context):
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        print(f"Indexing s3://{bucket}/{key}")

        # A1: custom labels from object metadata (S3 lowercases metadata keys)
        head = s3.head_object(Bucket=bucket, Key=key)
        custom = head.get("Metadata", {}).get("customlabels", "")
        labels = [l.strip().lower() for l in custom.split(",") if l.strip()]

        # Append Rekognition labels
        # No MaxLabels/MinConfidence limits: index every label Rekognition returns
        rek = rekognition.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}})
        for label in rek["Labels"]:
            name = label["Name"].lower()
            if name not in labels:
                labels.append(name)

        doc = {
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": head["LastModified"].strftime("%Y-%m-%dT%H:%M:%S"),
            "labels": labels,
        }
        doc_id = urllib.parse.quote(f"{bucket}/{key}", safe="")
        es_request("PUT", f"/{ES_INDEX}/_doc/{doc_id}", doc)
        print(json.dumps(doc))
        results.append(doc)

    return {"statusCode": 200, "body": json.dumps(results)}
