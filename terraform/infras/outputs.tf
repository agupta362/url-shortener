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
 