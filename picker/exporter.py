"""
Artifact exporter for the symbol picker.
"""
import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("core_engine.picker.exporter")

class ArtifactExporter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = config['output']['directory']
        self.filename_format = config['output']['filename_format']
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def export(self, 
               universe: Dict[str, Dict[str, Any]], 
               regime_data: Dict[str, Any], 
               asof_date: datetime,
               trade_date: datetime = None,
               diagnostics: Dict[str, Any] = None) -> str:
        """
        Export the selected universe and regime data to a JSON artifact.
        
        Args:
            universe: Dict of selected symbols and their metrics
            regime_data: Dict of regime info
            asof_date: The reference date
            trade_date: The date this universe is intended for
            diagnostics: Selection diagnostics
            
        Returns:
            Path to the created file
        """
        # Prepare the data structure
        artifact = {
            "version": "1.2",
            "asof_date": asof_date.strftime('%Y-%m-%d'),
            "trade_date": trade_date.strftime('%Y-%m-%d') if trade_date else None,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "regime": regime_data,
            "diagnostics": diagnostics or {},
            "universe_size": len(universe),
            "symbols": universe
        }
        
        # Calculate checksum for integrity
        content_str = json.dumps(artifact, sort_keys=True)
        checksum = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        artifact['checksum'] = checksum
        
        # Determine filename
        # Format: universe_{date}_{regime}.json
        # v3 schema uses 'primary' key for canonical label
        regime_label = regime_data.get('primary', regime_data.get('label', 'UNKNOWN')).replace(" ", "_").upper()
        date_str = asof_date.strftime('%Y-%m-%d')
        
        # Use config format or default
        filename = f"universe_{date_str}_{regime_label}.json"
        
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(artifact, f, indent=2)
                
            logger.info(f"✅ Exported universe artifact to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to export artifact: {e}")
            raise

