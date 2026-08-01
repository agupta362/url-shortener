"""
Flow:
  API publish_click() → SNS topic
                            ├─► SQS url-shortener-clicks      (analytics worker)
                            └─► SQS url-shortener-clicks-log  (logger worker)
"""
import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


def _client_kwargs():
    # Compose aws override may set these to "" — empty breaks instance-role auth.
    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_ENDPOINT_URL",
    ):
        if key in os.environ and not os.environ[key].strip():
            del os.environ[key]

    kwargs = {"region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1")}
    endpoint = os.getenv("AWS_ENDPOINT_URL")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return kwargs


def get_sqs_client():
    return boto3.client("sqs", **_client_kwargs())


def get_sns_client():
    return boto3.client("sns", **_client_kwargs())


def _queue_name_analytics():
    return os.getenv("SQS_CLICKS_QUEUE_NAME", "url-shortener-clicks")


def _queue_name_logger():
    return os.getenv("SQS_CLICKS_LOG_QUEUE_NAME", "url-shortener-clicks-log")


def _topic_name():
    return os.getenv("SNS_CLICKS_TOPIC_NAME", "url-shortener-clicks")


def ensure_queue(name, sqs=None):
    sqs = sqs or get_sqs_client()
    try:
        url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
    except ClientError:
        url = sqs.create_queue(QueueName=name)["QueueUrl"]
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])
    return url, attrs["Attributes"]["QueueArn"]


def ensure_topic(sns=None):
    sns = sns or get_sns_client()
    return sns.create_topic(Name=_topic_name())["TopicArn"]


def _allow_sns_to_sqs(sqs, queue_url, queue_arn, topic_arn):
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "sns.amazonaws.com"},
                "Action": "sqs:SendMessage",
                "Resource": queue_arn,
                "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
            }
        ],
    }
    sqs.set_queue_attributes(
        QueueUrl=queue_url,
        Attributes={"Policy": json.dumps(policy)},
    )


def _subscribe_queue(sns, sqs, topic_arn, queue_url, queue_arn):
    _allow_sns_to_sqs(sqs, queue_url, queue_arn, topic_arn)
    # RawMessageDelivery: queue gets our JSON directly (no SNS envelope wrapper)
    subs = sns.list_subscriptions_by_topic(TopicArn=topic_arn).get("Subscriptions", [])
    already = any(s.get("Endpoint") == queue_arn for s in subs)
    if not already:
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol="sqs",
            Endpoint=queue_arn,
            Attributes={"RawMessageDelivery": "true"},
        )


def ensure_messaging_infra():
    """
    Return topic + queue endpoints.
    On AWS (Terraform): use SNS_CLICKS_TOPIC_ARN + queue URLs from env/SSM.
    Locally (LocalStack): create topic/queues/subscriptions if missing.
    """
    topic_arn = os.getenv("SNS_CLICKS_TOPIC_ARN", "").strip()
    analytics_url = os.getenv("SQS_CLICKS_QUEUE_URL", "").strip()
    logger_url = os.getenv("SQS_CLICKS_LOG_QUEUE_URL", "").strip()

    if topic_arn and analytics_url and logger_url:
        return {
            "topic_arn": topic_arn,
            "analytics_queue_url": _normalize_queue_url(analytics_url),
            "logger_queue_url": _normalize_queue_url(logger_url),
        }

    sqs = get_sqs_client()
    sns = get_sns_client()
    topic_arn = ensure_topic(sns)

    analytics_url, analytics_arn = ensure_queue(_queue_name_analytics(), sqs)
    logger_url, logger_arn = ensure_queue(_queue_name_logger(), sqs)

    _subscribe_queue(sns, sqs, topic_arn, analytics_url, analytics_arn)
    _subscribe_queue(sns, sqs, topic_arn, logger_url, logger_arn)

    return {
        "topic_arn": topic_arn,
        "analytics_queue_url": _normalize_queue_url(analytics_url),
        "logger_queue_url": _normalize_queue_url(logger_url),
    }


def get_queue_url(sqs=None, name=None):
    """Return a queue URL (default = analytics clicks queue)."""
    name = name or _queue_name_analytics()
    explicit = os.getenv("SQS_CLICKS_QUEUE_URL") if name == _queue_name_analytics() else None
    if explicit:
        return _normalize_queue_url(explicit)
    url, _ = ensure_queue(name, sqs)
    return _normalize_queue_url(url)


def _normalize_queue_url(url):
    """Point LocalStack queue URLs at AWS_ENDPOINT_URL (k8s DNS: localstack:4566)."""
    endpoint = os.getenv("AWS_ENDPOINT_URL", "").strip().rstrip("/")
    if not endpoint or not url:
        return url
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    ep = urlparse(endpoint)
    if not ep.netloc:
        return url
    return urlunparse((ep.scheme or "http", ep.netloc, parsed.path, "", "", ""))


def parse_message_body(raw_body):
    """Parse SQS body; unwrap SNS envelope if RawMessageDelivery was off."""
    data = json.loads(raw_body)
    if isinstance(data, dict) and data.get("Type") == "Notification" and "Message" in data:
        return json.loads(data["Message"])
    return data


def publish_click(short_code, url_id=None):
    """Publish one click event to SNS — fans out to every subscribed queue."""
    sns = get_sns_client()
    infra = ensure_messaging_infra()
    body = {
        "event": "click",
        "short_code": short_code,
        "url_id": url_id,
        "clicked_at": datetime.now(timezone.utc).isoformat(),
    }
    sns.publish(TopicArn=infra["topic_arn"], Message=json.dumps(body))
    return body
