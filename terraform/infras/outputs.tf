output "public_ip" {
  value       = aws_instance.api_server.public_ip
  description = "Public IP of the API server"
}

output "public_dns" {
  value       = aws_instance.api_server.public_dns
  description = "Public DNS of the API server"
}
 