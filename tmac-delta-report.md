# 🛡️ TMAC Delta Risk Report

**Generated on:** 2026-03-16T06:26:02.205584Z
**Plan file:** `tests/fixtures/plans/create_with_threat.json`
**Execution Time:** 0.06s

---

> Este plan introduce 4 amenazas nuevas y resuelve 0.

## 📊 Delta Summary

| Métrica | Valor |
|---------|-------|
| ⬆ Amenazas introducidas | **4** |
| ⬇ Amenazas resueltas | **0** |
| ⚖ RiskDelta neto | **4** |
| ✚ Recursos creados | 1 |
| ✎ Recursos modificados | 0 |
| ✖ Recursos eliminados | 0 |

---

## 🔍 Delta Findings


| Acción | Recurso | Regla | Severidad | STRIDE | Descripción del cambio |
|--------|---------|-------|-----------|--------|------------------------|





| NUEVO | `aws_s3_bucket.data` | `TMAC-AWS-S3-001` | 🔴 Critical | Information Disclosure | acl: → public-read |





| NUEVO | `aws_s3_bucket.data` | `TMAC-AWS-S3-002` | 🟠 High | Information Disclosure | server_side_encryption_configuration |





| NUEVO | `aws_s3_bucket.data` | `TMAC-AWS-S3-003` | 🟡 Medium | Repudiation | logging |





| NUEVO | `aws_s3_bucket.data` | `TMAC-AWS-S3-005` | 🟠 High | Tampering | object_lock_enabled |

