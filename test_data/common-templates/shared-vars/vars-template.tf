output "account" {
  value = "{{ cluster.account }}"
}
output "cluster" {
  value = "{{ cluster.name }}"
}

output "env" {
  value = "{{ cluster.env or cluster.environment }}"
}

output "region" {
  value = "{{ cluster.region }}"
}
