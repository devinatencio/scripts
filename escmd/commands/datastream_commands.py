"""
Datastream command processors extracted from ElasticsearchClient.

This module handles datastream-related operations including:
- Datastream rollover operations
- Datastream lifecycle management
"""

import requests
from requests.auth import HTTPBasicAuth
import json
from typing import Dict, Any, Optional
from .base_command import BaseCommand


class DatastreamCommands(BaseCommand):
    """
    Command processor for datastream-related operations.
    """
    
    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'datastream'
    
    def rollover_datastream(self, datastream_name: str) -> Dict[str, Any]:
        """
        Rollover a datastream to create a new index.
        
        Args:
            datastream_name: Name of the datastream to rollover
            
        Returns:
            dict: Rollover response data
            
        Raises:
            requests.RequestException: If the rollover operation fails
        """
        if not datastream_name:
            raise ValueError("Datastream name cannot be empty")
            
        # Get ES URL
        ES_URL = self.es_client.build_es_url()

        # Perform rollover operation
        url = f'{ES_URL}/{datastream_name}/_rollover'
        
        try:
            if self.es_client.elastic_authentication:
                datastream_response = requests.post(
                    url,
                    auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                    verify=False,
                    timeout=30
                )
            else:
                datastream_response = requests.post(
                    url,
                    verify=False,
                    timeout=30
                )

            # Raise an exception if the response wasn't successful
            datastream_response.raise_for_status()
            datastream_data = datastream_response.json()
            return datastream_data
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to rollover datastream {datastream_name}: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from rollover operation: {str(e)}")
