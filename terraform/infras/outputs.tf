output "public_ip" {
  value       = aws_instance.api_server.public_ip
  description = "Public IP of the API server"
}

output "public_dns" {
  value       = aws_instance.api_server.public_dns
  description = "Public DNS of the API server"
}

output "rds_endpoint" {
  value       = aws_db_instance.postgres.address
  description = "RDS Postgres endpoint (use as DB_HOST)"
}

output "sns_clicks_topic_arn" {
  value       = aws_sns_topic.clicks.arn
  description = "SNS topic for click fan-out"
}

output "sqs_clicks_queue_url" {
  value       = aws_sqs_queue.clicks.url
  description = "SQS analytics queue URL"
}

output "sqs_clicks_log_queue_url" {
  value       = aws_sqs_queue.clicks_log.url
  description = "SQS logger queue URL"
}
 