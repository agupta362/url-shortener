"""
Click analytics worker — SQS analytics queue → Postgres.
"""
import time
import logging

from database import execute_query
from messaging import (
    ensure_messaging_infra,
    get_sqs_client,
    parse_message_body,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("click-worker")


def process_click(payload):
    short_code = payload.get("short_code")
    url_id = payload.get("url_id")

    if not short_code and not url_id:
        logger.warning("Skipping message with no short_code or url_id: %s", payload)
        return

    if not url_id:
        row = execute_query(
            "SELECT id FROM urls WHERE short_code = %s",
            (short_code,),
            fetch="one",
        )
        if not row:
            logger.warning("Unknown short_code %s — dropping message", short_code)
            return
        url_id = row[0]

    execute_query("UPDATE urls SET clicks = clicks + 1 WHERE id = %s", (url_id,))
    execute_query("INSERT INTO clicks (url_id) VALUES (%s)", (url_id,))
    logger.info("Recorded click short_code=%s url_id=%s", short_code, url_id)


def run(queue_url):
    sqs = get_sqs_client()
    logger.info("Analytics worker listening on %s", queue_url)

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
                process_click(payload)
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )
            except Exception:
                logger.exception("Failed to process message; will retry after visibility timeout")


if __name__ == "__main__":
    for attempt in range(20):
        try:
            infra = ensure_messaging_infra()
            run(infra["analytics_queue_url"])
            break
        except Exception as e:
            logger.info("Messaging not ready (%s), retry %s/20...", e, attempt + 1)
            time.sleep(2)
    else:
        raise SystemExit("Could not start analytics worker")
