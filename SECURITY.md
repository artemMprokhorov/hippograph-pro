# Security Considerations

## ⚠️ Important Disclaimer

**This is a research project exploring semantic memory and knowledge graph systems.** It has not been audited for production use with sensitive or confidential data. Use at your own risk.

---

## Current Security Model

### Authentication
- API key via URL parameter: `?api_key=YOUR_KEY`
- Alternative: Authorization header `Bearer YOUR_KEY`

### Known Limitations

**1. API Key in URL**
When using URL parameter authentication, keys are visible in:
- Server logs
- ngrok request logs  
- Browser history (if accessed directly)
- Proxy/CDN logs

**Mitigation:** Use strong, unique keys and rotate periodically.

**2. No Rate Limiting**
The server has no built-in rate limiting. API key holders can make unlimited requests.

**3. Unencrypted Database**
SQLite database stored in plaintext. Anyone with filesystem access can read all notes.

**Mitigation:** Proper filesystem permissions and server access controls.

**4. No Input Validation Limits**
Currently no hard limits on note size or request frequency.

---

## 🔐 Best Practices

### API Key Management
- Minimum 32 characters, cryptographically random
- Never commit keys to version control
- Rotate keys every 90 days
- Use different keys for different environments

### Server Access
- Run behind firewall
- Consider VPN for remote access
- Monitor access logs regularly
- Restrict Docker container privileges

### Data Protection
- Regular backups of database
- Secure backup storage
- Test restore procedures
- Document recovery process

---

## 🛡️ Threat Model

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| API key exposure | Medium | Strong keys, rotation, monitoring |
| Request flooding | Low | External rate limiting (nginx, cloudflare) |
| Data theft (server access) | Low | Filesystem permissions, monitoring |
| Man-in-the-middle | Low | HTTPS via ngrok |
| SQL injection | Very Low | Parameterized queries throughout |

---

## 🚧 Future Improvements

### Planned Security Enhancements
- OAuth 2.0 flow support
- Built-in rate limiting
- Request size validation
- Database encryption option
- Audit logging system

### Not Planned (Out of Scope)
- Multi-user authentication
- Fine-grained access control
- Compliance certifications
- Enterprise security features

This project focuses on research and personal use, not enterprise deployment.

---

## 📋 Security Checklist

Before deploying:

- [ ] Changed default API key from `.env.example`
- [ ] API key is 32+ characters, random
- [ ] Server behind firewall or VPN
- [ ] Regular backup schedule configured
- [ ] Tested restore procedure
- [ ] Monitoring/alerting for unusual activity
- [ ] Documented who has access
- [ ] Dependencies are up to date

---

## 🐛 Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public issue
2. Contact maintainer directly via GitHub
3. Include detailed description and reproduction steps
4. Allow time for fix before public disclosure

---

## ⚖️ Legal Disclaimer

This software is provided "as is" without warranty. Users are responsible for:
- Securing their deployment
- Protecting their data
- Compliance with applicable laws
- Understanding the risks

The authors assume no liability for data loss, unauthorized access, or other security incidents.
