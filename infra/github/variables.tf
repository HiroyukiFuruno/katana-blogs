variable "github_repository" {
  type        = string
  description = "GitHub Repository Name"
  default     = "katana-blogs"
}

variable "qiita_access_token" {
  type        = string
  description = "Qiita Access Token (write_qiita scope)"
  sensitive   = true
}
