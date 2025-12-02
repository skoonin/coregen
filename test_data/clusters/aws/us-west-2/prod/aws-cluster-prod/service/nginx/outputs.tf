output "instance_public_ip" {
  description = "Public IP of the Nginx instance"
  value       = aws_instance.nginx.public_ip
}

output "instance_id" {
  description = "ID of the Nginx instance"
  value       = aws_instance.nginx.id
}
