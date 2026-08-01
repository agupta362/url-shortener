resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project_name}/DB_PASSWORD"
  type  = "SecureString"
  value = var.db_password
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.project_name}/SECRET_KEY"
  type  = "SecureString"
  value = var.secret_key
}

resource "aws_ssm_parameter" "db_name" {
  name  = "/${var.project_name}/DB_NAME"
  type  = "String"
  value = "urlshortener"
}

resource "aws_ssm_parameter" "db_user" {
  name  = "/${var.project_name}/DB_USER"
  type  = "String"
  value = "postgres"
}

resource "aws_ssm_parameter" "algorithm" {
  name  = "/${var.project_name}/ALGORITHM"
  type  = "String"
  value = "HS256"
}

resource "aws_ssm_parameter" "access_token_expire" {
  name  = "/${var.project_name}/ACCESS_TOKEN_EXPIRE_MINUTES"
  type  = "String"
  value = "30"
}

resource "aws_ssm_parameter" "refresh_token_expire" {
  name  = "/${var.project_name}/REFRESH_TOKEN_EXPIRE_DAYS"
  type  = "String"
  value = "7"
}

# RDS hostname for the API (DB_HOST). Created after the RDS instance exists.
resource "aws_ssm_parameter" "db_host" {
  name  = "/${var.project_name}/DB_HOST"
  type  = "String"
  value = aws_db_instance.postgres.address
}

resource "aws_ssm_parameter" "sns_clicks_topic_arn" {
  name  = "/${var.project_name}/SNS_CLICKS_TOPIC_ARN"
  type  = "String"
  value = aws_sns_topic.clicks.arn
}

resource "aws_ssm_parameter" "sqs_clicks_queue_url" {
  name  = "/${var.project_name}/SQS_CLICKS_QUEUE_URL"
  type  = "String"
  value = aws_sqs_queue.clicks.url
}

resource "aws_ssm_parameter" "sqs_clicks_log_queue_url" {
  name  = "/${var.project_name}/SQS_CLICKS_LOG_QUEUE_URL"
  type  = "String"
  value = aws_sqs_queue.clicks_log.url
}