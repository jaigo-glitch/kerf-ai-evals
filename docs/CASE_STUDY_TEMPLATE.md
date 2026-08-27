# KERF beta case study

> Draft only. Replace every bracketed field with documented evidence. Delete sections that lack evidence.

## Problem

[Describe the concrete reliability problem. Who experienced it, and what decision was difficult?]

## Hypothesis

[State what you believed versioned questions, read-only SQL execution, and expected-result scoring would improve.]

## Product tested

- Release: [version]
- Dates: [start] to [end]
- Evaluation cases: [count]
- Providers/models: [exact IDs]
- Fixture runs: [count]
- Live runs: [count]

## Participants

[Number] testers participated. Their roles were [roles]. Participation was [paid/unpaid]. No participant is described as a customer unless they actually purchased the product.

## Findings

| Observation | Evidence | Product response |
|---|---|---|
| [What happened] | [Run ID, issue, or tester feedback] | [Change and commit] |

## Quantitative results

| Metric | Before | After | Method |
|---|---:|---:|---|
| Pass rate | [x] | [y] | [same versioned case set] |
| Incorrect outputs detected | [x] | [y] | [definition] |
| Average latency | [x] | [y] | [provider/model and sample size] |
| Average cost per case | [x] | [y] | [token rates and date] |

## Failures and limitations

[Document at least one failure. State that the included business data is synthetic and that the beta sample is small.]

## What changed

- [Issue → commit → release]
- [Issue → commit → release]

## Conclusion

[Say only what the evidence supports. Avoid claims about production readiness, market demand, or customer outcomes unless measured.]

