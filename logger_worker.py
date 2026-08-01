"""
Click logger worker — second SNS subscriber.

Shows fan-out: same click event, different job (log only, no DB).
In production this might be metrics, email, webhook, fraud check, etc.
"""
import time
import logging

from messaging import ensure_messaging_infra, get_sqs_client, parse_message_body

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("click-logger")


def run(queue_url):
    sqs = get_sqs_client()
    logger.info("Logger worker listening on %s", queue_url)

    while True:
        resp = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10,
            VisibilityTimeout=30,
        )
        for msg in resp.get("Messages", []):
            try:
                payload = parse_message_body(msg["Body"])
                logger.info(
                    "FAN-OUT log click short_code=%s url_id=%s at=%s",
                    payload.get("short_code"),
                    payload.get("url_id"),
                    payload.get("clicked_at"),
                )
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )
            except Exception:
                logger.exception("Failed to log message; will retry after visibility timeout")


if __name__ == "__main__":
    for attempt in range(20):
        try:
            infra = ensure_messaging_infra()
            run(infra["logger_queue_url"])
            break
        except Exception as e:
            logger.info("Messaging not ready (%s), retry %s/20...", e, attempt + 1)
            time.sleep(2)
    else:
        raise SystemExit("Could not start logger worker")
