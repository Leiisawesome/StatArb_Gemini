"""
Artifact exporter for the symbol picker.
"""
import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("core_engine.symbolpicker.exporter")

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
               asof_date: datetime) -> str:
        """
        Export the selected universe and regime data to a JSON artifact.
        
        Args:
            universe: Dict of selected symbols and their metrics
            regime_data: Dict of regime info
            asof_date: The reference date
            
        Returns:
            Path to the created file
        """
        # Prepare the data structure
        artifact = {
            "version": "1.0",
            "asof_date": asof_date.strftime('%Y-%m-%d'),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "regime": regime_data,
            "universe_size": len(universe),
            "symbols": universe
        }
        
        # Calculate checksum for integrity
        content_str = json.dumps(artifact, sort_keys=True)
        checksum = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        artifact['checksum'] = checksum
        
        # Determine filename
        # Format: universe_{date}_{regime}.json
        regime_label = regime_data.get('label', 'UNKNOWN').replace(" ", "_").upper()
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

