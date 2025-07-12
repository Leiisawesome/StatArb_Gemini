"""
Visualization utilities for enhanced pair trading system.

This module provides common utilities, configurations, and color schemes
for creating consistent and professional charts across the system.
"""

import matplotlib.pyplot as plt
import matplotlib.figure
import matplotlib.axes
import seaborn as sns
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

# Set default style for all charts
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

@dataclass
class ColorScheme:
    """Professional color scheme for trading charts."""
    
    # Primary colors
    primary_blue: str = '#1f77b4'
    primary_green: str = '#2ca02c'
    primary_red: str = '#d62728'
    primary_orange: str = '#ff7f0e'
    primary_purple: str = '#9467bd'
    
    # Trading specific colors
    long_color: str = '#2ca02c'    # Green for long positions
    short_color: str = '#d62728'   # Red for short positions
    hold_color: str = '#808080'    # Gray for hold/no position
    
    # Performance colors
    profit_color: str = '#2ca02c'  # Green for profits
    loss_color: str = '#d62728'    # Red for losses
    neutral_color: str = '#1f77b4' # Blue for neutral
    
    # Background colors
    background_light: str = '#f8f9fa'
    background_dark: str = '#343a40'
    grid_color: str = '#e9ecef'
    
    # Text colors
    text_primary: str = '#212529'
    text_secondary: str = '#6c757d'
    
    # Accent colors
    accent_colors: List[str] = field(default_factory=lambda: [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
        '#bcbd22', '#17becf'
    ])
    
    def get_trading_colors(self) -> Dict[str, str]:
        """Get colors for trading signals."""
        return {
            'LONG': self.long_color,
            'SHORT': self.short_color,
            'HOLD': self.hold_color
        }
    
    def get_performance_colors(self) -> Dict[str, str]:
        """Get colors for performance metrics."""
        return {
            'profit': self.profit_color,
            'loss': self.loss_color,
            'neutral': self.neutral_color
        }

@dataclass
class ChartConfig:
    """Configuration for chart appearance and behavior."""
    
    # Figure settings
    figure_size: Tuple[int, int] = (12, 8)
    dpi: int = 100
    
    # Font settings
    title_font_size: int = 16
    label_font_size: int = 12
    tick_font_size: int = 10
    legend_font_size: int = 10
    
    # Grid settings
    show_grid: bool = True
    grid_alpha: float = 0.3
    grid_style: str = '--'
    
    # Line settings
    line_width: float = 2.0
    marker_size: float = 6.0
    
    # Color scheme
    color_scheme: ColorScheme = field(default_factory=ColorScheme)
    
    # Layout settings
    tight_layout: bool = True
    subplot_adjust: Dict[str, float] = field(default_factory=lambda: {
        'left': 0.1,
        'bottom': 0.1,
        'right': 0.9,
        'top': 0.9,
        'wspace': 0.2,
        'hspace': 0.3
    })

class ChartFormatter:
    """Utility class for formatting charts consistently."""
    
    def __init__(self, config: ChartConfig = None):
        self.config = config or ChartConfig()
    
    def format_figure(self, fig: plt.Figure, title: str = None) -> plt.Figure:
        """Apply consistent formatting to a figure."""
        if title:
            fig.suptitle(title, fontsize=self.config.title_font_size, fontweight='bold')
        
        if self.config.tight_layout:
            fig.tight_layout()
        
        return fig
    
    def format_axis(self, ax: plt.Axes, title: str = None, xlabel: str = None, 
                   ylabel: str = None, show_grid: bool = None) -> plt.Axes:
        """Apply consistent formatting to an axis."""
        if title:
            ax.set_title(title, fontsize=self.config.title_font_size, fontweight='bold')
        
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self.config.label_font_size)
        
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self.config.label_font_size)
        
        # Grid settings
        if show_grid is None:
            show_grid = self.config.show_grid
        
        if show_grid:
            ax.grid(True, alpha=self.config.grid_alpha, linestyle=self.config.grid_style)
        
        # Tick settings
        ax.tick_params(axis='both', which='major', labelsize=self.config.tick_font_size)
        
        return ax
    
    def format_legend(self, ax: plt.Axes, **kwargs) -> plt.Axes:
        """Add and format legend."""
        legend_kwargs = {
            'fontsize': self.config.legend_font_size,
            'frameon': True,
            'fancybox': True,
            'shadow': True
        }
        legend_kwargs.update(kwargs)
        
        ax.legend(**legend_kwargs)
        return ax

