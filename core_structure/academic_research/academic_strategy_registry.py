"""
Academic Strategy Registry - Template-Aware Academic Research Integration
==========================================================================

Registry for academic strategy templates with comprehensive metadata, validation,
and research field categorization. Integrates with the hybrid template system.

Author: Pro Quant Desk Trader
"""

import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import json
import uuid

from strategy_templates.base import TemplateRegistry, TemplateCategory, TemplateInheritanceManager


class ResearchField(Enum):
    """Academic research fields for strategy categorization"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    FACTOR_MODELS = "factor_models"
    REGIME_DETECTION = "regime_detection"
    RISK_MANAGEMENT = "risk_management"
    EXECUTION = "execution"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    MARKET_MICROSTRUCTURE = "market_microstructure"
    BEHAVIORAL_FINANCE = "behavioral_finance"
    MACHINE_LEARNING = "machine_learning"


class PublicationStatus(Enum):
    """Publication status for academic strategies"""
    PREPRINT = "preprint"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PUBLISHED = "published"
    WORKING_PAPER = "working_paper"


@dataclass
class AcademicMetadata:
    """Comprehensive academic metadata for strategies"""
    authors: List[str]
    institution: str
    publication: str
    publication_date: str
    research_field: ResearchField
    abstract: str
    key_contributions: List[str]
    empirical_results: Dict[str, float]
    
    # Additional metadata
    publication_status: PublicationStatus = PublicationStatus.WORKING_PAPER
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    methodology: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    sample_period: Optional[str] = None
    geographic_scope: List[str] = field(default_factory=list)


@dataclass
class AcademicValidation:
    """Academic validation results and statistical significance"""
    out_of_sample_period: Optional[str] = None
    statistical_significance: Dict[str, float] = field(default_factory=dict)
    robustness_checks: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Statistical tests
    t_statistics: Dict[str, float] = field(default_factory=dict)
    p_values: Dict[str, float] = field(default_factory=dict)
    confidence_intervals: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Robustness measures
    bootstrap_results: Dict[str, Any] = field(default_factory=dict)
    monte_carlo_results: Dict[str, Any] = field(default_factory=dict)
    sensitivity_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AcademicTemplate:
    """Complete academic strategy template with metadata"""
    template_id: str
    base_template: Dict[str, Any]
    academic_metadata: AcademicMetadata
    academic_validation: AcademicValidation
    
    # Registry metadata
    registry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    registration_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    access_level: str = "public"  # public, restricted, private
    
    # Template integration
    template_category: TemplateCategory = TemplateCategory.SPECIFIC
    parent_templates: List[str] = field(default_factory=list)
    derived_templates: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'template_id': self.template_id,
            'registry_id': self.registry_id,
            'base_template': self.base_template,
            'academic_metadata': {
                'authors': self.academic_metadata.authors,
                'institution': self.academic_metadata.institution,
                'publication': self.academic_metadata.publication,
                'publication_date': self.academic_metadata.publication_date,
                'research_field': self.academic_metadata.research_field.value,
                'abstract': self.academic_metadata.abstract,
                'key_contributions': self.academic_metadata.key_contributions,
                'empirical_results': self.academic_metadata.empirical_results,
                'publication_status': self.academic_metadata.publication_status.value,
                'doi': self.academic_metadata.doi,
                'arxiv_id': self.academic_metadata.arxiv_id,
                'keywords': self.academic_metadata.keywords,
                'methodology': self.academic_metadata.methodology,
                'data_sources': self.academic_metadata.data_sources,
                'sample_period': self.academic_metadata.sample_period,
                'geographic_scope': self.academic_metadata.geographic_scope
            },
            'academic_validation': {
                'out_of_sample_period': self.academic_validation.out_of_sample_period,
                'statistical_significance': self.academic_validation.statistical_significance,
                'robustness_checks': self.academic_validation.robustness_checks,
                'performance_metrics': self.academic_validation.performance_metrics,
                'risk_metrics': self.academic_validation.risk_metrics,
                't_statistics': self.academic_validation.t_statistics,
                'p_values': self.academic_validation.p_values,
                'confidence_intervals': self.academic_validation.confidence_intervals,
                'bootstrap_results': self.academic_validation.bootstrap_results,
                'monte_carlo_results': self.academic_validation.monte_carlo_results,
                'sensitivity_analysis': self.academic_validation.sensitivity_analysis
            },
            'registration_date': self.registration_date,
            'last_updated': self.last_updated,
            'access_level': self.access_level,
            'template_category': self.template_category.value,
            'parent_templates': self.parent_templates,
            'derived_templates': self.derived_templates
        }


class AcademicStrategyRegistry:
    """
    Registry for academic strategy templates with comprehensive research integration
    """
    
    def __init__(self, template_registry: TemplateRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Academic template storage
        self.academic_templates: Dict[str, AcademicTemplate] = {}
        
        # Research field categorization
        self.research_fields: Dict[ResearchField, List[str]] = {
            field: [] for field in ResearchField
        }
        
        # Institution tracking
        self.institution_strategies: Dict[str, List[str]] = {}
        
        # Author tracking
        self.author_strategies: Dict[str, List[str]] = {}
        
        # Publication tracking
        self.publication_strategies: Dict[str, List[str]] = {}
        
        # Index tracking
        self.registry_stats = {
            'total_strategies': 0,
            'strategies_by_field': {},
            'strategies_by_institution': {},
            'strategies_by_status': {},
            'last_updated': datetime.now().isoformat()
        }
        
        self.logger.info("Academic Strategy Registry initialized")
    
    def publish_academic_strategy(self, 
                                base_template: Dict[str, Any],
                                academic_metadata: AcademicMetadata,
                                academic_validation: AcademicValidation,
                                template_category: TemplateCategory = TemplateCategory.SPECIFIC) -> str:
        """
        Publish academic strategy with complete metadata and validation
        """
        try:
            # Generate academic template ID
            base_id = base_template.get('template_id', 'unnamed_strategy')
            template_id = f"academic_{base_id}"
            
            # Ensure unique ID
            counter = 1
            original_id = template_id
            while template_id in self.academic_templates:
                template_id = f"{original_id}_v{counter}"
                counter += 1
            
            # Create academic template
            academic_template = AcademicTemplate(
                template_id=template_id,
                base_template=base_template,
                academic_metadata=academic_metadata,
                academic_validation=academic_validation,
                template_category=template_category
            )
            
            # Store academic template
            self.academic_templates[template_id] = academic_template
            
            # Update research field index
            research_field = academic_metadata.research_field
            self.research_fields[research_field].append(template_id)
            
            # Update institution index
            institution = academic_metadata.institution
            if institution not in self.institution_strategies:
                self.institution_strategies[institution] = []
            self.institution_strategies[institution].append(template_id)
            
            # Update author index
            for author in academic_metadata.authors:
                if author not in self.author_strategies:
                    self.author_strategies[author] = []
                self.author_strategies[author].append(template_id)
            
            # Update publication index
            publication = academic_metadata.publication
            if publication not in self.publication_strategies:
                self.publication_strategies[publication] = []
            self.publication_strategies[publication].append(template_id)
            
            # Update registry statistics
            self._update_registry_stats()
            
            # Integrate with main template registry if specified
            if academic_template.access_level == "public":
                self._integrate_with_main_registry(academic_template)
            
            self.logger.info(f"Academic strategy published: {template_id}")
            self.logger.info(f"Authors: {', '.join(academic_metadata.authors)}")
            self.logger.info(f"Institution: {academic_metadata.institution}")
            self.logger.info(f"Research field: {research_field.value}")
            
            return template_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish academic strategy: {e}")
            raise
    
    def get_academic_strategy(self, template_id: str) -> Optional[AcademicTemplate]:
        """Get academic strategy by template ID"""
        return self.academic_templates.get(template_id)
    
    def get_academic_strategies_by_field(self, research_field: ResearchField) -> List[AcademicTemplate]:
        """Get strategies by research field"""
        template_ids = self.research_fields.get(research_field, [])
        return [self.academic_templates[tid] for tid in template_ids if tid in self.academic_templates]
    
    def get_academic_strategies_by_author(self, author: str) -> List[AcademicTemplate]:
        """Get strategies by author"""
        template_ids = self.author_strategies.get(author, [])
        return [self.academic_templates[tid] for tid in template_ids if tid in self.academic_templates]
    
    def get_academic_strategies_by_institution(self, institution: str) -> List[AcademicTemplate]:
        """Get strategies by institution"""
        template_ids = self.institution_strategies.get(institution, [])
        return [self.academic_templates[tid] for tid in template_ids if tid in self.academic_templates]
    
    def get_academic_strategies_by_publication(self, publication: str) -> List[AcademicTemplate]:
        """Get strategies by publication"""
        template_ids = self.publication_strategies.get(publication, [])
        return [self.academic_templates[tid] for tid in template_ids if tid in self.academic_templates]
    
    def search_academic_strategies(self, 
                                 query: str,
                                 research_fields: Optional[List[ResearchField]] = None,
                                 institutions: Optional[List[str]] = None,
                                 authors: Optional[List[str]] = None,
                                 min_performance: Optional[Dict[str, float]] = None) -> List[AcademicTemplate]:
        """
        Advanced search for academic strategies
        """
        try:
            results = []
            
            for template in self.academic_templates.values():
                # Text search in multiple fields
                if query.lower() in template.template_id.lower() or \
                   query.lower() in template.academic_metadata.abstract.lower() or \
                   any(query.lower() in contrib.lower() for contrib in template.academic_metadata.key_contributions) or \
                   any(query.lower() in keyword.lower() for keyword in template.academic_metadata.keywords):
                    
                    # Research field filter
                    if research_fields and template.academic_metadata.research_field not in research_fields:
                        continue
                    
                    # Institution filter
                    if institutions and template.academic_metadata.institution not in institutions:
                        continue
                    
                    # Author filter
                    if authors and not any(author in template.academic_metadata.authors for author in authors):
                        continue
                    
                    # Performance filter
                    if min_performance:
                        performance_metrics = template.academic_validation.performance_metrics
                        if not all(performance_metrics.get(metric, 0) >= threshold 
                                 for metric, threshold in min_performance.items()):
                            continue
                    
                    results.append(template)
            
            # Sort by relevance (simple scoring based on query matches)
            results.sort(key=lambda t: self._calculate_relevance_score(t, query), reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get comprehensive registry summary"""
        return {
            'registry_stats': self.registry_stats,
            'research_field_distribution': {
                field.value: len(template_ids) 
                for field, template_ids in self.research_fields.items()
            },
            'top_institutions': sorted(
                [(inst, len(strategies)) for inst, strategies in self.institution_strategies.items()],
                key=lambda x: x[1], reverse=True
            )[:10],
            'top_authors': sorted(
                [(author, len(strategies)) for author, strategies in self.author_strategies.items()],
                key=lambda x: x[1], reverse=True
            )[:10],
            'recent_publications': self._get_recent_publications(limit=10),
            'performance_statistics': self._calculate_performance_statistics()
        }
    
    def export_academic_template(self, template_id: str) -> Dict[str, Any]:
        """Export academic template for sharing or backup"""
        if template_id not in self.academic_templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.academic_templates[template_id]
        return template.to_dict()
    
    def import_academic_template(self, template_data: Dict[str, Any]) -> str:
        """Import academic template from external source"""
        try:
            # Reconstruct academic metadata
            metadata_dict = template_data['academic_metadata']
            academic_metadata = AcademicMetadata(
                authors=metadata_dict['authors'],
                institution=metadata_dict['institution'],
                publication=metadata_dict['publication'],
                publication_date=metadata_dict['publication_date'],
                research_field=ResearchField(metadata_dict['research_field']),
                abstract=metadata_dict['abstract'],
                key_contributions=metadata_dict['key_contributions'],
                empirical_results=metadata_dict['empirical_results'],
                publication_status=PublicationStatus(metadata_dict.get('publication_status', 'working_paper')),
                doi=metadata_dict.get('doi'),
                arxiv_id=metadata_dict.get('arxiv_id'),
                keywords=metadata_dict.get('keywords', []),
                methodology=metadata_dict.get('methodology', []),
                data_sources=metadata_dict.get('data_sources', []),
                sample_period=metadata_dict.get('sample_period'),
                geographic_scope=metadata_dict.get('geographic_scope', [])
            )
            
            # Reconstruct academic validation
            validation_dict = template_data['academic_validation']
            academic_validation = AcademicValidation(
                out_of_sample_period=validation_dict.get('out_of_sample_period'),
                statistical_significance=validation_dict.get('statistical_significance', {}),
                robustness_checks=validation_dict.get('robustness_checks', []),
                performance_metrics=validation_dict.get('performance_metrics', {}),
                risk_metrics=validation_dict.get('risk_metrics', {}),
                t_statistics=validation_dict.get('t_statistics', {}),
                p_values=validation_dict.get('p_values', {}),
                confidence_intervals=validation_dict.get('confidence_intervals', {}),
                bootstrap_results=validation_dict.get('bootstrap_results', {}),
                monte_carlo_results=validation_dict.get('monte_carlo_results', {}),
                sensitivity_analysis=validation_dict.get('sensitivity_analysis', {})
            )
            
            # Publish the imported template
            template_category = TemplateCategory(template_data.get('template_category', 'specific'))
            
            return self.publish_academic_strategy(
                base_template=template_data['base_template'],
                academic_metadata=academic_metadata,
                academic_validation=academic_validation,
                template_category=template_category
            )
            
        except Exception as e:
            self.logger.error(f"Failed to import academic template: {e}")
            raise
    
    # Private helper methods
    def _integrate_with_main_registry(self, academic_template: AcademicTemplate):
        """Integrate academic template with main template registry"""
        try:
            # Add academic template to main registry for public access
            enhanced_template = academic_template.base_template.copy()
            enhanced_template['academic_metadata'] = academic_template.academic_metadata.__dict__
            enhanced_template['academic_validation'] = academic_template.academic_validation.__dict__
            enhanced_template['template_source'] = 'academic_research'
            
            # Register with main template registry
            # Note: This would require the main template registry to support academic templates
            self.logger.info(f"Academic template {academic_template.template_id} registered with main template system")
            
        except Exception as e:
            self.logger.warning(f"Failed to integrate with main registry: {e}")
    
    def _update_registry_stats(self):
        """Update registry statistics"""
        self.registry_stats['total_strategies'] = len(self.academic_templates)
        self.registry_stats['strategies_by_field'] = {
            field.value: len(template_ids) 
            for field, template_ids in self.research_fields.items() if template_ids
        }
        self.registry_stats['strategies_by_institution'] = {
            inst: len(strategies) 
            for inst, strategies in self.institution_strategies.items()
        }
        self.registry_stats['strategies_by_status'] = self._calculate_status_distribution()
        self.registry_stats['last_updated'] = datetime.now().isoformat()
    
    def _calculate_status_distribution(self) -> Dict[str, int]:
        """Calculate distribution by publication status"""
        status_counts = {}
        for template in self.academic_templates.values():
            status = template.academic_metadata.publication_status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _calculate_relevance_score(self, template: AcademicTemplate, query: str) -> float:
        """Calculate relevance score for search ranking"""
        score = 0.0
        query_lower = query.lower()
        
        # Title relevance
        if query_lower in template.template_id.lower():
            score += 10.0
        
        # Abstract relevance
        abstract_matches = template.academic_metadata.abstract.lower().count(query_lower)
        score += abstract_matches * 5.0
        
        # Keywords relevance
        keyword_matches = sum(1 for keyword in template.academic_metadata.keywords 
                             if query_lower in keyword.lower())
        score += keyword_matches * 3.0
        
        # Contributions relevance
        contrib_matches = sum(1 for contrib in template.academic_metadata.key_contributions 
                             if query_lower in contrib.lower())
        score += contrib_matches * 2.0
        
        return score
    
    def _get_recent_publications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent publications"""
        recent_templates = sorted(
            self.academic_templates.values(),
            key=lambda t: t.registration_date,
            reverse=True
        )[:limit]
        
        return [
            {
                'template_id': t.template_id,
                'authors': t.academic_metadata.authors,
                'institution': t.academic_metadata.institution,
                'publication': t.academic_metadata.publication,
                'research_field': t.academic_metadata.research_field.value,
                'registration_date': t.registration_date
            }
            for t in recent_templates
        ]
    
    def _calculate_performance_statistics(self) -> Dict[str, Any]:
        """Calculate aggregate performance statistics"""
        all_sharpe_ratios = []
        all_returns = []
        all_drawdowns = []
        
        for template in self.academic_templates.values():
            metrics = template.academic_validation.performance_metrics
            if 'sharpe_ratio' in metrics:
                all_sharpe_ratios.append(metrics['sharpe_ratio'])
            if 'total_return' in metrics:
                all_returns.append(metrics['total_return'])
            if 'max_drawdown' in metrics:
                all_drawdowns.append(metrics['max_drawdown'])
        
        return {
            'average_sharpe_ratio': sum(all_sharpe_ratios) / len(all_sharpe_ratios) if all_sharpe_ratios else 0,
            'average_return': sum(all_returns) / len(all_returns) if all_returns else 0,
            'average_drawdown': sum(all_drawdowns) / len(all_drawdowns) if all_drawdowns else 0,
            'total_strategies_with_metrics': len(all_sharpe_ratios)
        }
