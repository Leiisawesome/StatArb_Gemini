"""
Academic Repository Mining System
Extracts trading strategies from academic papers and research repositories
"""

import requests
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

@dataclass
class AcademicPaper:
    """Represents an academic paper with strategy information"""
    title: str
    authors: List[str]
    year: int
    journal: str
    doi: Optional[str]
    abstract: str
    text: str
    url: str
    keywords: List[str]

class AcademicStrategyMiner:
    """Mines trading strategies from academic repositories"""
    
    def __init__(self):
        self.sources = {
            'ssrn': SSRNMiner(),
            'arxiv': ArXivMiner(),
            'jstor': JSTORMiner(),
            'google_scholar': GoogleScholarMiner()
        }
        self.nlp_processor = NLPProcessor()
        self.logger = logging.getLogger(__name__)
        
        # Strategy-related keywords for filtering
        self.strategy_keywords = [
            'trading strategy', 'momentum', 'mean reversion', 'arbitrage',
            'factor model', 'statistical arbitrage', 'pairs trading',
            'technical analysis', 'quantitative trading', 'algorithmic trading',
            'portfolio optimization', 'risk management', 'asset allocation'
        ]
    
    def mine_strategies(self, 
                       keywords: List[str], 
                       date_range: Tuple[str, str],
                       max_papers: int = 100) -> List[Dict]:
        """
        Extract trading strategies from academic papers
        
        Args:
            keywords: List of search keywords
            date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format
            max_papers: Maximum number of papers to process
            
        Returns:
            List of extracted strategies
        """
        strategies = []
        
        for source_name, miner in self.sources.items():
            self.logger.info(f"Mining from {source_name}...")
            
            try:
                papers = miner.search_papers(keywords, date_range, max_papers//len(self.sources))
                
                for paper in papers:
                    strategy = self.extract_strategy_from_paper(paper)
                    if strategy:
                        strategies.append(strategy)
                        self.logger.info(f"Extracted strategy from: {paper.title}")
                        
            except Exception as e:
                self.logger.error(f"Error mining from {source_name}: {str(e)}")
                continue
        
        self.logger.info(f"Total strategies extracted: {len(strategies)}")
        return strategies
    
    def extract_strategy_from_paper(self, paper: AcademicPaper) -> Optional[Dict]:
        """
        Extract strategy logic from academic paper using NLP
        
        Args:
            paper: Academic paper object
            
        Returns:
            Strategy dictionary or None if no strategy found
        """
        try:
            # Extract methodology and results sections
            methodology = self.nlp_processor.extract_section(paper.text, 'methodology')
            results = self.nlp_processor.extract_section(paper.text, 'results')
            
            if not methodology:
                return None
            
            # Parse strategy components
            signals = self.extract_signals(methodology)
            risk_management = self.extract_risk_management(methodology)
            performance_metrics = self.extract_performance_metrics(results)
            
            if not signals:  # Must have at least basic signals
                return None
                
            return {
                'strategy_id': f"academic_{paper.doi or paper.title[:20]}",
                'name': paper.title,
                'description': paper.abstract,
                'source_type': 'academic',
                'source': paper.journal,
                'authors': paper.authors,
                'year': paper.year,
                'doi': paper.doi,
                'url': paper.url,
                'strategy_type': self.classify_strategy_type(signals, methodology),
                'assets': self.extract_asset_universe(methodology),
                'signals': signals,
                'risk_management': risk_management,
                'performance_metrics': performance_metrics,
                'raw_text': methodology,  # For AI enhancement
                'extraction_date': datetime.now().isoformat(),
                'confidence_score': self.calculate_confidence_score(paper, signals)
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting strategy from {paper.title}: {str(e)}")
            return None
    
    def extract_signals(self, methodology: str) -> List[Dict]:
        """Extract trading signals from methodology text"""
        signals = []
        
        # Pattern matching for common signal types
        signal_patterns = {
            'moving_average': r'moving average|MA|SMA|EMA',
            'rsi': r'RSI|relative strength index',
            'macd': r'MACD|moving average convergence divergence',
            'bollinger_bands': r'bollinger bands|BB',
            'momentum': r'momentum|return momentum|price momentum',
            'mean_reversion': r'mean reversion|reversion to mean',
            'volatility': r'volatility|ATR|average true range',
            'volume': r'volume|trading volume|volume analysis'
        }
        
        for signal_type, pattern in signal_patterns.items():
            if re.search(pattern, methodology, re.IGNORECASE):
                signals.append({
                    'signal_id': f"{signal_type}_{len(signals)}",
                    'signal_type': signal_type,
                    'parameters': self.extract_signal_parameters(methodology, signal_type),
                    'weight': 1.0  # Default weight, will be optimized later
                })
        
        return signals
    
    def extract_signal_parameters(self, methodology: str, signal_type: str) -> Dict:
        """Extract parameters for a specific signal type"""
        parameters = {}
        
        if signal_type == 'moving_average':
            # Extract lookback periods
            periods = re.findall(r'(\d+)\s*(?:day|period|window)', methodology)
            if periods:
                parameters['lookback_period'] = int(periods[0])
        
        elif signal_type == 'rsi':
            # Extract RSI parameters
            oversold = re.search(r'oversold.*?(\d+)', methodology, re.IGNORECASE)
            overbought = re.search(r'overbought.*?(\d+)', methodology, re.IGNORECASE)
            if oversold:
                parameters['oversold_threshold'] = int(oversold.group(1))
            if overbought:
                parameters['overbought_threshold'] = int(overbought.group(1))
        
        return parameters
    
    def extract_risk_management(self, methodology: str) -> Dict:
        """Extract risk management components"""
        risk_management = {}
        
        # Position sizing
        if re.search(r'position size|position sizing', methodology, re.IGNORECASE):
            risk_management['position_sizing'] = {
                'method': 'fixed_size',  # Default, will be enhanced
                'max_position_size': 0.1
            }
        
        # Stop loss
        if re.search(r'stop loss|stop-loss', methodology, re.IGNORECASE):
            risk_management['stop_loss'] = {
                'method': 'fixed_percentage',
                'percentage': 0.02  # Default 2%
            }
        
        # Take profit
        if re.search(r'take profit|take-profit', methodology, re.IGNORECASE):
            risk_management['take_profit'] = {
                'method': 'fixed_percentage',
                'percentage': 0.04  # Default 4%
            }
        
        return risk_management
    
    def extract_performance_metrics(self, results: str) -> Dict:
        """Extract performance metrics from results section"""
        metrics = {}
        
        # Sharpe ratio
        sharpe_match = re.search(r'sharpe.*?(\d+\.?\d*)', results, re.IGNORECASE)
        if sharpe_match:
            metrics['sharpe_ratio'] = float(sharpe_match.group(1))
        
        # Annual return
        return_match = re.search(r'annual.*?return.*?(\d+\.?\d*)%', results, re.IGNORECASE)
        if return_match:
            metrics['annual_return'] = float(return_match.group(1)) / 100
        
        # Maximum drawdown
        drawdown_match = re.search(r'drawdown.*?(\d+\.?\d*)%', results, re.IGNORECASE)
        if drawdown_match:
            metrics['max_drawdown'] = float(drawdown_match.group(1)) / 100
        
        return metrics
    
    def classify_strategy_type(self, signals: List[Dict], methodology: str) -> str:
        """Classify the strategy type based on signals and methodology"""
        signal_types = [s['signal_type'] for s in signals]
        
        if 'momentum' in signal_types:
            return 'momentum'
        elif 'mean_reversion' in signal_types:
            return 'mean_reversion'
        elif 'arbitrage' in methodology.lower():
            return 'arbitrage'
        elif len(signals) > 3:
            return 'multi_factor'
        else:
            return 'technical'
    
    def extract_asset_universe(self, methodology: str) -> Dict:
        """Extract asset universe information"""
        assets = {
            'universe': [],
            'benchmark': 'SPY',  # Default
            'asset_class': 'equity'  # Default
        }
        
        # Extract specific assets mentioned
        asset_patterns = [
            r'SPY|S&P 500',
            r'QQQ|NASDAQ',
            r'IWM|Russell 2000',
            r'stocks?|equities?',
            r'bonds?|fixed income',
            r'commodities?'
        ]
        
        for pattern in asset_patterns:
            if re.search(pattern, methodology, re.IGNORECASE):
                assets['universe'].append(pattern)
        
        return assets
    
    def calculate_confidence_score(self, paper: AcademicPaper, signals: List[Dict]) -> float:
        """Calculate confidence score for extracted strategy"""
        score = 0.0
        
        # Base score for having signals
        if signals:
            score += 0.3
        
        # Bonus for peer-reviewed journal
        if paper.journal in ['Journal of Finance', 'Journal of Financial Economics', 'Review of Financial Studies']:
            score += 0.2
        
        # Bonus for recent paper
        if paper.year >= 2020:
            score += 0.1
        
        # Bonus for detailed methodology
        if len(paper.text) > 5000:
            score += 0.2
        
        # Bonus for performance metrics
        if 'performance_metrics' in paper.text.lower():
            score += 0.2
        
        return min(score, 1.0)


class SSRNMiner:
    """Mines strategies from SSRN (Social Science Research Network)"""
    
    def search_papers(self, keywords: List[str], date_range: Tuple[str, str], max_papers: int) -> List[AcademicPaper]:
        """Search for papers on SSRN"""
        # Implementation for SSRN API
        # This would use SSRN's API to search for papers
        pass


class ArXivMiner:
    """Mines strategies from ArXiv"""
    
    def search_papers(self, keywords: List[str], date_range: Tuple[str, str], max_papers: int) -> List[AcademicPaper]:
        """Search for papers on ArXiv"""
        # Implementation for ArXiv API
        # This would use ArXiv's API to search for papers
        pass


class JSTORMiner:
    """Mines strategies from JSTOR"""
    
    def search_papers(self, keywords: List[str], date_range: Tuple[str, str], max_papers: int) -> List[AcademicPaper]:
        """Search for papers on JSTOR"""
        # Implementation for JSTOR API
        # This would use JSTOR's API to search for papers
        pass


class GoogleScholarMiner:
    """Mines strategies from Google Scholar"""
    
    def search_papers(self, keywords: List[str], date_range: Tuple[str, str], max_papers: int) -> List[AcademicPaper]:
        """Search for papers on Google Scholar"""
        # Implementation for Google Scholar scraping
        # This would scrape Google Scholar for papers
        pass


class NLPProcessor:
    """NLP processor for extracting strategy components from text"""
    
    def extract_section(self, text: str, section_name: str) -> str:
        """Extract specific section from paper text"""
        # Implementation for section extraction
        # This would use NLP to identify and extract methodology/results sections
        pass 