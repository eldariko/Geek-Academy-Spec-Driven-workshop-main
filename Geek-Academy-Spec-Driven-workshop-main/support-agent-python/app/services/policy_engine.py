"""Policy evaluation engine"""
from app.models import ClassificationResult, PolicyEvaluation, PolicyMatch
from app.services import HandbookService
from typing import Optional
from datetime import datetime, timedelta


class PolicyRule:
    """Base class for policy rules"""
    
    def evaluate(self, context: Optional[dict] = None) -> PolicyMatch:
        """Evaluate if this rule applies and return decision
        
        Args:
            context: Customer context dict with details
        
        Returns:
            PolicyMatch with evaluation result
        """
        raise NotImplementedError


class FirstMonthRefundRule(PolicyRule):
    """Refund eligible if account < 30 days and product unused"""
    
    def evaluate(self, context: Optional[dict] = None) -> Optional[PolicyMatch]:
        if not context:
            return None
        
        account_created_date = context.get("account_created_date")
        if not account_created_date:
            return None
        
        # Check if account is less than 30 days old
        if isinstance(account_created_date, str):
            try:
                account_created = datetime.fromisoformat(account_created_date)
            except ValueError:
                return None
        else:
            account_created = account_created_date
        
        days_old = (datetime.now() - account_created).days
        
        if days_old <= 30:
            return PolicyMatch(
                rule_name="first_month_refund",
                rule_category="refund",
                matches=True,
                decision="APPROVE",
                rationale=f"Account is only {days_old} days old. New accounts get full refund if unused.",
                handbook_reference="'We're generally pretty flexible on refunds in the first month. If someone signed up, didn't use it, and asks within ~30 days, just do it.'"
            )
        
        return None


class BillingErrorRefundRule(PolicyRule):
    """Refund approved for double charge, wrong amount, or charged after cancellation"""
    
    def evaluate(self, context: Optional[dict] = None) -> Optional[PolicyMatch]:
        if not context:
            return None
        
        # Check for billing error signals
        error_type = context.get("billing_error_type")
        if not error_type:
            return None
        
        error_types = {"double_charge", "wrong_amount", "charged_after_cancellation"}
        
        if error_type in error_types:
            return PolicyMatch(
                rule_name="billing_error_refund",
                rule_category="refund",
                matches=True,
                decision="APPROVE",
                rationale=f"Billing error detected ({error_type}). Refund approved with apology.",
                handbook_reference="'Obvious billing error on our side (double charge, wrong amount, charged after cancellation). Refund and apologize, no drama.'"
            )
        
        return None


class ServiceOutageRefundRule(PolicyRule):
    """Refund approved if service outage occurred during billing period"""
    
    def evaluate(self, context: Optional[dict] = None) -> Optional[PolicyMatch]:
        if not context:
            return None
        
        has_outage = context.get("service_outage_during_period", False)
        
        if has_outage:
            return PolicyMatch(
                rule_name="service_outage_refund",
                rule_category="refund",
                matches=True,
                decision="APPROVE",
                rationale="Service outage recorded during customer's billing period. Refund for affected period.",
                handbook_reference="'There was a real service outage during their billing period and they couldn't use the product.'"
            )
        
        return None


class OnePerYearRule(PolicyRule):
    """Goodwill refund limit: only one goodwill refund per customer per year"""
    
    def evaluate(self, context: Optional[dict] = None) -> Optional[PolicyMatch]:
        if not context:
            return None
        
        previous_goodwill_refund_date = context.get("previous_goodwill_refund_date")
        if not previous_goodwill_refund_date:
            # No previous goodwill refund, so this rule doesn't apply
            return None
        
        # Parse the date
        if isinstance(previous_goodwill_refund_date, str):
            try:
                refund_date = datetime.fromisoformat(previous_goodwill_refund_date)
            except ValueError:
                return None
        else:
            refund_date = previous_goodwill_refund_date
        
        # Check if within 12 months
        months_since = (datetime.now() - refund_date).days / 30.44  # Average days per month
        
        if months_since < 12:
            # Only applies to goodwill refunds (not billing errors)
            current_refund_type = context.get("current_refund_type", "goodwill")
            if current_refund_type == "goodwill":
                return PolicyMatch(
                    rule_name="one_per_year_limit",
                    rule_category="refund",
                    matches=True,
                    decision="DENY",
                    rationale=f"Customer already received goodwill refund {months_since:.0f} months ago. Limit is one per year.",
                    handbook_reference="'Customer has already had a refund within the past year. Our informal rule is one goodwill refund per customer per year.'"
                )
        
        return None


class ForgotToCancelRule(PolicyRule):
    """For multi-month refund requests, only offer most recent month if polite"""
    
    def evaluate(self, context: Optional[dict] = None) -> Optional[PolicyMatch]:
        if not context:
            return None
        
        months_charged_before_cancel = context.get("months_charged_before_cancel", 0)
        tone = context.get("tone", "neutral")
        
        if months_charged_before_cancel > 1:
            if tone == "polite" or tone == "neutral":
                return PolicyMatch(
                    rule_name="forgot_to_cancel_goodwill",
                    rule_category="refund",
                    matches=True,
                    decision="APPROVE",
                    rationale=f"Customer forgot to cancel for {months_charged_before_cancel} months. Offering refund for most recent month only as goodwill gesture.",
                    handbook_reference="'Best I'll usually do is refund the most recent month as a goodwill gesture if they're otherwise polite.'"
                )
            else:
                return PolicyMatch(
                    rule_name="forgot_to_cancel_denied",
                    rule_category="refund",
                    matches=True,
                    decision="DENY",
                    rationale=f"Customer forgot to cancel for {months_charged_before_cancel} months. No retroactive refunds policy.",
                    handbook_reference="'We don't do retroactive refunds for forgetting.'"
                )
        
        return None


