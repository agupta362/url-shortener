# SNS + SQS — same fan-out pattern as LocalStack, but real AWS.
# Cost at learning traffic: usually cents/month. Destroy with the rest of the stack.

resource "aws_sns_topic" "clicks" {
  name = "${var.project_name}-clicks"

  tags = {
    Name    = "${var.project_name}-clicks"
    Project = var.project_name
  }
}

resource "aws_sqs_queue" "clicks" {
  name                       = "${var.project_name}-clicks"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 86400

  tags = {
    Name    = "${var.project_name}-clicks"
    Project = var.project_name
  }
}

resource "aws_sqs_queue" "clicks_log" {
  name                       = "${var.project_name}-clicks-log"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 86400

  tags = {
    Name    = "${var.project_name}-clicks-log"
    Project = var.project_name
  }
}

resource "aws_sqs_queue_policy" "clicks" {
  queue_url = aws_sqs_queue.clicks.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNS"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.clicks.arn
        Condition = {
          ArnEquals = { "aws:SourceArn" = aws_sns_topic.clicks.arn }
        }
      }
    ]
  })
}

resource "aws_sqs_queue_policy" "clicks_log" {
  queue_url = aws_sqs_queue.clicks_log.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNS"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.clicks_log.arn
        Condition = {
          ArnEquals = { "aws:SourceArn" = aws_sns_topic.clicks.arn }
        }
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "clicks_analytics" {
  topic_arn            = aws_sns_topic.clicks.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.clicks.arn
  raw_message_delivery = true
}

resource "aws_sns_topic_subscription" "clicks_logger" {
  topic_arn            = aws_sns_topic.clicks.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.clicks_log.arn
  raw_message_delivery = true
}
