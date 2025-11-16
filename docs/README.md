# 📚 SWE AI Fleet — Documentation Hub

**Complete reference guide for SWE AI Fleet platform**

Welcome! This is your starting point for understanding, deploying, and operating SWE AI Fleet.

---

## 🚀 Quick Navigation

### For Different Roles

| Role | Start Here | Goal |
|------|-----------|------|
| **New User** | [Getting Started](./getting-started/README.md) | Deploy & explore in 30 minutes |
| **Developer** | [Microservices Guide](./microservices/README.md) | Understand architecture & contribute |
| **Operator** | [Operations Guide](./operations/README.md) | Deploy & monitor in production |
| **DevOps/SRE** | [Infrastructure](./infrastructure/README.md) | Deploy, scale & maintain |
| **Architect** | [Architecture](./architecture/README.md) | Understand system design & decisions |
| **Researcher** | [Reference](./reference/README.md) | Testing, patterns & technical details |

---

## 📖 Main Sections

### 🎯 [Getting Started](./getting-started/README.md)
- **What**: Complete onboarding guide
- **Time**: 10-30 minutes
- **Content**:
  - What is SWE AI Fleet
  - K8s deployment (10-15 min)
  - Local CRI-O demo (10 min)
  - Development practices (DDD, Ports & Adapters)
  - 3-day learning path
  - Production checklist

### 🏗️ [Architecture](./architecture/README.md)
- **What**: System design & principles
- **Audience**: Architects, senior developers
- **Content**:
  - Hexagonal architecture
  - Domain-Driven Design
  - Microservices interactions
  - Data flow & FSMs

### 🤖 [Microservices](./microservices/README.md)
- **What**: Complete guide to all 6 services
- **Audience**: Developers, integrators
- **Services**:
  1. **Planning** - Story FSM & lifecycle
  2. **Task Derivation** - LLM-based task generation
  3. **Context** - Knowledge graph context
  4. **Workflow** - Task FSM + RBAC
  5. **Orchestrator** - Multi-agent deliberation
  6. **Ray Executor** - GPU execution

Each service includes:
- API reference (gRPC)
- Event specifications (AsyncAPI)
- Error codes & recovery
- Performance & SLA
- Troubleshooting

### 🛠️ [Operations](./operations/README.md)
- **What**: Production deployment & operations
- **Audience**: Operators, SREs
- **Content**:
  - Deployment procedures
  - Health monitoring
  - Troubleshooting (K8s + CRI-O)
  - Scaling strategies
  - Backup & recovery

### ☁️ [Infrastructure](./infrastructure/README.md)
- **What**: K8s, networking, persistence
- **Audience**: DevOps, infrastructure teams
- **Content**:
  - K8s manifests
  - NATS JetStream setup
  - Neo4j + Redis configuration
  - Ray cluster setup
  - Network policies

### 📚 [Reference](./reference/README.md)
- **What**: Testing, patterns, conventions
- **Audience**: Developers, QA
- **Content**:
  - Testing strategy & pyramid
  - Code patterns (DDD, Ports & Adapters)
  - Naming conventions
  - Coverage requirements

### 📦 [Archived](./archived/README.md)
- **What**: Historical documentation
- **Purpose**: Reference & audit trail
- **Content**: 63 files from previous sessions

---

## 🔗 Quick Links

### Essential Documents
- [Hexagonal Architecture Principles](./normative/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md) - Core design principles
- [Testing Strategy](./reference/testing.md) - Unit/Integration/E2E
- [Troubleshooting](./operations/troubleshooting.md) - K8s + CRI-O issues
- [Project Genesis](./PROJECT_GENESIS.md) - History & evolution

### API References
- [gRPC Services](./specs/) - Protocol buffer definitions
- [AsyncAPI Events](./specs/asyncapi.yaml) - NATS event contracts
- [OpenAPI (Coming Soon)](./specs/) - REST API reference

