"""
Template Registry
================

Central registry for managing strategy templates with metadata, versioning,
and inheritance tracking.

Author: Pro Quant Desk Trader
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

class TemplateCategory(Enum):
    """Template categories for organization"""
    BASE = "base"
    SPECIFIC = "specific" 
    COMPOSITE = "composite"

class TemplateType(Enum):
    """Types of strategy templates"""
    SIGNAL_GENERATION = "signal_generation"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    EXECUTION = "execution"
    COMPLETE_STRATEGY = "complete_strategy"

class TemplateStatus(Enum):
    """Template lifecycle status"""
    DRAFT = "draft"
    VALIDATED = "validated"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"

@dataclass
class TemplateMetadata:
    """Metadata for strategy templates"""
    template_id: str
    name: str
    version: str
    category: TemplateCategory
    template_type: TemplateType
    status: TemplateStatus
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    parent_templates: List[str] = field(default_factory=list)
    child_templates: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None

@dataclass 
class BaseTemplate:
    """Base class for all strategy templates"""
    metadata: TemplateMetadata
    configuration: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            'metadata': asdict(self.metadata),
            'configuration': self.configuration,
            'parameters': self.parameters,
            'components': self.components
        }
    
    def calculate_checksum(self) -> str:
        """Calculate template content checksum"""
        try:
            content = json.dumps(self.to_dict_serializable(), sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception:
            # Fallback for checksum calculation
            return hashlib.sha256(str(self.metadata.template_id).encode()).hexdigest()
    
    def update_checksum(self):
        """Update template checksum"""
        self.metadata.checksum = self.calculate_checksum()
        self.metadata.updated_at = datetime.now()
    
    def to_dict_serializable(self) -> Dict[str, Any]:
        """Convert template to serializable dictionary"""
        template_dict = self.to_dict()
        
        # Convert datetime objects to strings
        template_dict['metadata']['created_at'] = self.metadata.created_at.isoformat()
        template_dict['metadata']['updated_at'] = self.metadata.updated_at.isoformat()
        
        # Convert enums to strings
        template_dict['metadata']['category'] = self.metadata.category.value
        template_dict['metadata']['template_type'] = self.metadata.template_type.value
        template_dict['metadata']['status'] = self.metadata.status.value
        
        return template_dict

class TemplateRegistry:
    """
    Central registry for managing strategy templates with inheritance tracking,
    versioning, and performance monitoring integration.
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Registry storage
        self.registry_path = Path(registry_path) if registry_path else Path("strategy_templates/registry.json")
        self.templates: Dict[str, BaseTemplate] = {}
        self.template_index: Dict[str, List[str]] = {
            'by_category': {},
            'by_type': {},
            'by_status': {},
            'by_author': {},
            'by_tags': {}
        }
        
        # Inheritance tracking
        self.inheritance_graph: Dict[str, Dict[str, List[str]]] = {
            'parents': {},  # template_id -> [parent_ids]
            'children': {}  # template_id -> [child_ids]
        }
        
        # Performance tracking
        self.performance_cache: Dict[str, Dict[str, Any]] = {}
        
        # Load existing registry
        self._load_registry()
        
        self.logger.info(f"TemplateRegistry initialized with {len(self.templates)} templates")
    
    def register_template(self, template: BaseTemplate) -> bool:
        """Register a new template in the registry"""
        try:
            template_id = template.metadata.template_id
            
            # Validate template
            if not self._validate_template(template):
                return False
            
            # Update checksum
            template.update_checksum()
            
            # Store template
            self.templates[template_id] = template
            
            # Update indices
            self._update_indices(template)
            
            # Update inheritance graph
            self._update_inheritance_graph(template)
            
            # Save registry
            self._save_registry()
            
            self.logger.info(f"Registered template: {template_id} v{template.metadata.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register template {template.metadata.template_id}: {e}")
            return False
    
    def get_template(self, template_id: str, version: Optional[str] = None) -> Optional[BaseTemplate]:
        """Retrieve template by ID and optional version"""
        if version:
            versioned_id = f"{template_id}@{version}"
            return self.templates.get(versioned_id)
        else:
            # Try direct lookup first
            template = self.templates.get(template_id)
            if template:
                return template
            
            # Then try latest version
            latest_version = self._get_latest_version(template_id)
            if latest_version:
                return self.templates.get(f"{template_id}@{latest_version}")
            
            return None
    
    def search_templates(self, 
                        category: Optional[TemplateCategory] = None,
                        template_type: Optional[TemplateType] = None,
                        status: Optional[TemplateStatus] = None,
                        tags: Optional[List[str]] = None,
                        author: Optional[str] = None) -> List[BaseTemplate]:
        """Search templates by criteria"""
        results = []
        
        for template in self.templates.values():
            # Filter by category
            if category and template.metadata.category != category:
                continue
            
            # Filter by type
            if template_type and template.metadata.template_type != template_type:
                continue
            
            # Filter by status
            if status and template.metadata.status != status:
                continue
            
            # Filter by author
            if author and template.metadata.author != author:
                continue
            
            # Filter by tags
            if tags:
                if not all(tag in template.metadata.tags for tag in tags):
                    continue
            
            results.append(template)
        
        return results
    
    def get_template_hierarchy(self, template_id: str) -> Dict[str, Any]:
        """Get complete inheritance hierarchy for a template"""
        hierarchy = {
            'template_id': template_id,
            'parents': [],
            'children': [],
            'ancestors': [],
            'descendants': []
        }
        
        # Get direct parents and children
        hierarchy['parents'] = self.inheritance_graph['parents'].get(template_id, [])
        hierarchy['children'] = self.inheritance_graph['children'].get(template_id, [])
        
        # Get all ancestors (recursive parents)
        hierarchy['ancestors'] = self._get_ancestors(template_id)
        
        # Get all descendants (recursive children)
        hierarchy['descendants'] = self._get_descendants(template_id)
        
        return hierarchy
    
    def update_template(self, template: BaseTemplate) -> bool:
        """Update existing template"""
        try:
            template_id = template.metadata.template_id
            
            if template_id not in self.templates:
                self.logger.warning(f"Template {template_id} not found for update")
                return False
            
            # Validate template
            if not self._validate_template(template):
                return False
            
            # Update checksum and timestamp
            template.update_checksum()
            
            # Update template
            self.templates[template_id] = template
            
            # Update indices
            self._update_indices(template)
            
            # Update inheritance graph
            self._update_inheritance_graph(template)
            
            # Save registry
            self._save_registry()
            
            self.logger.info(f"Updated template: {template_id} v{template.metadata.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update template {template.metadata.template_id}: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete template from registry"""
        try:
            if template_id not in self.templates:
                self.logger.warning(f"Template {template_id} not found for deletion")
                return False
            
            # Check for dependencies
            children = self.inheritance_graph['children'].get(template_id, [])
            if children:
                self.logger.error(f"Cannot delete template {template_id}: has dependent children {children}")
                return False
            
            # Remove from templates
            del self.templates[template_id]
            
            # Clean up indices
            self._remove_from_indices(template_id)
            
            # Clean up inheritance graph
            self._remove_from_inheritance_graph(template_id)
            
            # Save registry
            self._save_registry()
            
            self.logger.info(f"Deleted template: {template_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete template {template_id}: {e}")
            return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        stats = {
            'total_templates': len(self.templates),
            'by_category': {},
            'by_type': {},
            'by_status': {},
            'by_author': {},
            'inheritance_depth': {},
            'performance_summary': {}
        }
        
        # Count by category
        for template in self.templates.values():
            category = template.metadata.category.value
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            template_type = template.metadata.template_type.value
            stats['by_type'][template_type] = stats['by_type'].get(template_type, 0) + 1
            
            status = template.metadata.status.value
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            author = template.metadata.author
            stats['by_author'][author] = stats['by_author'].get(author, 0) + 1
        
        # Calculate inheritance depth
        for template_id in self.templates:
            ancestors = self._get_ancestors(template_id)
            descendants = self._get_descendants(template_id)
            stats['inheritance_depth'][template_id] = {
                'ancestor_count': len(ancestors),
                'descendant_count': len(descendants)
            }
        
        return stats
    
    def _validate_template(self, template: BaseTemplate) -> bool:
        """Validate template structure and content"""
        try:
            # Check required fields
            if not template.metadata.template_id:
                self.logger.error("Template missing template_id")
                return False
            
            if not template.metadata.name:
                self.logger.error("Template missing name")
                return False
            
            if not template.metadata.version:
                self.logger.error("Template missing version")
                return False
            
            # Validate parent templates exist
            for parent_id in template.metadata.parent_templates:
                if parent_id not in self.templates:
                    self.logger.error(f"Parent template {parent_id} not found")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Template validation failed: {e}")
            return False
    
    def _update_indices(self, template: BaseTemplate):
        """Update search indices"""
        template_id = template.metadata.template_id
        
        # Update category index
        category = template.metadata.category.value
        if category not in self.template_index['by_category']:
            self.template_index['by_category'][category] = []
        if template_id not in self.template_index['by_category'][category]:
            self.template_index['by_category'][category].append(template_id)
        
        # Update type index
        template_type = template.metadata.template_type.value
        if template_type not in self.template_index['by_type']:
            self.template_index['by_type'][template_type] = []
        if template_id not in self.template_index['by_type'][template_type]:
            self.template_index['by_type'][template_type].append(template_id)
        
        # Update status index
        status = template.metadata.status.value
        if status not in self.template_index['by_status']:
            self.template_index['by_status'][status] = []
        if template_id not in self.template_index['by_status'][status]:
            self.template_index['by_status'][status].append(template_id)
        
        # Update author index
        author = template.metadata.author
        if author not in self.template_index['by_author']:
            self.template_index['by_author'][author] = []
        if template_id not in self.template_index['by_author'][author]:
            self.template_index['by_author'][author].append(template_id)
        
        # Update tags index
        for tag in template.metadata.tags:
            if tag not in self.template_index['by_tags']:
                self.template_index['by_tags'][tag] = []
            if template_id not in self.template_index['by_tags'][tag]:
                self.template_index['by_tags'][tag].append(template_id)
    
    def _update_inheritance_graph(self, template: BaseTemplate):
        """Update inheritance graph"""
        template_id = template.metadata.template_id
        
        # Update parents
        self.inheritance_graph['parents'][template_id] = template.metadata.parent_templates.copy()
        
        # Update children for parent templates
        for parent_id in template.metadata.parent_templates:
            if parent_id not in self.inheritance_graph['children']:
                self.inheritance_graph['children'][parent_id] = []
            if template_id not in self.inheritance_graph['children'][parent_id]:
                self.inheritance_graph['children'][parent_id].append(template_id)
    
    def _get_ancestors(self, template_id: str, visited: Optional[set] = None) -> List[str]:
        """Get all ancestor templates (recursive)"""
        if visited is None:
            visited = set()
        
        if template_id in visited:
            return []  # Prevent cycles
        
        visited.add(template_id)
        ancestors = []
        
        parents = self.inheritance_graph['parents'].get(template_id, [])
        for parent_id in parents:
            ancestors.append(parent_id)
            ancestors.extend(self._get_ancestors(parent_id, visited))
        
        return list(set(ancestors))  # Remove duplicates
    
    def _get_descendants(self, template_id: str, visited: Optional[set] = None) -> List[str]:
        """Get all descendant templates (recursive)"""
        if visited is None:
            visited = set()
        
        if template_id in visited:
            return []  # Prevent cycles
        
        visited.add(template_id)
        descendants = []
        
        children = self.inheritance_graph['children'].get(template_id, [])
        for child_id in children:
            descendants.append(child_id)
            descendants.extend(self._get_descendants(child_id, visited))
        
        return list(set(descendants))  # Remove duplicates
    
    def _get_latest_version(self, template_id: str) -> Optional[str]:
        """Get latest version of a template"""
        versions = []
        for stored_id in self.templates:
            if stored_id.startswith(f"{template_id}@"):
                version = stored_id.split("@")[1]
                versions.append(version)
            elif stored_id == template_id:
                versions.append("latest")
        
        if not versions:
            return None
        
        # Simple version sorting (could be enhanced)
        return max(versions)
    
    def _remove_from_indices(self, template_id: str):
        """Remove template from all indices"""
        for index_type in self.template_index:
            for key, template_list in self.template_index[index_type].items():
                if template_id in template_list:
                    template_list.remove(template_id)
    
    def _remove_from_inheritance_graph(self, template_id: str):
        """Remove template from inheritance graph"""
        # Remove from parents
        if template_id in self.inheritance_graph['parents']:
            del self.inheritance_graph['parents'][template_id]
        
        # Remove from children
        if template_id in self.inheritance_graph['children']:
            del self.inheritance_graph['children'][template_id]
        
        # Remove from other templates' parent/child lists
        for tid, parents in self.inheritance_graph['parents'].items():
            if template_id in parents:
                parents.remove(template_id)
        
        for tid, children in self.inheritance_graph['children'].items():
            if template_id in children:
                children.remove(template_id)
    
    def _load_registry(self):
        """Load registry from file"""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                
                # Load templates
                for template_data in data.get('templates', []):
                    metadata_dict = template_data['metadata']
                    
                    # Convert datetime strings back to datetime objects
                    metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
                    metadata_dict['updated_at'] = datetime.fromisoformat(metadata_dict['updated_at'])
                    
                    # Convert enum strings back to enums
                    metadata_dict['category'] = TemplateCategory(metadata_dict['category'])
                    metadata_dict['template_type'] = TemplateType(metadata_dict['template_type'])
                    metadata_dict['status'] = TemplateStatus(metadata_dict['status'])
                    
                    metadata = TemplateMetadata(**metadata_dict)
                    
                    template = BaseTemplate(
                        metadata=metadata,
                        configuration=template_data.get('configuration', {}),
                        parameters=template_data.get('parameters', {}),
                        components=template_data.get('components', {})
                    )
                    
                    self.templates[template.metadata.template_id] = template
                
                # Load indices
                self.template_index = data.get('template_index', self.template_index)
                
                # Load inheritance graph
                self.inheritance_graph = data.get('inheritance_graph', self.inheritance_graph)
                
                self.logger.info(f"Loaded {len(self.templates)} templates from registry")
            
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save registry to file"""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for serialization
            templates_data = []
            for template in self.templates.values():
                template_dict = template.to_dict_serializable()
                templates_data.append(template_dict)
            
            data = {
                'templates': templates_data,
                'template_index': self.template_index,
                'inheritance_graph': self.inheritance_graph,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Saved registry with {len(self.templates)} templates")
            
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
