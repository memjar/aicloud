# API Key Rotation Log

Audit trail of all key rotations for aimodels.cloud API.
Update this file after each rotation following the template below.

## Rotation Entry Template

```markdown
## YYYY-MM-DD — [NORMAL|EMERGENCY] ROTATION: [Key Type]

**Environment:** [development|staging|production]
**Key Type:** [OPENAI_API_KEY|ANTHROPIC_API_KEY|...]
**Rotation Type:** [Scheduled|Emergency|Compromise]
**Old Key Hash:** [first 16 chars of SHA256]
**New Key Hash:** [first 16 chars of SHA256]
**AWS Region:** [us-east-1|...]
**Deployed:** YYYY-MM-DD HH:MM UTC
**Verified:** YYYY-MM-DD HH:MM UTC
**Old Key Deactivated:** YYYY-MM-DD HH:MM UTC
**Completed By:** [username or CI/CD system]
**Reviewed By:** [username]
**Issues/Notes:** [Any problems encountered or notes]
**Rollback Used:** [Yes/No]
**Post-Mortem:** [Link to incident report if emergency]
**Duration:** [minutes from start to full recovery]
```

---

## Rotation History

### Initialize Log

This log tracks all rotations for audit and compliance purposes.

- Quarterly reviews: Extract logs for SOC2, compliance audits
- Emergency rotations: Document immediately
- Scheduled rotations: Plan in advance using rotation schedule

### Tracking Instructions

1. Use timestamps in UTC (Zulu time)
2. Hash keys using: `echo -n "KEY_VALUE" | sha256sum | cut -c1-16`
3. Document any issues or unusual behavior
4. Update within 1 hour of completion
5. Schedule post-mortem for emergency rotations

### Access Control

- **Read:** All engineering team members
- **Write:** Infrastructure team, on-call engineer
- **Review:** CTO, Security officer (monthly)

---

## Key Rotation Tracking

| Date | Environment | Key Type | Duration | Status | Completed By |
|------|-------------|----------|----------|--------|--------------|
| TBD | production | OPENAI_API_KEY | -- | Pending | -- |
| TBD | production | ANTHROPIC_API_KEY | -- | Pending | -- |
| TBD | production | TOGETHER_API_KEY | -- | Pending | -- |
| TBD | staging | STRIPE_API_KEY | -- | Pending | -- |

---

## Notes

- First rotation scheduled for ~90 days after initial setup
- Keep old key active for 24-48 hours before deactivation
- Always verify new key works before deactivating old key
- Export audit logs before rotation: `src/utils/key_logging.py`
- Backup current configuration before making changes
- Test in staging first (except for database/redis keys)

---

## References

- [Key Rotation Guide](KEY_ROTATION_GUIDE.md)
- [Emergency Playbook](EMERGENCY_ROTATION_PLAYBOOK.md)
- [Configuration Guide](CONFIGURATION.md)
