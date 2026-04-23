# Contract: Approval Gate — Workflow Integration

**Feature**: 002-hitl-refund-approval  
**Date**: 2026-04-17  
**Type**: Workflow step contract

---

## Purpose

Defines how the `SupportRequestWorkflow` integrates the human approval gate between the PolicyEngine and ResponseAgent steps.

---

## Gate Trigger Condition

The approval gate activates **if and only if**:

```
classification.classified_intent == "refund_request"
AND classification.escalation_reason is None
```

If the condition is false, the workflow proceeds directly to ResponseAgent with no modification.

---

## Gate Inputs (from WorkflowState)

| Input                                     | Source                 | Used for                                                         |
| ----------------------------------------- | ---------------------- | ---------------------------------------------------------------- |
| `state.classification.classified_intent`  | ClassifierAgent output | Gate trigger check                                               |
| `state.policy_evaluation.final_decision`  | PolicyEngine output    | Populating `Recommendation.suggested_decision`                   |
| `state.policy_evaluation.evaluated_rules` | PolicyEngine output    | Populating `Recommendation.policy_rules_applied` and `reasoning` |
| `state.request.raw_message`               | CustomerRequest        | Displayed in approval prompt                                     |
| `state.request.request_id`                | CustomerRequest        | `Recommendation.request_id` and audit log                        |

---

## Gate Outputs (written to WorkflowState)

| Output         | Field                  | Value                     |
| -------------- | ---------------------- | ------------------------- |
| Human decision | `state.human_decision` | `HumanDecision` dataclass |

The `state.human_decision` field is `None` for all non-refund requests.

---

## Recommendation Construction

The workflow constructs a `Recommendation` as follows:

| `Recommendation` field | Derived from                                                                             |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `request_id`           | `state.request.request_id`                                                               |
| `suggested_decision`   | `"approve"` if `policy_eval.final_decision == "APPROVE"` else `"reject"`                 |
| `reasoning`            | Concatenated rationale from `policy_eval.evaluated_rules` (each `PolicyMatch.rationale`) |
| `policy_rules_applied` | `[rule.rule_name for rule in policy_eval.evaluated_rules if rule.matches]`               |
| `generated_at`         | `datetime.now()` at construction time                                                    |

---

## Workflow Step Sequence (modified)

```
Step 1: Classify             [ClassifierAgent]
Step 2: PolicyEngine         [PolicyEngine]
Step 2a: GATE CHECK          ← NEW
         if refund_request → build Recommendation → HumanApprovalService.request_approval()
                            → write state.human_decision
Step 3: Generate Response    [ResponseAgent]  ← reads state.human_decision if present
```

---

## ResponseAgent Behavior Change

When `state.human_decision` is present, the ResponseAgent uses `state.human_decision.decision` (not `state.policy_evaluation.final_decision`) to determine the outcome:

| `human_decision.decision` | ResponseAgent behavior                                                             |
| ------------------------- | ---------------------------------------------------------------------------------- |
| `"approve"`               | Generate refund confirmation message                                               |
| `"reject"`                | Generate polite decline message; do NOT reveal the agent's original recommendation |

---

## Non-Refund Pass-Through

No changes to step timing, content, or audit behavior for non-refund intents. `state.human_decision` remains `None`. `WorkflowState.agent_log` does not include an approval step entry.

---

## Audit Log Step

After `request_approval()` returns, the workflow logs the gate outcome to `WorkflowState.agent_log`:

```
[timestamp] HumanApproval: decision={decision} overrides_recommendation={overrides_recommendation}
```
