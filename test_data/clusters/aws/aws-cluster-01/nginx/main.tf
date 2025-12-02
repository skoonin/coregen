terraform {
  backend "s3" {
    bucket = "terraform-state-us-east-2"
    key    = "dev/aws-cluster-dev/service/nginx/terraform.tfstate"
    region = "us-east-2"
  }
}

provider "aws" {
  region = var.region
}

resource "aws_instance" "nginx" {
  ami           = var.ami_id
  instance_type = var.instance_type

  user_data = <<-EOF
              #!/bin/bash
              amazon-linux-extras install nginx1
              systemctl start nginx
              systemctl enable nginx
              EOF

  tags = {
    Name        = "nginx-server"
    Environment = var.environment
  }

  vpc_security_group_ids = [aws_security_group.nginx.id]
}

resource "aws_security_group" "nginx" {
  name        = "nginx-security-group"
  description = "Security group for Nginx server"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