### Deployment
- [Fresh Deploy](./operations/DEPLOYMENT.md) - First-time setup
- [Monitoring & Observability](./operations/DEPLOYMENT.md#monitoring) - Metrics & alerts
- [Scaling](./operations/DEPLOYMENT.md#scaling) - Horizontal/vertical

---

## 📊 Documentation Structure

```
docs/
├── README.md                       ← YOU ARE HERE
├── getting-started/
│   └── README.md                   ← Start here (30 min)
├── architecture/
│   ├── README.md                   ← System design
│   └── [10+ architecture docs]
├── microservices/
│   ├── README.md                   ← All 6 services
│   └── [service-specific guides]
├── operations/
│   ├── README.md                   ← Production guide
│   ├── DEPLOYMENT.md               ← Deploy procedures
│   └── troubleshooting.md          ← K8s + CRI-O issues
├── infrastructure/
│   ├── README.md                   ← K8s setup
│   └── [K8s manifests & configs]
├── reference/
│   ├── testing.md                  ← Testing pyramid
│   └── [patterns & conventions]
├── normative/
│   └── HEXAGONAL_ARCHITECTURE_PRINCIPLES.md
├── archived/
│   ├── README.md                   ← 63 historical files
│   ├── sessions/
│   ├── summaries/
│   └── ...
├── specs/
│   ├── asyncapi.yaml               ← Event contracts
│   ├── planning.proto               ← Planning Service API
│   └── [other proto files]
└── [monitoring, examples, etc.]
```

---

## ⚡ Common Tasks

### "I want to deploy SWE AI Fleet"
1. Read [Getting Started](./getting-started/README.md) (10 min)
2. Follow [Deployment Guide](./operations/DEPLOYMENT.md) (15 min)
3. Run verification script (5 min)

### "I want to understand the code"
1. Read [Hexagonal Architecture](./normative/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md) (15 min)
2. Explore [Planning Service](./microservices/README.md#planning-service) (20 min)
3. Review tests in `services/planning/tests/unit/` (30 min)

### "Something isn't working"
1. Check [Troubleshooting](./operations/troubleshooting.md)
2. Find service in [Microservices Guide](./microservices/README.md)
3. Review error codes & recovery procedures

### "I want to add a feature"
1. Read [Getting Started](./getting-started/README.md#development-practices) (15 min)
2. Study [Testing Strategy](./reference/testing.md) (20 min)
3. Create PR following DDD + testing pyramid

---

## 📈 Documentation Stats

| Metric | Value |
|--------|-------|
| **Total Files** | ~120 (from 191, -37% reduction) |
| **Canonical Sources** | 3 (Testing, Getting Started, Troubleshooting) |
| **Service READMEs** | 6 (all enriched) |
| **Total Lines** | ~12,000+ lines |
| **Last Updated** | 2025-11-15 (Phase 4 complete) |

---

## 🎯 Documentation Philosophy

### Single Source of Truth
- **No duplicates**: If documented, exists in only one place
- **Canonical references**: When needed, link to canonical source
- **Versioned together**: With code changes

### Easy to Navigate
- **Start with your role**: Different entry points for different needs
- **Clear hierarchy**: Directory structure mirrors information architecture
- **Linked throughout**: Cross-references enable discovery

### Comprehensive
- **Architecture decisions**: Why, not just how
- **Error codes & recovery**: Operational clarity
- **Performance baselines**: Know what to expect
- **SLA/monitoring**: Measure health

### Up-to-Date
- **Maintained with code**: Documentation changes == code changes
- **Reviewed in PRs**: Like any other code artifact
- **Versioned in git**: Full history preserved

---

## 🚀 Getting Started

**Choose your path:**

1. **Deploying?** → [Getting Started](./getting-started/README.md) (30 min)
2. **Developing?** → [Microservices](./microservices/README.md) (45 min)
3. **Operating?** → [Operations](./operations/README.md) (1 hour)
4. **Troubleshooting?** → [Troubleshooting](./operations/troubleshooting.md) (5-30 min)

---

## 📝 Contributing to Documentation

**How to update docs:**
1. Update the relevant file(s)
2. Ensure links still work
3. Test: `make test docs=true` (when available)
4. Commit with message: `docs(service/component): change summary`
5. Reference any associated code changes

**Docs review checklist:**
- ✅ Content is accurate and up-to-date
- ✅ Examples work (test them)
- ✅ Links point to correct locations
- ✅ Markdown is clean and readable
- ✅ No duplicates (use links instead)

---

## 📞 Support

### Questions?
- Check the relevant guide above
- Search for keywords in documentation
- Review troubleshooting section
- Check [GitHub Issues](https://github.com/underpass-ai/swe-ai-fleet/issues)

### Found an Error?
- Create PR with fix
- Or file issue with details

### Want to Improve Docs?
- PRs welcome!
- Follow "Contributing to Documentation" above

---

## 🔐 Security & Compliance

- **No secrets in docs**: Passwords, keys go in secure vaults
- **Public repo**: Assume all docs are readable by anyone
- **Audit trail**: Git history shows all changes
- **GDPR-aware**: No PII in documentation

---

**Last Updated**: November 15, 2025  
**Status**: ✅ **COMPLETE & COMPREHENSIVE**  
**Next**: Monitor usage patterns and refine based on feedback

---

**Ready? Pick a section above and start!** 🚀


