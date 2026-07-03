output "public_ip" {
  value       = aws_instance.api_server.public_ip
  description = "Public IP of the API server — use this to SSH in and update EC2_HOST secret"
}

output "public_dns" {
  value       = aws_instance.api_server.public_dns
  description = "Public DNS of the API server"
}

output "ssh_command" {
  value       = "ssh -i ~/.ssh/my-api-key.pem ubuntu@${aws_instance.api_server.public_ip}"
  description = "Ready-to-use SSH command"
}