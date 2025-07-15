+------------------------------------------------------+
|                    GitHub Repository                 |
|  +-----------------------------------------------+   |
|  | Issues / Pull Requests / Webhooks            |   |
+------------------------------------------------------+
                  |             ^
      GitHub API  |             |  PRs/Reviews
                  v             |
     +-------------------------------+
     |     AgentDev Controller       |
     |  (Runs in AWS ECS Fargate)    |
     +-------------------------------+
                   |  |
        +----------+  +-----------+
        |                         |
+-------------+            +-------------+
| Claude Agent| <--> Redis | Claude Agent|
|  (Role: Dev)|   ElastiCache  (Role: Reviewer)
+-------------+            +-------------+
        |                         |
        v                         v
   CloudWatch Logs         CloudWatch Logs

Here’s what we’ve done so far:

📐 Architecture: AWS-native, ECS + Redis + CloudWatch Logs

📝 Detailed GitHub issues: actionable, scoped for your contributors

🐳 Starter Docker scaffolding: Dockerfile + Compose, boto3 + Redis stack

No Kubernetes, no Copilot — plain AWS CLI + boto3 preferred workflow

1️⃣ Execution environment: AWS ECS with Fargate
Why ECS/Fargate?

Serverless containers (no EC2 mgmt)

Pre-integrated with AWS CLI/SAM CLI

Pricing is pay-per-use

No Kubernetes complexity, but supports Docker containers natively

2️⃣ GitHub Integration
AgentDev will run as an external service that authenticates to GitHub API securely via a bot account.

Issues/PRs will drive the work queue.

3️⃣ Claude Code Integration
Claude Code is API-based: we just need an environment that securely holds API credentials and makes HTTP calls.

Claude won’t need any unusual system dependencies (Python + requests/httpx will suffice).

4️⃣ Coordination and state management
Shared state store for agents: AWS ElastiCache (Redis) or SQS queues.

Keeps agent state externalized (coordination-safe) while maintaining logs.

5️⃣ Audit Logging
Logs written to CloudWatch Logs for centralization and auditability.