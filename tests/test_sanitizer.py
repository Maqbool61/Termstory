from termstory.sanitizer import (
    should_blacklist_command,
    redact_command,
    sanitize_session_commands
)

def test_blacklist_commands():
    assert should_blacklist_command("vault read secret/data") is True
    assert should_blacklist_command("aws configure set aws_access_key_id 123") is True
    assert should_blacklist_command("gh auth login --with-token") is True
    assert should_blacklist_command("kubectl create secret generic db-user-pass --from-literal=username=dev") is True
    
    # Safe commands
    assert should_blacklist_command("git status") is False
    assert should_blacklist_command("docker compose up") is False

def test_redact_environment_variables():
    # Exports
    assert redact_command("export DATABASE_URL=mysql://root:pass@localhost/db") == "export DATABASE_URL=[REDACTED]"
    assert redact_command("export AWS_SECRET_ACCESS_KEY='secret key'") == "export AWS_SECRET_ACCESS_KEY=[REDACTED]"
    assert redact_command('export PORT="8080"') == 'export PORT=[REDACTED]'
    
    # Inline high-risk env vars
    assert redact_command("DB_PASSWORD=123 python3 app.py") == "DB_PASSWORD=[REDACTED] python3 app.py"
    assert redact_command("API_TOKEN='token' npm run start") == "API_TOKEN=[REDACTED] npm run start"
    
    # Safe assignments (should not redact)
    assert redact_command("i=0") == "i=0"
    assert redact_command("name=app") == "name=app"

def test_redact_password_flags():
    assert redact_command("mysql -u root -pPassword123") == "mysql -u root -p[REDACTED]"
    assert redact_command("pg_dump -h localhost -U postgres --password=my-pass db") == "pg_dump -h localhost -U postgres --password=[REDACTED] db"
    assert redact_command("curl -H 'Authorization: Bearer secret-token' http://api") == "curl -H 'Authorization: Bearer [REDACTED_TOKEN]' http://[REDACTED_HOST]"
    assert redact_command("cli --token secret-token-value") == "cli --token [REDACTED]"

def test_redact_ips_and_fqdns():
    # IPs
    assert redact_command("ssh admin@192.168.1.105") == "ssh admin@[REDACTED_IP]"
    
    # FQDNs
    assert redact_command("curl https://api.internal.domain.local/v1/users") == "curl https://[REDACTED_HOST]/v1/users"
    assert redact_command("ping dev-server.local") == "ping [REDACTED_HOST]"
    
    # Excluded files (should not be redacted)
    assert redact_command("python3 main.py") == "python3 main.py"
    assert redact_command("cat config.json") == "cat config.json"
    assert redact_command("vim README.md") == "vim README.md"

def test_redact_secrets_patterns():
    # AWS Key
    assert redact_command("aws s3 ls --access-key AKIAIOSFODNN7EXAMPLE") == "aws s3 ls --access-key [REDACTED_AWS_KEY]"
    # Slack token
    assert redact_command("curl -d 'token=xoxb-123456789012-abcdefghijklmnopqrstuvwx'") == "curl -d 'token=[REDACTED_SLACK_TOKEN]'"

def test_sanitize_session_commands():
    # Normal session
    cmds = ["cd project", "git status", "python3 main.py"]
    sanitized, is_blacklisted = sanitize_session_commands(cmds)
    assert is_blacklisted is False
    assert sanitized == ["cd project", "git status", "python3 main.py"]
    
    # Sensitive session
    cmds = ["export DB_PASS=123", "python3 main.py"]
    sanitized, is_blacklisted = sanitize_session_commands(cmds)
    assert is_blacklisted is False
    assert sanitized == ["export DB_PASS=[REDACTED]", "python3 main.py"]
    
    # Blacklisted session
    cmds = ["cd project", "vault read secret"]
    sanitized, is_blacklisted = sanitize_session_commands(cmds)
    assert is_blacklisted is True
    assert sanitized is None