def create_subplot_grid(nrows: int, ncols: int, config: ChartConfig = None, 
                       **kwargs) -> Tuple[plt.Figure, np.ndarray]:
    """Create a subplot grid with consistent formatting."""
    if config is None:
        config = ChartConfig()
    
    fig_kwargs = {
        'figsize': config.figure_size,
        'dpi': config.dpi
    }
    fig_kwargs.update(kwargs)
    
    fig, axes = plt.subplots(nrows, ncols, **fig_kwargs)
    
    # Ensure axes is always an array
    if nrows == 1 and ncols == 1:
        axes = np.array([axes])
    elif nrows == 1 or ncols == 1:
        axes = axes.reshape(-1)
    
    return fig, axes

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a value as percentage."""
    return f"{value * 100:.{decimals}f}%"

def format_currency(value: float, currency: str = "$", decimals: int = 2) -> str:
    """Format a value as currency."""
    return f"{currency}{value:,.{decimals}f}"

def format_number(value: float, decimals: int = 2, suffix: str = "") -> str:
    """Format a number with consistent formatting."""
    if abs(value) >= 1e9:
        return f"{value/1e9:.{decimals}f}B{suffix}"
    elif abs(value) >= 1e6:
        return f"{value/1e6:.{decimals}f}M{suffix}"
    elif abs(value) >= 1e3:
        return f"{value/1e3:.{decimals}f}K{suffix}"
    else:
        return f"{value:.{decimals}f}{suffix}"

def add_watermark(ax: plt.Axes, text: str = "Enhanced Pair Trading System", 
                 alpha: float = 0.1, fontsize: int = 20) -> plt.Axes:
    """Add a watermark to the chart."""
    ax.text(0.5, 0.5, text, transform=ax.transAxes, 
            fontsize=fontsize, alpha=alpha, ha='center', va='center',
            rotation=30, color='gray')
    return ax

def save_chart(fig: plt.Figure, filename: str, dpi: int = 300, 
               bbox_inches: str = 'tight', **kwargs) -> None:
    """Save chart with consistent settings."""
    save_kwargs = {
        'dpi': dpi,
        'bbox_inches': bbox_inches,
        'facecolor': 'white',
        'edgecolor': 'none'
    }
    save_kwargs.update(kwargs)
    
    fig.savefig(filename, **save_kwargs)

def calculate_chart_dimensions(n_charts: int, max_cols: int = 3) -> Tuple[int, int]:
    """Calculate optimal subplot dimensions."""
    if n_charts <= max_cols:
        return 1, n_charts
    else:
        nrows = (n_charts + max_cols - 1) // max_cols
        ncols = max_cols
        return nrows, ncols

def create_color_gradient(start_color: str, end_color: str, n_colors: int) -> List[str]:
    """Create a color gradient between two colors."""
    import matplotlib.colors as mcolors
    
    # Convert colors to RGB
    start_rgb = mcolors.to_rgb(start_color)
    end_rgb = mcolors.to_rgb(end_color)
    
    # Create gradient
    colors = []
    for i in range(n_colors):
        ratio = i / (n_colors - 1) if n_colors > 1 else 0
        r = start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio
        g = start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio
        b = start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio
        colors.append(mcolors.to_hex((r, g, b)))
    
    return colors

def annotate_extremes(ax: plt.Axes, x_data: np.ndarray, y_data: np.ndarray, 
                     n_points: int = 5, prefix: str = "") -> plt.Axes:
    """Annotate extreme points on a chart."""
    if len(y_data) < n_points:
        return ax
    
    # Find extreme points
    max_indices = np.argsort(y_data)[-n_points:]
    min_indices = np.argsort(y_data)[:n_points]
    
    # Annotate maximum points
    for idx in max_indices:
        ax.annotate(f'{prefix}{y_data[idx]:.2f}', 
                   xy=(x_data[idx], y_data[idx]),
                   xytext=(10, 10), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='green', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    # Annotate minimum points
    for idx in min_indices:
        ax.annotate(f'{prefix}{y_data[idx]:.2f}', 
                   xy=(x_data[idx], y_data[idx]),
                   xytext=(10, -10), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    return ax 