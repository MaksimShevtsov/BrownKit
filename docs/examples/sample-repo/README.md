# Sample Repo Fixture

A deliberately-tiny Java/Maven project used to smoke-test BrownKit's helper
scripts. Not a runnable Spring Boot app — just enough structure for
detectors and parsers to do useful work.

## Shape

```
sample-repo/
├── pom.xml                        # Maven manifest; DB dep (postgresql)
├── Jenkinsfile                    # CI detection
├── src/main/java/com/example/
│   ├── payments/{PaymentController,PaymentService}.java   # Payments candidate
│   └── customers/{CustomerController,CustomerRepository}.java  # Customers candidate
├── src/main/resources/application.yml   # contains a DEMO-ONLY credential
├── src/test/java/com/example/payments/PaymentServiceTest.java
└── target/site/jacoco/jacoco.xml  # fixture coverage report
```

Expected candidates after `/scan`: `Payments` and `Customers`.

## Smoke-test the helpers

From the BrownKit repo root:

```bash
# 1. Stack detection
./scripts/bash/detect-stack.sh --root docs/examples/sample-repo
#   → java, pom.xml, has_db_dependency: true, ci_platforms: [jenkins],
#     coverage_report_candidates: ["target/site/jacoco/jacoco.xml"],
#     adaptations: { db_schema_analysis: auto, coverage_source: report }

# 2. Manifest enumeration
./scripts/bash/list-manifests.sh --root docs/examples/sample-repo
#   → one manifest entry for pom.xml with sha1

# 3. Coverage parsing
./scripts/bash/parse-coverage.sh --report docs/examples/sample-repo/target/site/jacoco/jacoco.xml
#   → source: jacoco, totals: { line_rate ≈ 0.4 }, two packages

# 4. Secret scanning
./scripts/bash/find-secrets.sh --root docs/examples/sample-repo
#   → one LOW-confidence finding in application.yml (demo-only credential)
```

## End-to-end walkthrough (LLM commands)

If you have spec-kit wired up:

```bash
specify run speckit.brownkit.init      # answers: compliance=[], env=[dev], has_frontend=false
specify run speckit.brownkit.scan      # ≈ 2 candidates from S1/S3
specify run speckit.brownkit.discover  # locks BC-001 Payments, BC-002 Customers
specify run speckit.brownkit.report    # 4 reports emitted
specify run speckit.brownkit.assess    # unified risk scoring
specify run speckit.brownkit.generate  # capability contexts + prompts
specify run speckit.brownkit.finish    # acceptance check, manifest, handoff
```

You should see the SDET report flag `not-collected` for defect/flaky
signals (none registered), and the Payments capability carry a higher
unified risk than Customers (driven by DB dependency + credential in
config).

## Safety note

The `password:` in `application.yml` is obviously fake and marked with
`BROWNKIT_EXAMPLE_ONLY`. The string exists solely to exercise
`find-secrets.sh`. **Do not use this config as a template for real apps.**