class PolicyEngine:
    """Core policy evaluation engine"""
    
    def __init__(self, handbook_service: HandbookService):
        """Initialize policy engine
        
        Args:
            handbook_service: HandbookService instance for policy lookups
        """
        self.handbook = handbook_service
    
    def evaluate(self, classification: ClassificationResult, handbook_context: Optional[dict] = None) -> PolicyEvaluation:
        """Evaluate policy based on classification
        
        Args:
            classification: ClassificationResult from classifier
            handbook_context: Optional context dict with customer details
        
        Returns:
            PolicyEvaluation with decision and applied rules
        """
        intent = classification.classified_intent
        request_id = classification.request_id
        
        # Route to appropriate evaluation method
        if intent == "simple_question":
            return self._evaluate_simple_question(request_id)
        elif intent == "refund_request":
            return self._evaluate_refund_request(request_id, handbook_context)
        elif intent == "cancellation_request":
            return self._evaluate_cancellation(request_id)
        elif intent == "escalation_needed":
            return PolicyEvaluation(
                request_id=request_id,
                intent=intent,
                final_decision="ESCALATE",
                escalation_reason=classification.escalation_reason
            )
        else:
            # Unknown intent
            return PolicyEvaluation(
                request_id=request_id,
                intent=intent,
                final_decision="ESCALATE",
                escalation_reason="unknown_intent"
            )
    
    def _evaluate_simple_question(self, request_id: str) -> PolicyEvaluation:
        """Evaluate simple question — always approve handbook lookup
        
        Args:
            request_id: Request ID for tracking
        
        Returns:
            PolicyEvaluation with APPROVE decision
        """
        return PolicyEvaluation(
            request_id=request_id,
            intent="simple_question",
            final_decision="APPROVE",
            evaluated_rules=[
                PolicyMatch(
                    rule_name="simple_question_approved",
                    rule_category="general",
                    matches=True,
                    decision="APPROVE",
                    rationale="Simple questions are always answered with handbook information",
                    handbook_reference="General support policy"
                )
            ]
        )
    
    def _evaluate_refund_request(self, request_id: str, context: Optional[dict] = None) -> PolicyEvaluation:
        """Evaluate refund request against handbook rules
        
        Args:
            request_id: Request ID for tracking
            context: Customer context dict
        
        Returns:
            PolicyEvaluation with refund decision
        """
        if not context:
            # If no context provided, ask for clarification
            return PolicyEvaluation(
                request_id=request_id,
                intent="refund_request",
                final_decision="NEEDS_CLARIFICATION",
                clarification_needed_fields=["charge_date", "charge_amount"],
                evaluated_rules=[]
            )
        
        # Evaluate all refund rules in priority order
        rules = [
            FirstMonthRefundRule(),
            BillingErrorRefundRule(),
            ServiceOutageRefundRule(),
            OnePerYearRule(),
            ForgotToCancelRule(),
        ]
        
        evaluated_rules = []
        final_decision = "NEEDS_CLARIFICATION"
        should_apologize = False
        should_mention_timeline = False
        escalation_reason = None
        
        for rule in rules:
            result = rule.evaluate(context)
            if result:
                evaluated_rules.append(result)
                
                if result.decision == "APPROVE":
                    final_decision = "APPROVE"
                    should_mention_timeline = True
                    # Check if this is a billing error (requires apology)
                    if result.rule_name == "billing_error_refund":
                        should_apologize = True
                    break  # First applicable rule wins
                elif result.decision == "DENY":
                    final_decision = "DENY"
                    break  # Deny rules are final
        
        # If no rules matched, need more info or escalate
        if not evaluated_rules:
            final_decision = "NEEDS_CLARIFICATION"
            clarification_fields = ["charge_date", "charge_amount"]
            
            # Check for context that might indicate special handling needed
            if context.get("tone") == "abusive" or context.get("repeated_contacts", 0) >= 3:
                final_decision = "ESCALATE"
                escalation_reason = "Customer tone or contact pattern requires escalation"
            elif context.get("billing_amount", 0) > 100:
                final_decision = "ESCALATE"
                escalation_reason = "High-value billing dispute (>$100) requires escalation"
        
        return PolicyEvaluation(
            request_id=request_id,
            intent="refund_request",
            final_decision=final_decision,
            clarification_needed_fields=["charge_date", "charge_amount"] if final_decision == "NEEDS_CLARIFICATION" else [],
            evaluated_rules=evaluated_rules,
            should_apologize=should_apologize,
            should_mention_timeline=should_mention_timeline,
            escalation_reason=escalation_reason
        )
    
    def _evaluate_cancellation(self, request_id: str) -> PolicyEvaluation:
        """Evaluate cancellation request
        
        Args:
            request_id: Request ID for tracking
        
        Returns:
            PolicyEvaluation with cancellation decision
        """
        return PolicyEvaluation(
            request_id=request_id,
            intent="cancellation_request",
            final_decision="APPROVE",
            evaluated_rules=[
                PolicyMatch(
                    rule_name="cancellation_approved",
                    rule_category="cancellation",
                    matches=True,
                    decision="APPROVE",
                    rationale="Cancellation requests are always processed",
                    handbook_reference="Cancellations — This one is simpler. If a customer wants to cancel, cancel them."
                )
            ]
        )
