# Security Policy

## 🔒 Security Best Practices

### API Keys and Secrets

**CRITICAL:** Never commit sensitive data to version control!

1. **Environment Variables**
   - Copy `.env.example` to `.env`
   - Fill in your actual API keys and secrets
   - `.env` is in `.gitignore` and will NOT be committed

2. **Rotating Compromised Keys**
   - If you accidentally committed an API key, rotate it immediately
   - For Google API keys: https://console.cloud.google.com/apis/credentials
   - Generate new SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

3. **Production Deployment**
   - Use environment variables or secret management services
   - Never use DEBUG=True in production
   - Use strong, randomly generated SECRET_KEY

### File Upload Security

- Maximum file size: 16MB (configurable in config.py)
- Allowed extensions: PDF, PNG, JPG, JPEG, GIF
- Files are sanitized using `secure_filename()`

### Authentication

- Session timeout: 2 hours (configurable)
- Passwords should be hashed (TODO: implement bcrypt)
- CSRF protection enabled (TODO: add Flask-WTF)

### Database Security

- Use parameterized queries (SQLAlchemy ORM)
- Enable SSL for database connections in production
- Regular backups recommended

### HTTPS

- Always use HTTPS in production
- Configure SSL/TLS certificates
- Use Flask-Talisman for security headers

## 🐛 Reporting Security Vulnerabilities

If you discover a security vulnerability, please email: [your-email@example.com]

**Do NOT** open a public GitHub issue for security vulnerabilities.

## 📋 Security Checklist for Deployment

- [ ] All secrets in environment variables
- [ ] DEBUG=False in production
- [ ] HTTPS enabled
- [ ] Database SSL enabled
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] Security headers configured
- [ ] Regular dependency updates
- [ ] Monitoring and alerting configured
