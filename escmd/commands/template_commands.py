"""
Template command processors for ElasticsearchClient.

This module handles template-related operations including:
- Legacy index templates (_template API)
- Composable index templates (_index_template API)
- Component templates (_component_template API)
- Template listing and detailed inspection
"""

from typing import Any, Dict, List, Optional
from .base_command import BaseCommand
import copy
import logging

# Handle imports based on context
_template_backup_available = False
_template_modifier_available = False
TemplateBackup = None
TemplateModifier = None

try:
    # When run as part of escmd package
    from template_utils.template_backup import TemplateBackup
    from template_utils.field_manipulation import TemplateModifier
    _template_backup_available = True
    _template_modifier_available = True
except ImportError:
    try:
        # When run as relative import
        from ..template_utils.template_backup import TemplateBackup
        from ..template_utils.field_manipulation import TemplateModifier
        _template_backup_available = True
        _template_modifier_available = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class TemplateCommands(BaseCommand):
    """
    Command processor for template-related operations.

    Supports both legacy and composable index templates as well as component templates.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'templates'

    def list_all_templates(self, template_type: str = 'all') -> Dict[str, Any]:
        """
        Get all templates with comprehensive information.

        Args:
            template_type: Type of templates to retrieve ('all', 'legacy', 'composable', 'component')

        Returns:
            dict: Template information organized by type
        """
        result = {
            'legacy_templates': {},
            'composable_templates': {},
            'component_templates': {},
            'summary': {
                'legacy_count': 0,
                'composable_count': 0,
                'component_count': 0,
                'total_count': 0
            }
        }

        try:
            # Get legacy templates if requested
            if template_type in ['all', 'legacy']:
                try:
                    legacy_response = self.es_client.es.indices.get_template()

                    # Handle response format differences
                    if hasattr(legacy_response, 'body'):
                        result['legacy_templates'] = legacy_response.body
                    elif hasattr(legacy_response, 'get'):
                        result['legacy_templates'] = dict(legacy_response)
                    else:
                        result['legacy_templates'] = legacy_response

                    # Sort legacy templates alphabetically by name
                    if result['legacy_templates'] and not isinstance(result['legacy_templates'], str):
                        result['legacy_templates'] = dict(sorted(result['legacy_templates'].items()))

                    result['summary']['legacy_count'] = len(result['legacy_templates'])
                except Exception as e:
                    result['legacy_templates'] = {"error": f"Failed to get legacy templates: {str(e)}"}

            # Get composable index templates if requested
            if template_type in ['all', 'composable']:
                try:
                    composable_response = self.es_client.es.indices.get_index_template()

                    # Handle response format differences
                    if hasattr(composable_response, 'body'):
                        templates_data = composable_response.body
                    elif hasattr(composable_response, 'get'):
                        templates_data = dict(composable_response)
                    else:
                        templates_data = composable_response

                    # Extract templates from the response structure
                    if 'index_templates' in templates_data:
                        for template in templates_data['index_templates']:
                            name = template.get('name', 'unknown')
                            result['composable_templates'][name] = template

                    # Sort composable templates alphabetically by name
                    if result['composable_templates']:
                        result['composable_templates'] = dict(sorted(result['composable_templates'].items()))

                    result['summary']['composable_count'] = len(result['composable_templates'])
                except Exception as e:
                    result['composable_templates'] = {"error": f"Failed to get composable templates: {str(e)}"}

            # Get component templates if requested
            if template_type in ['all', 'component']:
                try:
                    component_response = self.es_client.es.cluster.get_component_template()

                    # Handle response format differences
                    if hasattr(component_response, 'body'):
                        templates_data = component_response.body
                    elif hasattr(component_response, 'get'):
                        templates_data = dict(component_response)
                    else:
                        templates_data = component_response

                    # Extract templates from the response structure
                    if 'component_templates' in templates_data:
                        for template in templates_data['component_templates']:
                            name = template.get('name', 'unknown')
                            result['component_templates'][name] = template

                    # Sort component templates alphabetically by name
                    if result['component_templates']:
                        result['component_templates'] = dict(sorted(result['component_templates'].items()))

                    result['summary']['component_count'] = len(result['component_templates'])
                except Exception as e:
                    result['component_templates'] = {"error": f"Failed to get component templates: {str(e)}"}

            # Calculate total count
            result['summary']['total_count'] = (
                result['summary']['legacy_count'] +
                result['summary']['composable_count'] +
                result['summary']['component_count']
            )

            return result

        except Exception as e:
            return {"error": f"Failed to list templates: {str(e)}"}

    def get_template_detail(self, name: str, template_type: str = 'auto') -> Dict[str, Any]:
        """
        Get detailed information about a specific template.

        Args:
            name: Template name
            template_type: Type of template ('auto', 'legacy', 'composable', 'component')

        Returns:
            dict: Detailed template information
        """
        result = {
            'name': name,
            'type': None,
            'found': False,
            'template_data': None,
            'metadata': {
                'version': None,
                'created_at': None,
                'managed': False,
                'index_patterns': [],
                'priority': None,
                'settings': {},
                'mappings': {},
                'aliases': {}
            }
        }

        try:
            # If auto-detect, try all template types
            if template_type == 'auto':
                # Try composable first (newer format)
                composable_result = self._get_composable_template(name)
                if composable_result['found']:
                    result.update(composable_result)
                    result['type'] = 'composable'
                    return result

                # Try legacy template
                legacy_result = self._get_legacy_template(name)
                if legacy_result['found']:
                    result.update(legacy_result)
                    result['type'] = 'legacy'
                    return result

                # Try component template
                component_result = self._get_component_template(name)
                if component_result['found']:
                    result.update(component_result)
                    result['type'] = 'component'
                    return result

            elif template_type == 'composable':
                composable_result = self._get_composable_template(name)
                result.update(composable_result)
                result['type'] = 'composable'

            elif template_type == 'legacy':
                legacy_result = self._get_legacy_template(name)
                result.update(legacy_result)
                result['type'] = 'legacy'

            elif template_type == 'component':
                component_result = self._get_component_template(name)
                result.update(component_result)
                result['type'] = 'component'

            return result

        except Exception as e:
            result['error'] = f"Failed to get template details: {str(e)}"
            return result

    def _get_composable_template(self, name: str) -> Dict[str, Any]:
        """Get composable index template details."""
        result = {'found': False, 'template_data': None, 'metadata': {}}

        try:
            response = self.es_client.es.indices.get_index_template(name=name)

            # Handle response format differences
            if hasattr(response, 'body'):
                data = response.body
            elif hasattr(response, 'get'):
                data = dict(response)
            else:
                data = response

            if 'index_templates' in data and data['index_templates']:
                template = data['index_templates'][0]  # Should only be one
                result['found'] = True
                result['template_data'] = template

                # Extract metadata
                index_template = template.get('index_template', {})
                result['metadata'] = {
                    'version': index_template.get('version'),
                    'priority': index_template.get('priority', 0),
                    'index_patterns': index_template.get('index_patterns', []),
                    'composed_of': index_template.get('composed_of', []),
                    'template': index_template.get('template', {}),
                    'data_stream': index_template.get('data_stream'),
                    'allow_auto_create': index_template.get('allow_auto_create'),
                    '_meta': index_template.get('_meta', {})
                }

                # Extract template details
                template_def = index_template.get('template', {})
                result['metadata'].update({
                    'settings': template_def.get('settings', {}),
                    'mappings': template_def.get('mappings', {}),
                    'aliases': template_def.get('aliases', {})
                })

        except Exception:
            # Template doesn't exist or error occurred
            pass

        return result

    def _get_legacy_template(self, name: str) -> Dict[str, Any]:
        """Get legacy index template details."""
        result = {'found': False, 'template_data': None, 'metadata': {}}

        try:
            response = self.es_client.es.indices.get_template(name=name)

            # Handle response format differences
            if hasattr(response, 'body'):
                data = response.body
            elif hasattr(response, 'get'):
                data = dict(response)
            else:
                data = response

            if name in data:
                template = data[name]
                result['found'] = True
                result['template_data'] = template

                # Extract metadata
                result['metadata'] = {
                    'version': template.get('version'),
                    'order': template.get('order', 0),
                    'index_patterns': template.get('index_patterns', []),
                    'settings': template.get('settings', {}),
                    'mappings': template.get('mappings', {}),
                    'aliases': template.get('aliases', {}),
                    '_meta': template.get('_meta', {})
                }

        except Exception:
            # Template doesn't exist or error occurred
            pass

        return result

    def _get_component_template(self, name: str) -> Dict[str, Any]:
        """Get component template details."""
        result = {'found': False, 'template_data': None, 'metadata': {}}

        try:
            response = self.es_client.es.cluster.get_component_template(name=name)

            # Handle response format differences
            if hasattr(response, 'body'):
                data = response.body
            elif hasattr(response, 'get'):
                data = dict(response)
            else:
                data = response

            if 'component_templates' in data and data['component_templates']:
                template = data['component_templates'][0]  # Should only be one
                result['found'] = True
                result['template_data'] = template

                # Extract metadata
                component_template = template.get('component_template', {})
                result['metadata'] = {
                    'version': component_template.get('version'),
                    '_meta': component_template.get('_meta', {}),
                    'template': component_template.get('template', {})
                }

                # Extract template details
                template_def = component_template.get('template', {})
                result['metadata'].update({
                    'settings': template_def.get('settings', {}),
                    'mappings': template_def.get('mappings', {}),
                    'aliases': template_def.get('aliases', {})
                })

        except Exception:
            # Template doesn't exist or error occurred
            pass

        return result

    def get_templates_usage(self) -> Dict[str, Any]:
        """
        Get information about which indices are using which templates.

        Returns:
            dict: Template usage information
        """
        try:
            # Get all templates
            all_templates = self.list_all_templates()

            # Get all indices
            indices_response = self.es_client.es.cat.indices(format='json', h='index')

            # Handle response format differences
            if hasattr(indices_response, 'body'):
                indices_data = indices_response.body
            else:
                indices_data = indices_response

            indices = [idx['index'] for idx in indices_data]

            # Analyze template usage
            usage = {
                'templates_in_use': {},
                'unused_templates': [],
                'indices_without_templates': [],
                'template_conflicts': []
            }

            # Check each template against indices
            for template_type in ['legacy_templates', 'composable_templates']:
                if template_type in all_templates and not isinstance(all_templates[template_type], dict) or 'error' not in all_templates[template_type]:
                    for template_name, template_data in all_templates[template_type].items():
                        if template_name == 'error':
                            continue

                        # Extract index patterns based on template type
                        if template_type == 'legacy_templates':
                            patterns = template_data.get('index_patterns', [])
                        else:
                            # Composable template
                            index_template = template_data.get('index_template', {}) if 'index_template' in template_data else template_data
                            patterns = index_template.get('index_patterns', [])

                        matching_indices = []
                        for pattern in patterns:
                            # Simple pattern matching (could be enhanced with proper regex)
                            pattern_regex = pattern.replace('*', '.*')
                            matching = [idx for idx in indices if self._matches_pattern(idx, pattern_regex)]
                            matching_indices.extend(matching)

                        if matching_indices:
                            usage['templates_in_use'][template_name] = {
                                'type': template_type.replace('_templates', ''),
                                'patterns': patterns,
                                'matching_indices': list(set(matching_indices)),
                                'match_count': len(set(matching_indices))
                            }
                        else:
                            usage['unused_templates'].append({
                                'name': template_name,
                                'type': template_type.replace('_templates', ''),
                                'patterns': patterns
                            })

            # Sort templates_in_use alphabetically by template name
            if usage['templates_in_use']:
                usage['templates_in_use'] = dict(sorted(usage['templates_in_use'].items()))

            # Sort unused_templates alphabetically by name
            if usage['unused_templates']:
                usage['unused_templates'] = sorted(usage['unused_templates'], key=lambda x: x['name'])

            return usage

        except Exception as e:
            return {"error": f"Failed to get template usage: {str(e)}"}

    def _matches_pattern(self, index_name: str, pattern: str) -> bool:
        """
        Check if an index name matches a template pattern.

        Args:
            index_name: Name of the index
            pattern: Pattern to match (regex format)

        Returns:
            bool: True if matches
        """
        import re
        try:
            return bool(re.match(f"^{pattern}$", index_name))
        except re.error:
            # If regex is invalid, fall back to simple string comparison
            return pattern.replace('.*', '*') == index_name

    def modify_template(self, template_name: str, template_type: str, field_path: str,
                       operation: str, value: str, backup: bool = True,
                       backup_dir: Optional[str] = None, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Modify a template field using the specified operation.

        Args:
            template_name: Name of the template to modify
            template_type: Type of template ('legacy', 'composable', 'component', 'auto')
            field_path: Dot-notation path to the field (e.g., "template.settings.index.routing.allocation.exclude._name")
            operation: Operation to perform ('set', 'append', 'remove', 'delete')
            value: Value for the operation
            backup: Whether to create a backup before modification
            backup_dir: Custom backup directory (optional)
            cluster_name: Cluster name for backup metadata (optional)

        Returns:
            Dict containing operation result and metadata
        """
        result = {
            'success': False,
            'template_name': template_name,
            'template_type': template_type,
            'operation': operation,
            'field_path': field_path,
            'value': value,
            'backup_created': False,
            'backup_file': None,
            'original_value': None,
            'new_value': None,
            'error': None
        }

        try:
            # Check if template modification utilities are available
            if not _template_backup_available or not _template_modifier_available:
                result['error'] = "Template modification utilities not available"
                return result

            # First, get the current template
            template_data = self.get_template_detail(template_name, template_type)

            if not template_data.get('found', False):
                result['error'] = f"Template '{template_name}' not found"
                return result

            # Determine actual template type if auto-detection was used
            actual_template_type = template_data.get('type', template_type)
            result['template_type'] = actual_template_type

            # Extract the template definition based on type
            if actual_template_type == 'component':
                template_def = template_data['template_data']['component_template']
            elif actual_template_type == 'composable':
                template_def = template_data['template_data']['index_template']
            elif actual_template_type == 'legacy':
                template_def = template_data['template_data']
            else:
                result['error'] = f"Unknown template type: {actual_template_type}"
                return result

            # Create backup if requested
            if backup:
                try:
                    if not TemplateBackup:
                        raise ImportError("TemplateBackup not available")
                    backup_manager = TemplateBackup(backup_dir)
                    backup_file = backup_manager.create_backup(
                        template_name, actual_template_type, template_data['template_data'], cluster_name
                    )
                    result['backup_created'] = True
                    result['backup_file'] = backup_file
                except Exception as e:
                    logger.warning(f"Backup creation failed: {str(e)}")
                    result['error'] = f"Backup creation failed: {str(e)}"
                    return result

            # Get original value for comparison
            if not TemplateModifier:
                result['error'] = "TemplateModifier not available"
                return result
            modifier = TemplateModifier()
            original_value, field_exists = modifier.get_field_value(template_def, field_path)
            result['original_value'] = original_value

            # Validate field path
            validation_issues = modifier.validate_field_path(template_def, field_path)
            if validation_issues and operation not in ['set']:
                # For 'set' operation, we allow creating new paths
                result['error'] = f"Field path validation failed: {'; '.join(validation_issues)}"
                return result

            # Apply the modification
            modified_template = copy.deepcopy(template_def)
            modifier.modify_field(modified_template, field_path, operation, value)

            # Get new value for comparison
            new_value, _ = modifier.get_field_value(modified_template, field_path)
            result['new_value'] = new_value

            # Update the template in Elasticsearch
            update_result = self._update_template(template_name, actual_template_type, modified_template)

            if update_result['success']:
                result['success'] = True
            else:
                result['error'] = update_result['error']

        except Exception as e:
            logger.error(f"Template modification failed: {str(e)}")
            result['error'] = f"Template modification failed: {str(e)}"

        return result

    def _update_template(self, template_name: str, template_type: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a template in Elasticsearch.

        Args:
            template_name: Name of the template
            template_type: Type of template ('legacy', 'composable', 'component')
            template_data: Template data to update

        Returns:
            Dict with success status and error information
        """
        result = {'success': False, 'error': None}

        try:
            if template_type == 'component':
                response = self.es_client.es.cluster.put_component_template(
                    name=template_name,
                    body=template_data
                )
            elif template_type == 'composable':
                response = self.es_client.es.indices.put_index_template(
                    name=template_name,
                    body=template_data
                )
            elif template_type == 'legacy':
                response = self.es_client.es.indices.put_template(
                    name=template_name,
                    body=template_data
                )
            else:
                result['error'] = f"Unsupported template type: {template_type}"
                return result

            # Check response
            if hasattr(response, 'body'):
                response_data = response.body
            else:
                response_data = response

            if response_data.get('acknowledged', False):
                result['success'] = True
            else:
                result['error'] = "Template update was not acknowledged by Elasticsearch"

        except Exception as e:
            logger.error(f"Failed to update template '{template_name}': {str(e)}")
            result['error'] = str(e)

        return result

    def backup_template(self, template_name: str, template_type: str = 'auto',
                       backup_dir: Optional[str] = None, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a backup of a template.

        Args:
            template_name: Name of the template to backup
            template_type: Type of template ('legacy', 'composable', 'component', 'auto')
            backup_dir: Custom backup directory (optional)
            cluster_name: Cluster name for backup metadata (optional)

        Returns:
            Dict containing backup result information
        """
        result = {
            'success': False,
            'template_name': template_name,
            'template_type': template_type,
            'backup_file': None,
            'error': None
        }

        try:
            # Check if backup utilities are available
            if not _template_backup_available:
                result['error'] = "Template backup utilities not available"
                return result

            # Get the template data
            template_data = self.get_template_detail(template_name, template_type)

            if not template_data.get('found', False):
                result['error'] = f"Template '{template_name}' not found"
                return result

            # Determine actual template type
            actual_template_type = template_data.get('type', template_type)
            result['template_type'] = actual_template_type

            # Create backup
            if not TemplateBackup:
                result['error'] = "TemplateBackup not available"
                return result
            backup_manager = TemplateBackup(backup_dir)
            backup_file = backup_manager.create_backup(
                template_name, actual_template_type, template_data['template_data'], cluster_name
            )

            result['success'] = True
            result['backup_file'] = backup_file

        except Exception as e:
            logger.error(f"Template backup failed: {str(e)}")
            result['error'] = str(e)

        return result

    def restore_template(self, backup_file: str) -> Dict[str, Any]:
        """
        Restore a template from a backup file.

        Args:
            backup_file: Path to the backup file

        Returns:
            Dict containing restore result information
        """
        result = {
            'success': False,
            'template_name': None,
            'template_type': None,
            'backup_file': backup_file,
            'error': None
        }

        try:
            # Check if backup utilities are available
            if not _template_backup_available:
                result['error'] = "Template backup utilities not available"
                return result

            # Load backup data
            if not TemplateBackup:
                result['error'] = "TemplateBackup not available"
                return result
            backup_manager = TemplateBackup()
            backup_data = backup_manager.restore_template(backup_file)

            metadata = backup_data['metadata']
            template_data = backup_data['template_data']

            template_name = metadata['template_name']
            template_type = metadata['template_type']

            result['template_name'] = template_name
            result['template_type'] = template_type

            # Restore the template
            update_result = self._update_template(template_name, template_type, template_data)

            if update_result['success']:
                result['success'] = True
            else:
                result['error'] = f"Failed to restore template: {update_result['error']}"

        except Exception as e:
            logger.error(f"Template restore failed: {str(e)}")
            result['error'] = str(e)

        return result

    def list_backups(self, template_name: Optional[str] = None, template_type: Optional[str] = None,
                    backup_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        List available template backups.

        Args:
            template_name: Filter by template name (optional)
            template_type: Filter by template type (optional)
            backup_dir: Custom backup directory (optional)

        Returns:
            Dict containing backup listing information
        """
        result = {
            'success': False,
            'backups': [],
            'error': None
        }

        try:
            # Check if backup utilities are available
            if not _template_backup_available:
                result['error'] = "Template backup utilities not available"
                return result

            if not TemplateBackup:
                result['error'] = "TemplateBackup not available"
                return result
            backup_manager = TemplateBackup(backup_dir)
            backups = backup_manager.list_backups(template_name, template_type)

            result['success'] = True
            result['backups'] = backups

        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
            result['error'] = str(e)

        return result

    def validate_template(self, template_data: Dict[str, Any], template_type: str) -> List[str]:
        """
        Validate template data structure.

        Args:
            template_data: Template data to validate
            template_type: Type of template

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        try:
            # Basic structure validation based on template type
            if template_type == 'component':
                if 'template' not in template_data:
                    issues.append("Component template missing 'template' section")
            elif template_type == 'composable':
                if 'index_patterns' not in template_data:
                    issues.append("Composable template missing 'index_patterns'")
                if 'template' not in template_data:
                    issues.append("Composable template missing 'template' section")
            elif template_type == 'legacy':
                if 'index_patterns' not in template_data and 'template' not in template_data:
                    issues.append("Legacy template missing 'index_patterns' or 'template'")

            # Additional validation can be added here

        except Exception as e:
            issues.append(f"Validation error: {str(e)}")

        return issues

    def create_templates_from_file(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Create templates from a JSON file.

        Args:
            file_path: Path to JSON file containing template definitions
            dry_run: If True, validate but don't create templates

        Returns:
            dict: Creation result with success status and details
        """
        import json
        import os

        result = {
            'success': False,
            'created_count': 0,
            'failed_count': 0,
            'created_templates': [],
            'failed_templates': [],
            'error': None
        }

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                result['error'] = f"File not found: {file_path}"
                return result

            # Read and parse JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different JSON structures
            templates_to_create = []

            if 'component_templates' in data:
                # Bulk component templates format
                for template_def in data['component_templates']:
                    templates_to_create.append({
                        'name': template_def['name'],
                        'type': 'component',
                        'definition': template_def['component_template']
                    })
            elif 'index_templates' in data:
                # Bulk composable templates format
                for template_def in data['index_templates']:
                    templates_to_create.append({
                        'name': template_def['name'],
                        'type': 'composable',
                        'definition': template_def['index_template']
                    })
            elif 'templates' in data:
                # Bulk legacy templates format
                for template_name, template_def in data['templates'].items():
                    templates_to_create.append({
                        'name': template_name,
                        'type': 'legacy',
                        'definition': template_def
                    })
            else:
                # Single template format - try to auto-detect type
                if 'component_template' in data:
                    templates_to_create.append({
                        'name': data.get('name', 'unnamed_template'),
                        'type': 'component',
                        'definition': data['component_template']
                    })
                elif 'index_template' in data:
                    templates_to_create.append({
                        'name': data.get('name', 'unnamed_template'),
                        'type': 'composable',
                        'definition': data['index_template']
                    })
                else:
                    # Assume legacy template
                    templates_to_create.append({
                        'name': data.get('name', 'unnamed_template'),
                        'type': 'legacy',
                        'definition': data
                    })

            if not templates_to_create:
                result['error'] = "No valid template definitions found in JSON file"
                return result

            # Process each template
            for template_info in templates_to_create:
                try:
                    template_result = self._create_single_template(
                        template_info['name'],
                        template_info['type'],
                        template_info['definition'],
                        dry_run
                    )

                    if template_result['success']:
                        result['created_count'] += 1
                        result['created_templates'].append({
                            'name': template_info['name'],
                            'type': template_info['type']
                        })
                    else:
                        result['failed_count'] += 1
                        result['failed_templates'].append({
                            'name': template_info['name'],
                            'error': template_result['error']
                        })

                except Exception as e:
                    result['failed_count'] += 1
                    result['failed_templates'].append({
                        'name': template_info['name'],
                        'error': str(e)
                    })

            result['success'] = result['created_count'] > 0 or dry_run

        except json.JSONDecodeError as e:
            result['error'] = f"Invalid JSON format: {str(e)}"
        except Exception as e:
            result['error'] = f"Failed to process file: {str(e)}"

        return result

    def create_template_inline(self, template_name: str, template_type: str,
                              definition: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Create a single template from inline JSON definition.

        Args:
            template_name: Name for the template
            template_type: Type of template (component, composable, legacy)
            definition: JSON string containing template definition
            dry_run: If True, validate but don't create template

        Returns:
            dict: Creation result with success status and details
        """
        import json

        result = {
            'success': False,
            'created_count': 0,
            'failed_count': 0,
            'created_templates': [],
            'failed_templates': [],
            'error': None
        }

        try:
            # Parse JSON definition
            template_def = json.loads(definition)

            # Create the template
            template_result = self._create_single_template(
                template_name, template_type, template_def, dry_run
            )

            if template_result['success']:
                result['success'] = True
                result['created_count'] = 1
                result['created_templates'].append({
                    'name': template_name,
                    'type': template_type
                })
            else:
                result['failed_count'] = 1
                result['failed_templates'].append({
                    'name': template_name,
                    'error': template_result['error']
                })
                result['error'] = template_result['error']

        except json.JSONDecodeError as e:
            result['error'] = f"Invalid JSON definition: {str(e)}"
            result['failed_count'] = 1
            result['failed_templates'].append({
                'name': template_name,
                'error': result['error']
            })
        except Exception as e:
            result['error'] = f"Failed to create template: {str(e)}"
            result['failed_count'] = 1
            result['failed_templates'].append({
                'name': template_name,
                'error': result['error']
            })

        return result

    def _create_single_template(self, template_name: str, template_type: str,
                               template_definition: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Create a single template using the appropriate Elasticsearch API.

        Args:
            template_name: Name for the template
            template_type: Type of template (component, composable, legacy)
            template_definition: Template definition dictionary
            dry_run: If True, validate but don't create template

        Returns:
            dict: Creation result with success status and details
        """
        result = {
            'success': False,
            'error': None,
            'template_name': template_name,
            'template_type': template_type
        }

        try:
            if dry_run:
                # In dry run mode, just validate the structure
                result['success'] = True
                result['dry_run'] = True
                return result

            # Create template based on type
            if template_type == 'component':
                response = self.es_client.es.cluster.put_component_template(
                    name=template_name,
                    body=template_definition
                )
            elif template_type == 'composable':
                response = self.es_client.es.indices.put_index_template(
                    name=template_name,
                    body=template_definition
                )
            elif template_type == 'legacy':
                response = self.es_client.es.indices.put_template(
                    name=template_name,
                    body=template_definition
                )
            else:
                result['error'] = f"Unsupported template type: {template_type}"
                return result

            # Check response
            if hasattr(response, 'body'):
                response_body = response.body
            else:
                response_body = response

            if response_body.get('acknowledged', False):
                result['success'] = True
            else:
                result['error'] = "Template creation not acknowledged by Elasticsearch"

        except Exception as e:
            result['error'] = f"Elasticsearch API error: {str(e)}"

        return result


# Backward compatibility functions
def list_all_templates(es_client, template_type: str = 'all') -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    template_cmd = TemplateCommands(es_client)
    return template_cmd.list_all_templates(template_type)


def get_template_detail(es_client, name: str, template_type: str = 'auto') -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    template_cmd = TemplateCommands(es_client)
    return template_cmd.get_template_detail(name, template_type)


def get_templates_usage(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    template_cmd = TemplateCommands(es_client)
    return template_cmd.get_templates_usage()
