"""LF2 - search-photos
GET /search?q=... : Lex extracts keywords -> search OpenSearch "photos" index.
Returns {"results": [{"url": ..., "labels": [...]}]} (empty if no keywords).
"""
import base64
import json
import os
import urllib.request

import boto3

lex = boto3.client("lexv2-runtime")
s3 = boto3.client("s3")

ES = os.environ["ES_ENDPOINT"]
INDEX = os.environ.get("ES_INDEX", "photos")
AUTH = base64.b64encode(f"{os.environ['ES_USER']}:{os.environ['ES_PASS']}".encode()).decode()
CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET,PUT,OPTIONS", "Content-Type": "application/json"}


def singular(w):
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "sses")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def get_keywords(q):
    r = lex.recognize_text(botId=os.environ["BOT_ID"], botAliasId=os.environ["BOT_ALIAS_ID"],
                           localeId="en_US", sessionId="search", text=q)
    intent = r.get("sessionState", {}).get("intent", {})
    if intent.get("name") != "SearchIntent":
        return []
    words = []
    for slot in (intent.get("slots") or {}).values():
        v = ((slot or {}).get("value") or {}).get("interpretedValue")
        if v:
            words.append(v.strip().lower())
    return words


def search(keywords):
    terms = set()
    for k in keywords:
        terms.update({k, singular(k)})
    body = {"size": 100, "query": {"bool": {"should": [{"match": {"labels": t}} for t in terms],
                                            "minimum_should_match": 1}}}
    req = urllib.request.Request(f"https://{ES}/{INDEX}/_search", data=json.dumps(body).encode(),
                                 method="POST", headers={"Content-Type": "application/json",
                                                         "Authorization": f"Basic {AUTH}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        hits = json.loads(r.read())["hits"]["hits"]
    out = []
    for h in hits:
        d = h["_source"]
        url = s3.generate_presigned_url("get_object", Params={"Bucket": d["bucket"], "Key": d["objectKey"]},
                                        ExpiresIn=3600)
        out.append({"url": url, "labels": d.get("labels", [])})
    return out


def lambda_handler(event, context):
    q = ((event.get("queryStringParameters") or {}).get("q") or event.get("q") or "").strip()
    print("query:", q)
    results = []
    if q:
        keywords = get_keywords(q)
        print("keywords:", keywords)
        if keywords:
            results = search(keywords)
    return {"statusCode": 200, "headers": CORS, "body": json.dumps({"results": results})}
