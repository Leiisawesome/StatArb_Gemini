"""
Academic-Industry Collaboration Framework
==========================================

Framework for facilitating collaboration between academic institutions and
trading firms, including partnership management, strategy submission, and
evaluation workflows.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

from .academic_strategy_registry import AcademicTemplate, AcademicStrategyRegistry, ResearchField


class PartnershipType(Enum):
    """Types of academic-industry partnerships"""
    RESEARCH_COLLABORATION = "research_collaboration"
    STRATEGY_VALIDATION = "strategy_validation"
    DATA_SHARING = "data_sharing"
    JOINT_DEVELOPMENT = "joint_development"
    LICENSING = "licensing"
    CONSULTING = "consulting"


class PartnershipStatus(Enum):
    """Status of partnerships"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    COMPLETED = "completed"


class DataSharingLevel(Enum):
    """Levels of data sharing in partnerships"""
    NONE = "none"
    SUMMARY_ONLY = "summary_only"
    AGGREGATED_DATA = "aggregated_data"
    DETAILED_DATA = "detailed_data"
    FULL_ACCESS = "full_access"


class SubmissionStatus(Enum):
    """Status of academic strategy submissions"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    RETIRED = "retired"


@dataclass
class PartnershipTerms:
    """Terms and conditions for academic-industry partnerships"""
    partnership_type: PartnershipType
    duration_months: int
    data_sharing_level: DataSharingLevel
    intellectual_property_rights: str
    publication_rights: str
    revenue_sharing_percentage: float = 0.0
    exclusivity_period_months: int = 0
    
    # Data sharing terms
    data_access_restrictions: List[str] = field(default_factory=list)
    data_usage_limitations: List[str] = field(default_factory=list)
    
    # Performance requirements
    min_performance_thresholds: Dict[str, float] = field(default_factory=dict)
    reporting_frequency: str = "monthly"
    
    # Compliance requirements
    regulatory_compliance: List[str] = field(default_factory=list)
    audit_requirements: List[str] = field(default_factory=list)


@dataclass
class ResearchPartnership:
    """Academic-industry research partnership"""
    partnership_id: str
    academic_institution: str
    trading_firm: str
    contact_academic: str
    contact_industry: str
    
    # Partnership details
    partnership_terms: PartnershipTerms
    research_focus_areas: List[ResearchField]
    start_date: str
    end_date: Optional[str] = None
    
    # Status and tracking
    status: PartnershipStatus = PartnershipStatus.PENDING
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Partnership metrics
    strategies_submitted: int = 0
    strategies_approved: int = 0
    strategies_deployed: int = 0
    total_performance: Dict[str, float] = field(default_factory=dict)
    
    # Documents and agreements
    legal_documents: List[str] = field(default_factory=list)
    technical_specifications: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'partnership_id': self.partnership_id,
            'academic_institution': self.academic_institution,
            'trading_firm': self.trading_firm,
            'contact_academic': self.contact_academic,
            'contact_industry': self.contact_industry,
            'partnership_terms': {
                'partnership_type': self.partnership_terms.partnership_type.value,
                'duration_months': self.partnership_terms.duration_months,
                'data_sharing_level': self.partnership_terms.data_sharing_level.value,
                'intellectual_property_rights': self.partnership_terms.intellectual_property_rights,
                'publication_rights': self.partnership_terms.publication_rights,
                'revenue_sharing_percentage': self.partnership_terms.revenue_sharing_percentage,
                'exclusivity_period_months': self.partnership_terms.exclusivity_period_months,
                'data_access_restrictions': self.partnership_terms.data_access_restrictions,
                'data_usage_limitations': self.partnership_terms.data_usage_limitations,
                'min_performance_thresholds': self.partnership_terms.min_performance_thresholds,
                'reporting_frequency': self.partnership_terms.reporting_frequency,
                'regulatory_compliance': self.partnership_terms.regulatory_compliance,
                'audit_requirements': self.partnership_terms.audit_requirements
            },
            'research_focus_areas': [field.value for field in self.research_focus_areas],
            'start_date': self.start_date,
            'end_date': self.end_date,
            'status': self.status.value,
            'created_date': self.created_date,
            'last_updated': self.last_updated,
            'strategies_submitted': self.strategies_submitted,
            'strategies_approved': self.strategies_approved,
            'strategies_deployed': self.strategies_deployed,
            'total_performance': self.total_performance,
            'legal_documents': self.legal_documents,
            'technical_specifications': self.technical_specifications
        }


@dataclass
class StrategySubmission:
    """Academic strategy submission for industry evaluation"""
    submission_id: str
    partnership_id: str
    academic_template_id: str
    submitter: str
    
    # Submission details
    submission_date: str = field(default_factory=lambda: datetime.now().isoformat())
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    priority_level: str = "normal"  # low, normal, high, urgent
    
    # Review and evaluation
    assigned_reviewer: Optional[str] = None
    review_start_date: Optional[str] = None
    review_completion_date: Optional[str] = None
    evaluation_results: Dict[str, Any] = field(default_factory=dict)
    
    # Testing and validation
    testing_start_date: Optional[str] = None
    testing_completion_date: Optional[str] = None
    testing_results: Dict[str, Any] = field(default_factory=dict)
    
    # Decision and feedback
    decision: Optional[str] = None
    decision_date: Optional[str] = None
    decision_rationale: Optional[str] = None
    feedback_to_academic: List[str] = field(default_factory=list)
    
    # Deployment tracking
    deployment_date: Optional[str] = None
    deployment_configuration: Dict[str, Any] = field(default_factory=dict)
    live_performance: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'submission_id': self.submission_id,
            'partnership_id': self.partnership_id,
            'academic_template_id': self.academic_template_id,
            'submitter': self.submitter,
            'submission_date': self.submission_date,
            'status': self.status.value,
            'priority_level': self.priority_level,
            'assigned_reviewer': self.assigned_reviewer,
            'review_start_date': self.review_start_date,
            'review_completion_date': self.review_completion_date,
            'evaluation_results': self.evaluation_results,
            'testing_start_date': self.testing_start_date,
            'testing_completion_date': self.testing_completion_date,
            'testing_results': self.testing_results,
            'decision': self.decision,
            'decision_date': self.decision_date,
            'decision_rationale': self.decision_rationale,
            'feedback_to_academic': self.feedback_to_academic,
            'deployment_date': self.deployment_date,
            'deployment_configuration': self.deployment_configuration,
            'live_performance': self.live_performance,
            'tags': self.tags,
            'notes': self.notes
        }


class AcademicIndustryCollaboration:
    """
    Framework for managing academic-industry collaboration and partnerships
    """
    
    def __init__(self, academic_registry: AcademicStrategyRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.academic_registry = academic_registry
        
        # Partnership management
        self.partnerships: Dict[str, ResearchPartnership] = {}
        self.submissions: Dict[str, StrategySubmission] = {}
        
        # Indexing for efficient queries
        self.partnerships_by_institution: Dict[str, List[str]] = {}
        self.partnerships_by_firm: Dict[str, List[str]] = {}
        self.partnerships_by_status: Dict[PartnershipStatus, List[str]] = {
            status: [] for status in PartnershipStatus
        }
        
        self.submissions_by_partnership: Dict[str, List[str]] = {}
        self.submissions_by_status: Dict[SubmissionStatus, List[str]] = {
            status: [] for status in SubmissionStatus
        }
        
        # Collaboration metrics
        self.collaboration_metrics = {
            'total_partnerships': 0,
            'active_partnerships': 0,
            'total_submissions': 0,
            'successful_deployments': 0,
            'average_review_time_days': 0.0,
            'average_success_rate': 0.0
        }
        
        self.logger.info("Academic-Industry Collaboration Framework initialized")
    
    def create_research_partnership(self,
                                  academic_institution: str,
                                  trading_firm: str,
                                  contact_academic: str,
                                  contact_industry: str,
                                  partnership_terms: PartnershipTerms,
                                  research_focus_areas: List[ResearchField],
                                  start_date: Optional[str] = None) -> str:
        """
        Create a new research partnership between academic institution and trading firm
        """
        try:
            # Generate partnership ID
            partnership_id = f"partnership_{academic_institution.replace(' ', '_')}_{trading_firm.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Use provided start date or current date
            if start_date is None:
                start_date = datetime.now().isoformat()
            
            # Calculate end date based on duration
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = start_dt + timedelta(days=partnership_terms.duration_months * 30)
            end_date = end_dt.isoformat()
            
            # Create partnership
            partnership = ResearchPartnership(
                partnership_id=partnership_id,
                academic_institution=academic_institution,
                trading_firm=trading_firm,
                contact_academic=contact_academic,
                contact_industry=contact_industry,
                partnership_terms=partnership_terms,
                research_focus_areas=research_focus_areas,
                start_date=start_date,
                end_date=end_date,
                status=PartnershipStatus.PENDING
            )
            
            # Store partnership
            self.partnerships[partnership_id] = partnership
            
            # Update indexes
            self._update_partnership_indexes(partnership)
            
            # Update metrics
            self._update_collaboration_metrics()
            
            self.logger.info(f"Research partnership created: {partnership_id}")
            self.logger.info(f"Between {academic_institution} and {trading_firm}")
            self.logger.info(f"Focus areas: {[field.value for field in research_focus_areas]}")
            
            return partnership_id
            
        except Exception as e:
            self.logger.error(f"Failed to create research partnership: {e}")
            raise
    
    def submit_academic_strategy(self,
                                partnership_id: str,
                                academic_template_id: str,
                                submitter: str,
                                priority_level: str = "normal",
                                tags: Optional[List[str]] = None) -> str:
        """
        Submit academic strategy for industry evaluation
        """
        try:
            if partnership_id not in self.partnerships:
                raise ValueError(f"Partnership {partnership_id} not found")
            
            partnership = self.partnerships[partnership_id]
            
            if partnership.status != PartnershipStatus.ACTIVE:
                raise ValueError(f"Partnership {partnership_id} is not active (status: {partnership.status.value})")
            
            # Verify academic template exists
            academic_template = self.academic_registry.get_academic_strategy(academic_template_id)
            if not academic_template:
                raise ValueError(f"Academic template {academic_template_id} not found")
            
            # Generate submission ID
            submission_id = f"submission_{partnership_id}_{academic_template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create submission
            submission = StrategySubmission(
                submission_id=submission_id,
                partnership_id=partnership_id,
                academic_template_id=academic_template_id,
                submitter=submitter,
                priority_level=priority_level,
                tags=tags or []
            )
            
            # Store submission
            self.submissions[submission_id] = submission
            
            # Update indexes
            self._update_submission_indexes(submission)
            
            # Update partnership metrics
            partnership.strategies_submitted += 1
            partnership.last_updated = datetime.now().isoformat()
            
            # Update collaboration metrics
            self._update_collaboration_metrics()
            
            self.logger.info(f"Academic strategy submitted: {submission_id}")
            self.logger.info(f"Template: {academic_template_id}, Submitter: {submitter}")
            
            return submission_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit academic strategy: {e}")
            raise
    
    def assign_reviewer(self, submission_id: str, reviewer: str) -> bool:
        """Assign reviewer to strategy submission"""
        try:
            if submission_id not in self.submissions:
                raise ValueError(f"Submission {submission_id} not found")
            
            submission = self.submissions[submission_id]
            
            if submission.status != SubmissionStatus.SUBMITTED:
                raise ValueError(f"Submission {submission_id} is not in submitted status")
            
            # Assign reviewer and update status
            submission.assigned_reviewer = reviewer
            submission.review_start_date = datetime.now().isoformat()
            submission.status = SubmissionStatus.UNDER_REVIEW
            
            # Update indexes
            self._update_submission_indexes(submission)
            
            self.logger.info(f"Reviewer {reviewer} assigned to submission {submission_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to assign reviewer: {e}")
            return False
    
    def complete_review(self,
                       submission_id: str,
                       evaluation_results: Dict[str, Any],
                       decision: str,
                       rationale: str,
                       feedback: List[str]) -> bool:
        """Complete review of strategy submission"""
        try:
            if submission_id not in self.submissions:
                raise ValueError(f"Submission {submission_id} not found")
            
            submission = self.submissions[submission_id]
            
            if submission.status != SubmissionStatus.UNDER_REVIEW:
                raise ValueError(f"Submission {submission_id} is not under review")
            
            # Complete review
            submission.review_completion_date = datetime.now().isoformat()
            submission.evaluation_results = evaluation_results
            submission.decision = decision
            submission.decision_date = datetime.now().isoformat()
            submission.decision_rationale = rationale
            submission.feedback_to_academic = feedback
            
            # Update status based on decision
            if decision.lower() == "approved":
                submission.status = SubmissionStatus.APPROVED
                # Update partnership metrics
                partnership = self.partnerships[submission.partnership_id]
                partnership.strategies_approved += 1
            elif decision.lower() == "rejected":
                submission.status = SubmissionStatus.REJECTED
            else:
                submission.status = SubmissionStatus.SUBMITTED  # Return to submitted for clarification
            
            # Update indexes
            self._update_submission_indexes(submission)
            
            # Update collaboration metrics
            self._update_collaboration_metrics()
            
            self.logger.info(f"Review completed for submission {submission_id}: {decision}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete review: {e}")
            return False
    
    def activate_partnership(self, partnership_id: str) -> bool:
        """Activate a pending partnership"""
        try:
            if partnership_id not in self.partnerships:
                raise ValueError(f"Partnership {partnership_id} not found")
            
            partnership = self.partnerships[partnership_id]
            
            if partnership.status != PartnershipStatus.PENDING:
                raise ValueError(f"Partnership {partnership_id} is not pending (status: {partnership.status.value})")
            
            partnership.status = PartnershipStatus.ACTIVE
            partnership.last_updated = datetime.now().isoformat()
            
            # Update indexes
            self._update_partnership_indexes(partnership)
            self._update_collaboration_metrics()
            
            self.logger.info(f"Partnership activated: {partnership_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to activate partnership: {e}")
            return False
    
    def get_partnerships_by_institution(self, institution: str) -> List[ResearchPartnership]:
        """Get partnerships by academic institution"""
        partnership_ids = self.partnerships_by_institution.get(institution, [])
        return [self.partnerships[pid] for pid in partnership_ids if pid in self.partnerships]
    
    def get_partnerships_by_firm(self, firm: str) -> List[ResearchPartnership]:
        """Get partnerships by trading firm"""
        partnership_ids = self.partnerships_by_firm.get(firm, [])
        return [self.partnerships[pid] for pid in partnership_ids if pid in self.partnerships]
    
    def get_partnerships_by_status(self, status: PartnershipStatus) -> List[ResearchPartnership]:
        """Get partnerships by status"""
        partnership_ids = self.partnerships_by_status.get(status, [])
        return [self.partnerships[pid] for pid in partnership_ids if pid in self.partnerships]
    
    def get_submissions_by_partnership(self, partnership_id: str) -> List[StrategySubmission]:
        """Get submissions by partnership"""
        submission_ids = self.submissions_by_partnership.get(partnership_id, [])
        return [self.submissions[sid] for sid in submission_ids if sid in self.submissions]
    
    def get_submissions_by_status(self, status: SubmissionStatus) -> List[StrategySubmission]:
        """Get submissions by status"""
        submission_ids = self.submissions_by_status.get(status, [])
        return [self.submissions[sid] for sid in submission_ids if sid in self.submissions]
    
    def get_partnership_performance_summary(self, partnership_id: str) -> Dict[str, Any]:
        """Get comprehensive partnership performance summary"""
        try:
            if partnership_id not in self.partnerships:
                raise ValueError(f"Partnership {partnership_id} not found")
            
            partnership = self.partnerships[partnership_id]
            submissions = self.get_submissions_by_partnership(partnership_id)
            
            # Calculate performance metrics
            total_submissions = len(submissions)
            approved_submissions = len([s for s in submissions if s.status == SubmissionStatus.APPROVED])
            deployed_submissions = len([s for s in submissions if s.status == SubmissionStatus.DEPLOYED])
            rejected_submissions = len([s for s in submissions if s.status == SubmissionStatus.REJECTED])
            
            approval_rate = (approved_submissions / total_submissions) if total_submissions > 0 else 0.0
            deployment_rate = (deployed_submissions / total_submissions) if total_submissions > 0 else 0.0
            
            # Calculate average review time
            completed_reviews = [s for s in submissions if s.review_completion_date and s.review_start_date]
            if completed_reviews:
                review_times = []
                for s in completed_reviews:
                    start = datetime.fromisoformat(s.review_start_date)
                    end = datetime.fromisoformat(s.review_completion_date)
                    review_times.append((end - start).days)
                avg_review_time = sum(review_times) / len(review_times)
            else:
                avg_review_time = 0.0
            
            return {
                'partnership_info': {
                    'partnership_id': partnership_id,
                    'academic_institution': partnership.academic_institution,
                    'trading_firm': partnership.trading_firm,
                    'status': partnership.status.value,
                    'start_date': partnership.start_date,
                    'research_focus_areas': [field.value for field in partnership.research_focus_areas]
                },
                'submission_metrics': {
                    'total_submissions': total_submissions,
                    'approved_submissions': approved_submissions,
                    'deployed_submissions': deployed_submissions,
                    'rejected_submissions': rejected_submissions,
                    'pending_review': len([s for s in submissions if s.status in [SubmissionStatus.SUBMITTED, SubmissionStatus.UNDER_REVIEW]]),
                    'approval_rate': approval_rate,
                    'deployment_rate': deployment_rate
                },
                'timing_metrics': {
                    'average_review_time_days': avg_review_time,
                    'fastest_review_days': min([
                        (datetime.fromisoformat(s.review_completion_date) - datetime.fromisoformat(s.review_start_date)).days
                        for s in completed_reviews
                    ]) if completed_reviews else 0,
                    'slowest_review_days': max([
                        (datetime.fromisoformat(s.review_completion_date) - datetime.fromisoformat(s.review_start_date)).days
                        for s in completed_reviews
                    ]) if completed_reviews else 0
                },
                'performance_data': partnership.total_performance,
                'recent_activity': self._get_recent_partnership_activity(partnership_id)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get partnership performance summary: {e}")
            return {}
    
    def get_collaboration_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive collaboration dashboard"""
        try:
            # Overall statistics
            total_partnerships = len(self.partnerships)
            active_partnerships = len(self.get_partnerships_by_status(PartnershipStatus.ACTIVE))
            total_submissions = len(self.submissions)
            
            # Partnership distribution
            partnership_by_status = {
                status.value: len(partnership_ids) 
                for status, partnership_ids in self.partnerships_by_status.items()
            }
            
            # Submission distribution
            submission_by_status = {
                status.value: len(submission_ids)
                for status, submission_ids in self.submissions_by_status.items()
            }
            
            # Top performing partnerships
            partnership_performance = []
            for partnership_id, partnership in self.partnerships.items():
                performance_summary = self.get_partnership_performance_summary(partnership_id)
                if performance_summary:
                    partnership_performance.append({
                        'partnership_id': partnership_id,
                        'institution': partnership.academic_institution,
                        'firm': partnership.trading_firm,
                        'approval_rate': performance_summary['submission_metrics']['approval_rate'],
                        'deployment_rate': performance_summary['submission_metrics']['deployment_rate'],
                        'total_submissions': performance_summary['submission_metrics']['total_submissions']
                    })
            
            # Sort by approval rate
            partnership_performance.sort(key=lambda x: x['approval_rate'], reverse=True)
            
            # Recent activity
            recent_submissions = sorted(
                self.submissions.values(),
                key=lambda s: s.submission_date,
                reverse=True
            )[:10]
            
            return {
                'overview': {
                    'total_partnerships': total_partnerships,
                    'active_partnerships': active_partnerships,
                    'total_submissions': total_submissions,
                    'last_updated': datetime.now().isoformat()
                },
                'partnership_distribution': partnership_by_status,
                'submission_distribution': submission_by_status,
                'top_partnerships': partnership_performance[:5],
                'recent_submissions': [
                    {
                        'submission_id': s.submission_id,
                        'partnership_id': s.partnership_id,
                        'academic_template_id': s.academic_template_id,
                        'submitter': s.submitter,
                        'submission_date': s.submission_date,
                        'status': s.status.value
                    }
                    for s in recent_submissions
                ],
                'collaboration_metrics': self.collaboration_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate collaboration dashboard: {e}")
            return {}
    
    # Private helper methods
    def _update_partnership_indexes(self, partnership: ResearchPartnership):
        """Update partnership indexes"""
        partnership_id = partnership.partnership_id
        
        # Update institution index
        institution = partnership.academic_institution
        if institution not in self.partnerships_by_institution:
            self.partnerships_by_institution[institution] = []
        if partnership_id not in self.partnerships_by_institution[institution]:
            self.partnerships_by_institution[institution].append(partnership_id)
        
        # Update firm index
        firm = partnership.trading_firm
        if firm not in self.partnerships_by_firm:
            self.partnerships_by_firm[firm] = []
        if partnership_id not in self.partnerships_by_firm[firm]:
            self.partnerships_by_firm[firm].append(partnership_id)
        
        # Update status index
        # Remove from old status
        for status_list in self.partnerships_by_status.values():
            if partnership_id in status_list:
                status_list.remove(partnership_id)
        
        # Add to new status
        self.partnerships_by_status[partnership.status].append(partnership_id)
    
    def _update_submission_indexes(self, submission: StrategySubmission):
        """Update submission indexes"""
        submission_id = submission.submission_id
        
        # Update partnership index
        partnership_id = submission.partnership_id
        if partnership_id not in self.submissions_by_partnership:
            self.submissions_by_partnership[partnership_id] = []
        if submission_id not in self.submissions_by_partnership[partnership_id]:
            self.submissions_by_partnership[partnership_id].append(submission_id)
        
        # Update status index
        # Remove from old status
        for status_list in self.submissions_by_status.values():
            if submission_id in status_list:
                status_list.remove(submission_id)
        
        # Add to new status
        self.submissions_by_status[submission.status].append(submission_id)
    
    def _update_collaboration_metrics(self):
        """Update collaboration metrics"""
        try:
            self.collaboration_metrics['total_partnerships'] = len(self.partnerships)
            self.collaboration_metrics['active_partnerships'] = len(self.get_partnerships_by_status(PartnershipStatus.ACTIVE))
            self.collaboration_metrics['total_submissions'] = len(self.submissions)
            self.collaboration_metrics['successful_deployments'] = len(self.get_submissions_by_status(SubmissionStatus.DEPLOYED))
            
            # Calculate average review time
            completed_reviews = [
                s for s in self.submissions.values() 
                if s.review_completion_date and s.review_start_date
            ]
            
            if completed_reviews:
                review_times = []
                for s in completed_reviews:
                    start = datetime.fromisoformat(s.review_start_date)
                    end = datetime.fromisoformat(s.review_completion_date)
                    review_times.append((end - start).days)
                self.collaboration_metrics['average_review_time_days'] = sum(review_times) / len(review_times)
            
            # Calculate success rate
            total_reviewed = len([s for s in self.submissions.values() if s.decision])
            successful = len([s for s in self.submissions.values() if s.decision and s.decision.lower() == "approved"])
            
            if total_reviewed > 0:
                self.collaboration_metrics['average_success_rate'] = successful / total_reviewed
            
        except Exception as e:
            self.logger.error(f"Failed to update collaboration metrics: {e}")
    
    def _get_recent_partnership_activity(self, partnership_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent activity for partnership"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            submissions = self.get_submissions_by_partnership(partnership_id)
            
            recent_activity = []
            for submission in submissions:
                submission_date = datetime.fromisoformat(submission.submission_date)
                if submission_date >= cutoff_date:
                    recent_activity.append({
                        'type': 'submission',
                        'date': submission.submission_date,
                        'description': f"Strategy {submission.academic_template_id} submitted by {submission.submitter}",
                        'status': submission.status.value
                    })
                
                if submission.review_completion_date:
                    review_date = datetime.fromisoformat(submission.review_completion_date)
                    if review_date >= cutoff_date:
                        recent_activity.append({
                            'type': 'review_completed',
                            'date': submission.review_completion_date,
                            'description': f"Review completed for {submission.academic_template_id}: {submission.decision}",
                            'status': submission.status.value
                        })
            
            # Sort by date (most recent first)
            recent_activity.sort(key=lambda x: x['date'], reverse=True)
            
            return recent_activity
            
        except Exception as e:
            self.logger.error(f"Failed to get recent partnership activity: {e}")
            return []
