"""
Academic Strategy Repository - Comprehensive Strategy Management
================================================================

Repository for managing, searching, and analyzing academic strategy templates
with advanced filtering, categorization, and performance tracking capabilities.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re
import numpy as np

from .academic_strategy_registry import (
    AcademicTemplate, AcademicStrategyRegistry, ResearchField, PublicationStatus
)


class SortCriteria(Enum):
    """Sorting criteria for strategy search results"""
    PUBLICATION_DATE = "publication_date"
    PERFORMANCE = "performance"
    CITATIONS = "citations"
    DOWNLOADS = "downloads"
    RELEVANCE = "relevance"
    ALPHABETICAL = "alphabetical"


class PerformanceMetric(Enum):
    """Performance metrics for strategy evaluation"""
    SHARPE_RATIO = "sharpe_ratio"
    TOTAL_RETURN = "total_return"
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"
    WIN_RATE = "win_rate"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"


@dataclass
class SearchFilters:
    """Comprehensive search filters for academic strategies"""
    # Text search
    query: Optional[str] = None
    
    # Metadata filters
    research_fields: Optional[List[ResearchField]] = None
    institutions: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    publications: Optional[List[str]] = None
    publication_status: Optional[List[PublicationStatus]] = None
    
    # Date filters
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None
    registration_date_from: Optional[str] = None
    registration_date_to: Optional[str] = None
    
    # Performance filters
    min_performance: Optional[Dict[str, float]] = None
    max_performance: Optional[Dict[str, float]] = None
    
    # Statistical filters
    min_statistical_significance: Optional[Dict[str, float]] = None
    required_robustness_checks: Optional[List[str]] = None
    
    # Template filters
    template_categories: Optional[List[str]] = None
    access_levels: Optional[List[str]] = None
    
    # Keywords and methodology
    keywords: Optional[List[str]] = None
    methodology: Optional[List[str]] = None
    data_sources: Optional[List[str]] = None
    geographic_scope: Optional[List[str]] = None


@dataclass
class SearchResult:
    """Search result with relevance scoring and metadata"""
    template: AcademicTemplate
    relevance_score: float
    match_reasons: List[str] = field(default_factory=list)
    performance_rank: Optional[int] = None
    citation_count: int = 0
    download_count: int = 0


@dataclass
class RepositoryStatistics:
    """Comprehensive repository statistics"""
    total_strategies: int = 0
    strategies_by_field: Dict[str, int] = field(default_factory=dict)
    strategies_by_institution: Dict[str, int] = field(default_factory=dict)
    strategies_by_status: Dict[str, int] = field(default_factory=dict)
    average_performance: Dict[str, float] = field(default_factory=dict)
    recent_additions: int = 0
    top_performing_strategies: List[str] = field(default_factory=list)
    most_cited_strategies: List[str] = field(default_factory=list)
    trending_research_areas: List[str] = field(default_factory=list)


class AcademicStrategyRepository:
    """
    Comprehensive repository for academic strategy templates with advanced
    search, filtering, and analysis capabilities
    """
    
    def __init__(self, academic_registry: AcademicStrategyRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.academic_registry = academic_registry
        
        # Repository metadata
        self.strategy_metadata: Dict[str, Dict[str, Any]] = {}
        self.search_index: Dict[str, Set[str]] = {}
        self.performance_rankings: Dict[PerformanceMetric, List[str]] = {}
        
        # Usage tracking
        self.download_counts: Dict[str, int] = {}
        self.citation_counts: Dict[str, int] = {}
        self.view_counts: Dict[str, int] = {}
        
        # Categories and collections
        self.strategy_categories = {
            'momentum': 'Momentum and trend-following strategies',
            'mean_reversion': 'Mean reversion and contrarian strategies',
            'factor_models': 'Multi-factor and factor timing strategies',
            'regime_detection': 'Regime-aware and adaptive strategies',
            'risk_management': 'Risk management and portfolio optimization',
            'execution': 'Execution and market microstructure strategies',
            'portfolio_optimization': 'Portfolio construction and optimization',
            'market_microstructure': 'Market microstructure and liquidity strategies',
            'behavioral_finance': 'Behavioral finance and sentiment strategies',
            'machine_learning': 'Machine learning and AI-based strategies'
        }
        
        # Initialize search index
        self._build_search_index()
        
        self.logger.info("Academic Strategy Repository initialized")
    
    def search_strategies(self, 
                         filters: SearchFilters,
                         sort_by: SortCriteria = SortCriteria.RELEVANCE,
                         limit: Optional[int] = None) -> List[SearchResult]:
        """
        Advanced search for academic strategies with comprehensive filtering
        """
        try:
            self.logger.info(f"Searching strategies with filters: {filters.query}")
            
            # Get all strategies as starting point
            all_templates = list(self.academic_registry.academic_templates.values())
            
            # Apply filters
            filtered_templates = self._apply_filters(all_templates, filters)
            
            # Calculate relevance scores
            search_results = []
            for template in filtered_templates:
                relevance_score, match_reasons = self._calculate_relevance_score(template, filters)
                
                result = SearchResult(
                    template=template,
                    relevance_score=relevance_score,
                    match_reasons=match_reasons,
                    citation_count=self.citation_counts.get(template.template_id, 0),
                    download_count=self.download_counts.get(template.template_id, 0)
                )
                search_results.append(result)
            
            # Sort results
            search_results = self._sort_results(search_results, sort_by)
            
            # Apply limit
            if limit:
                search_results = search_results[:limit]
            
            # Update performance rankings
            self._update_performance_rankings(search_results)
            
            self.logger.info(f"Search completed: {len(search_results)} results found")
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Strategy search failed: {e}")
            return []
    
    def get_strategies_by_performance(self,
                                    metric: PerformanceMetric,
                                    min_value: Optional[float] = None,
                                    max_value: Optional[float] = None,
                                    top_n: Optional[int] = None) -> List[AcademicTemplate]:
        """Get strategies filtered and ranked by performance metrics"""
        try:
            strategies = []
            metric_name = metric.value
            
            for template in self.academic_registry.academic_templates.values():
                performance_metrics = template.academic_validation.performance_metrics
                
                if metric_name in performance_metrics:
                    value = performance_metrics[metric_name]
                    
                    # Apply value filters
                    if min_value is not None and value < min_value:
                        continue
                    if max_value is not None and value > max_value:
                        continue
                    
                    strategies.append((template, value))
            
            # Sort by performance metric (descending for most metrics, ascending for drawdown)
            reverse_sort = metric not in [PerformanceMetric.MAX_DRAWDOWN, PerformanceMetric.VOLATILITY]
            strategies.sort(key=lambda x: x[1], reverse=reverse_sort)
            
            # Apply top_n filter
            if top_n:
                strategies = strategies[:top_n]
            
            return [template for template, _ in strategies]
            
        except Exception as e:
            self.logger.error(f"Performance-based search failed: {e}")
            return []
    
    def get_strategies_by_institution(self, institution: str) -> List[AcademicTemplate]:
        """Get strategies by academic institution"""
        return self.academic_registry.get_academic_strategies_by_institution(institution)
    
    def get_strategies_by_author(self, author: str) -> List[AcademicTemplate]:
        """Get strategies by author"""
        return self.academic_registry.get_academic_strategies_by_author(author)
    
    def get_strategies_by_field(self, research_field: ResearchField) -> List[AcademicTemplate]:
        """Get strategies by research field"""
        return self.academic_registry.get_academic_strategies_by_field(research_field)
    
    def get_trending_strategies(self, days: int = 30, limit: int = 10) -> List[Tuple[AcademicTemplate, int]]:
        """Get trending strategies based on recent activity"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            trending_scores = {}
            
            for template_id, template in self.academic_registry.academic_templates.items():
                score = 0
                
                # Recent registration bonus
                reg_date = datetime.fromisoformat(template.registration_date)
                if reg_date >= cutoff_date:
                    score += 10
                
                # Download activity
                recent_downloads = self.download_counts.get(template_id, 0)
                score += recent_downloads * 2
                
                # Citation activity
                recent_citations = self.citation_counts.get(template_id, 0)
                score += recent_citations * 5
                
                # View activity
                recent_views = self.view_counts.get(template_id, 0)
                score += recent_views
                
                if score > 0:
                    trending_scores[template] = score
            
            # Sort by trending score
            trending_list = sorted(trending_scores.items(), key=lambda x: x[1], reverse=True)
            
            return trending_list[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get trending strategies: {e}")
            return []
    
    def get_similar_strategies(self, template_id: str, limit: int = 5) -> List[Tuple[AcademicTemplate, float]]:
        """Find strategies similar to the given template"""
        try:
            if template_id not in self.academic_registry.academic_templates:
                raise ValueError(f"Template {template_id} not found")
            
            base_template = self.academic_registry.academic_templates[template_id]
            similarities = []
            
            for other_id, other_template in self.academic_registry.academic_templates.items():
                if other_id == template_id:
                    continue
                
                similarity_score = self._calculate_similarity(base_template, other_template)
                if similarity_score > 0.1:  # Minimum similarity threshold
                    similarities.append((other_template, similarity_score))
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to find similar strategies: {e}")
            return []
    
    def get_repository_statistics(self) -> RepositoryStatistics:
        """Get comprehensive repository statistics"""
        try:
            stats = RepositoryStatistics()
            
            # Basic counts
            stats.total_strategies = len(self.academic_registry.academic_templates)
            
            # Field distribution
            for field in ResearchField:
                strategies = self.get_strategies_by_field(field)
                if strategies:
                    stats.strategies_by_field[field.value] = len(strategies)
            
            # Institution distribution
            for template in self.academic_registry.academic_templates.values():
                institution = template.academic_metadata.institution
                stats.strategies_by_institution[institution] = stats.strategies_by_institution.get(institution, 0) + 1
            
            # Status distribution
            for template in self.academic_registry.academic_templates.values():
                status = template.academic_metadata.publication_status.value
                stats.strategies_by_status[status] = stats.strategies_by_status.get(status, 0) + 1
            
            # Average performance
            performance_sums = {}
            performance_counts = {}
            
            for template in self.academic_registry.academic_templates.values():
                for metric, value in template.academic_validation.performance_metrics.items():
                    if isinstance(value, (int, float)):
                        performance_sums[metric] = performance_sums.get(metric, 0) + value
                        performance_counts[metric] = performance_counts.get(metric, 0) + 1
            
            for metric in performance_sums:
                if performance_counts[metric] > 0:
                    stats.average_performance[metric] = performance_sums[metric] / performance_counts[metric]
            
            # Recent additions (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            stats.recent_additions = len([
                t for t in self.academic_registry.academic_templates.values()
                if datetime.fromisoformat(t.registration_date) >= cutoff_date
            ])
            
            # Top performing strategies
            top_performers = self.get_strategies_by_performance(
                PerformanceMetric.SHARPE_RATIO, top_n=5
            )
            stats.top_performing_strategies = [t.template_id for t in top_performers]
            
            # Most cited strategies
            most_cited = sorted(
                self.citation_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            stats.most_cited_strategies = [template_id for template_id, _ in most_cited]
            
            # Trending research areas
            trending = self.get_trending_strategies(limit=3)
            research_areas = []
            for template, _ in trending:
                field = template.academic_metadata.research_field.value
                if field not in research_areas:
                    research_areas.append(field)
            stats.trending_research_areas = research_areas
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to generate repository statistics: {e}")
            return RepositoryStatistics()
    
    def record_download(self, template_id: str) -> bool:
        """Record a strategy download"""
        try:
            if template_id in self.academic_registry.academic_templates:
                self.download_counts[template_id] = self.download_counts.get(template_id, 0) + 1
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to record download: {e}")
            return False
    
    def record_citation(self, template_id: str) -> bool:
        """Record a strategy citation"""
        try:
            if template_id in self.academic_registry.academic_templates:
                self.citation_counts[template_id] = self.citation_counts.get(template_id, 0) + 1
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to record citation: {e}")
            return False
    
    def record_view(self, template_id: str) -> bool:
        """Record a strategy view"""
        try:
            if template_id in self.academic_registry.academic_templates:
                self.view_counts[template_id] = self.view_counts.get(template_id, 0) + 1
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to record view: {e}")
            return False
    
    # Private helper methods
    def _apply_filters(self, templates: List[AcademicTemplate], filters: SearchFilters) -> List[AcademicTemplate]:
        """Apply search filters to template list"""
        filtered = templates
        
        # Research field filter
        if filters.research_fields:
            filtered = [t for t in filtered if t.academic_metadata.research_field in filters.research_fields]
        
        # Institution filter
        if filters.institutions:
            filtered = [t for t in filtered if t.academic_metadata.institution in filters.institutions]
        
        # Author filter
        if filters.authors:
            filtered = [t for t in filtered if any(author in t.academic_metadata.authors for author in filters.authors)]
        
        # Publication filter
        if filters.publications:
            filtered = [t for t in filtered if t.academic_metadata.publication in filters.publications]
        
        # Publication status filter
        if filters.publication_status:
            filtered = [t for t in filtered if t.academic_metadata.publication_status in filters.publication_status]
        
        # Date filters
        if filters.publication_date_from:
            date_from = datetime.fromisoformat(filters.publication_date_from)
            filtered = [t for t in filtered if datetime.fromisoformat(t.academic_metadata.publication_date) >= date_from]
        
        if filters.publication_date_to:
            date_to = datetime.fromisoformat(filters.publication_date_to)
            filtered = [t for t in filtered if datetime.fromisoformat(t.academic_metadata.publication_date) <= date_to]
        
        # Performance filters
        if filters.min_performance:
            for metric, min_val in filters.min_performance.items():
                filtered = [t for t in filtered if t.academic_validation.performance_metrics.get(metric, 0) >= min_val]
        
        if filters.max_performance:
            for metric, max_val in filters.max_performance.items():
                filtered = [t for t in filtered if t.academic_validation.performance_metrics.get(metric, float('inf')) <= max_val]
        
        # Keywords filter
        if filters.keywords:
            filtered = [t for t in filtered if any(
                keyword.lower() in [k.lower() for k in t.academic_metadata.keywords]
                for keyword in filters.keywords
            )]
        
        return filtered
    
    def _calculate_relevance_score(self, template: AcademicTemplate, filters: SearchFilters) -> Tuple[float, List[str]]:
        """Calculate relevance score for search result"""
        score = 0.0
        match_reasons = []
        
        if filters.query:
            query_lower = filters.query.lower()
            
            # Title match
            if query_lower in template.template_id.lower():
                score += 20.0
                match_reasons.append("title_match")
            
            # Abstract match
            abstract_matches = template.academic_metadata.abstract.lower().count(query_lower)
            score += abstract_matches * 10.0
            if abstract_matches > 0:
                match_reasons.append("abstract_match")
            
            # Keywords match
            keyword_matches = sum(1 for keyword in template.academic_metadata.keywords 
                                if query_lower in keyword.lower())
            score += keyword_matches * 15.0
            if keyword_matches > 0:
                match_reasons.append("keyword_match")
            
            # Contributions match
            contrib_matches = sum(1 for contrib in template.academic_metadata.key_contributions 
                                if query_lower in contrib.lower())
            score += contrib_matches * 8.0
            if contrib_matches > 0:
                match_reasons.append("contribution_match")
        
        # Performance boost
        sharpe_ratio = template.academic_validation.performance_metrics.get('sharpe_ratio', 0)
        if sharpe_ratio > 1.0:
            score += (sharpe_ratio - 1.0) * 5.0
            match_reasons.append("high_performance")
        
        # Recent publication boost
        try:
            pub_date = datetime.fromisoformat(template.academic_metadata.publication_date)
            days_old = (datetime.now() - pub_date).days
            if days_old < 365:  # Published within last year
                score += (365 - days_old) / 365 * 10.0
                match_reasons.append("recent_publication")
        except:
            pass
        
        # Citation boost
        citation_count = self.citation_counts.get(template.template_id, 0)
        score += citation_count * 2.0
        if citation_count > 0:
            match_reasons.append("cited_work")
        
        return score, match_reasons
    
    def _sort_results(self, results: List[SearchResult], sort_by: SortCriteria) -> List[SearchResult]:
        """Sort search results by specified criteria"""
        if sort_by == SortCriteria.RELEVANCE:
            results.sort(key=lambda r: r.relevance_score, reverse=True)
        elif sort_by == SortCriteria.PUBLICATION_DATE:
            results.sort(key=lambda r: r.template.academic_metadata.publication_date, reverse=True)
        elif sort_by == SortCriteria.PERFORMANCE:
            results.sort(key=lambda r: r.template.academic_validation.performance_metrics.get('sharpe_ratio', 0), reverse=True)
        elif sort_by == SortCriteria.CITATIONS:
            results.sort(key=lambda r: r.citation_count, reverse=True)
        elif sort_by == SortCriteria.DOWNLOADS:
            results.sort(key=lambda r: r.download_count, reverse=True)
        elif sort_by == SortCriteria.ALPHABETICAL:
            results.sort(key=lambda r: r.template.template_id)
        
        return results
    
    def _calculate_similarity(self, template1: AcademicTemplate, template2: AcademicTemplate) -> float:
        """Calculate similarity score between two templates"""
        similarity = 0.0
        
        # Research field similarity
        if template1.academic_metadata.research_field == template2.academic_metadata.research_field:
            similarity += 0.3
        
        # Institution similarity
        if template1.academic_metadata.institution == template2.academic_metadata.institution:
            similarity += 0.1
        
        # Author overlap
        authors1 = set(template1.academic_metadata.authors)
        authors2 = set(template2.academic_metadata.authors)
        author_overlap = len(authors1.intersection(authors2)) / len(authors1.union(authors2))
        similarity += author_overlap * 0.2
        
        # Keyword overlap
        keywords1 = set([k.lower() for k in template1.academic_metadata.keywords])
        keywords2 = set([k.lower() for k in template2.academic_metadata.keywords])
        if keywords1 and keywords2:
            keyword_overlap = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
            similarity += keyword_overlap * 0.2
        
        # Methodology overlap
        methods1 = set([m.lower() for m in template1.academic_metadata.methodology])
        methods2 = set([m.lower() for m in template2.academic_metadata.methodology])
        if methods1 and methods2:
            method_overlap = len(methods1.intersection(methods2)) / len(methods1.union(methods2))
            similarity += method_overlap * 0.2
        
        return min(similarity, 1.0)  # Cap at 1.0
    
    def _update_performance_rankings(self, results: List[SearchResult]):
        """Update performance rankings based on search results"""
        try:
            for metric in PerformanceMetric:
                metric_name = metric.value
                templates_with_metric = []
                
                for result in results:
                    performance_metrics = result.template.academic_validation.performance_metrics
                    if metric_name in performance_metrics:
                        templates_with_metric.append((result.template.template_id, performance_metrics[metric_name]))
                
                # Sort by performance (descending for most metrics, ascending for drawdown/volatility)
                reverse_sort = metric not in [PerformanceMetric.MAX_DRAWDOWN, PerformanceMetric.VOLATILITY]
                templates_with_metric.sort(key=lambda x: x[1], reverse=reverse_sort)
                
                # Update ranking
                self.performance_rankings[metric] = [template_id for template_id, _ in templates_with_metric]
                
                # Update rank in results
                for i, result in enumerate(results):
                    if result.template.template_id in self.performance_rankings[metric]:
                        result.performance_rank = self.performance_rankings[metric].index(result.template.template_id) + 1
                        break
        
        except Exception as e:
            self.logger.error(f"Failed to update performance rankings: {e}")
    
    def _build_search_index(self):
        """Build search index for faster text searches"""
        try:
            self.search_index.clear()
            
            for template_id, template in self.academic_registry.academic_templates.items():
                # Index all searchable text
                searchable_text = []
                searchable_text.append(template.template_id.lower())
                searchable_text.append(template.academic_metadata.abstract.lower())
                searchable_text.extend([k.lower() for k in template.academic_metadata.keywords])
                searchable_text.extend([c.lower() for c in template.academic_metadata.key_contributions])
                searchable_text.extend([a.lower() for a in template.academic_metadata.authors])
                searchable_text.append(template.academic_metadata.institution.lower())
                
                # Create word index
                for text in searchable_text:
                    words = re.findall(r'\w+', text)
                    for word in words:
                        if word not in self.search_index:
                            self.search_index[word] = set()
                        self.search_index[word].add(template_id)
                        
        except Exception as e:
            self.logger.error(f"Failed to build search index: {e}")