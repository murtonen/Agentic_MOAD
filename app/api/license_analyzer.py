import os
import re
from typing import Dict, List, Any, Optional, Tuple

class LicenseAnalyzer:
    """
    Specialized agent for analyzing license differences and feature availability
    across different ServiceNow license tiers.
    """
    
    def __init__(self):
        """Initialize the license analyzer."""
        # ServiceNow license tiers (in order)
        self.license_tiers = ['standard', 'pro', 'pro+', 'enterprise']
        
        # ServiceNow products
        self.products = ['itsm', 'csx', 'itom', 'hrsd', 'csm', 'itbm']
        
        # Common features and their license availability when not explicitly stated
        # This is domain knowledge about typical ServiceNow licensing patterns
        self.feature_defaults = {
            'virtual agent': {
                'standard': False,
                'pro': True,
                'pro+': True,
                'enterprise': True
            },
            'now assist': {
                'standard': False,
                'pro': True,
                'pro+': True,
                'enterprise': True
            },
            'predictive intelligence': {
                'standard': False,
                'pro': True,
                'pro+': True,
                'enterprise': True
            },
            'performance analytics': {
                'standard': False,
                'pro': True,
                'pro+': True,
                'enterprise': True
            }
        }
    
    def analyze_license_differences(self, content_list: List[str], query: str) -> Dict[str, Any]:
        """
        Analyze license differences based on slides content and query.
        
        Args:
            content_list: List of slide content strings
            query: The original query
            
        Returns:
            Dictionary with structured license information
        """
        # Extract the feature of interest from the query
        feature = self._extract_feature_from_query(query)
        
        # Look for tables and structured content that might contain license info
        tables = self._extract_tables(content_list)
        
        # Process the content to find license tier information
        tier_info = self._analyze_content(content_list, feature, tables)
        
        # If we couldn't find specific info but have a default for this feature,
        # use the default knowledge
        if feature in self.feature_defaults and not any(tier_info.values()):
            print(f"Using default knowledge for feature: {feature}")
            tier_info = self.feature_defaults[feature]
        
        return {
            'feature': feature,
            'tiers': tier_info,
            'has_concrete_info': any(tier_info.values()) or bool(tables),
            'tables': tables
        }
    
    def _extract_feature_from_query(self, query: str) -> str:
        """
        Extract the main feature from the query.
        
        Args:
            query: The query string
            
        Returns:
            The main feature mentioned in the query
        """
        query_lower = query.lower()
        
        # List of common ServiceNow features
        features = [
            'virtual agent', 'now assist', 'predictive intelligence', 
            'workflow', 'performance analytics', 'ai search', 'knowledge graph',
            'chatbot', 'automation', 'cmdb', 'service portal'
        ]
        
        # Find which feature is in the query
        for feature in features:
            if feature in query_lower:
                return feature
        
        # If no known feature is found, look for noun phrases
        # Default to 'virtual agent' for our specific use case
        return 'virtual agent'
    
    def _extract_tables(self, content_list: List[str]) -> List[Dict[str, Any]]:
        """
        Extract tables that might contain license information.
        
        Args:
            content_list: List of slide content strings
            
        Returns:
            List of dictionaries containing table info
        """
        tables = []
        
        for content in content_list:
            # Look for table markers in our structured content
            if "--- Tables ---" in content:
                table_sections = content.split("--- Tables ---")[1].split("---")[0]
                raw_tables = re.split(r'Table \d+:', table_sections)
                
                for raw_table in raw_tables:
                    if not raw_table.strip():
                        continue
                        
                    rows = raw_table.strip().split('\n')
                    if len(rows) < 2:  # Need at least a header and one row
                        continue
                        
                    # Process the table
                    table_data = self._process_table(rows)
                    if table_data:
                        tables.append(table_data)
            
            # Also look for capability matrices (which might not be formatted as tables)
            if "capability matrix" in content.lower() or "feature matrix" in content.lower():
                # Extract sections that might contain matrix information
                matrix_data = self._extract_capability_matrix(content)
                if matrix_data:
                    tables.append({
                        'type': 'capability_matrix',
                        'data': matrix_data
                    })
        
        return tables
    
    def _process_table(self, rows: List[str]) -> Optional[Dict[str, Any]]:
        """
        Process a table to extract license information.
        
        Args:
            rows: List of table rows
            
        Returns:
            Dictionary with processed table data or None
        """
        # Check if this table contains license information
        header = rows[0].lower()
        has_license_info = any(tier in header for tier in self.license_tiers)
        
        if not has_license_info:
            return None
            
        # Extract column headers
        headers = [cell.strip().lower() for cell in rows[0].split('|')]
        
        # Identify which columns correspond to which license tiers
        tier_columns = {}
        for i, header_cell in enumerate(headers):
            for tier in self.license_tiers:
                if tier in header_cell:
                    tier_columns[tier] = i
        
        # If we didn't find any tier columns, this table isn't relevant
        if not tier_columns:
            return None
            
        # Process rows to extract feature information
        features = {}
        for row in rows[1:]:
            cells = [cell.strip() for cell in row.split('|')]
            if len(cells) < len(headers):
                continue  # Malformed row
                
            # First cell usually contains the feature name
            feature_name = cells[0].lower()
            
            # Skip empty or header-like rows
            if not feature_name or all(not cell for cell in cells[1:]):
                continue
                
            # Extract availability for each tier
            availability = {}
            for tier, col_idx in tier_columns.items():
                if col_idx < len(cells):
                    cell_value = cells[col_idx].lower()
                    availability[tier] = self._interpret_availability(cell_value)
            
            features[feature_name] = availability
        
        return {
            'type': 'license_table',
            'tier_columns': tier_columns,
            'features': features
        }
    
    def _extract_capability_matrix(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract capability matrix information from content.
        
        Args:
            content: Slide content string
            
        Returns:
            Dictionary with matrix data or None
        """
        # For capability matrices, we'll look for patterns in the content
        # that indicate feature availability by license tier
        content_lower = content.lower()
        
        # Look for sections that might list features by tier
        features_by_tier = {}
        
        for tier in self.license_tiers:
            # Look for patterns like "Standard includes:" or "Available in Pro:"
            tier_patterns = [
                f"{tier} includes", f"{tier} license includes",
                f"available in {tier}", f"{tier} edition features",
                f"{tier} edition", f"{tier} license"
            ]
            
            for pattern in tier_patterns:
                if pattern in content_lower:
                    # Find the section that might list features for this tier
                    pattern_idx = content_lower.find(pattern)
                    section_end = content_lower.find("\n\n", pattern_idx)
                    if section_end == -1:
                        section_end = len(content_lower)
                    
                    section = content_lower[pattern_idx:section_end]
                    
                    # Extract potential features from this section
                    features = self._extract_features_from_section(section)
                    if features:
                        if tier not in features_by_tier:
                            features_by_tier[tier] = []
                        features_by_tier[tier].extend(features)
        
        if not features_by_tier:
            return None
            
        return {
            'type': 'tier_features',
            'features_by_tier': features_by_tier
        }
    
    def _extract_features_from_section(self, section: str) -> List[str]:
        """
        Extract feature names from a section of text.
        
        Args:
            section: Text section
            
        Returns:
            List of feature names
        """
        # Common ServiceNow features to look for
        common_features = [
            'virtual agent', 'now assist', 'predictive intelligence', 
            'workflow', 'performance analytics', 'ai search', 'knowledge graph',
            'chatbot', 'automation', 'cmdb', 'service portal'
        ]
        
        found_features = []
        
        # Look for common features in the section
        for feature in common_features:
            if feature in section:
                found_features.append(feature)
        
        # Also look for bullet points which might indicate features
        bullet_matches = re.findall(r'(?:^|\n)\s*[\•\-\*]\s*(.*?)(?:$|\n)', section)
        for match in bullet_matches:
            if match.strip() and len(match.strip()) > 3:  # Avoid empty or tiny matches
                found_features.append(match.strip())
        
        return found_features
    
    def _interpret_availability(self, cell_value: str) -> bool:
        """
        Interpret a cell value to determine feature availability.
        
        Args:
            cell_value: The cell value string
            
        Returns:
            True if feature is available, False otherwise
        """
        # Positive indicators
        positive = ['yes', 'y', '✓', '✔', 'included', 'available', 'x', 'true']
        
        # Negative indicators
        negative = ['no', 'n', '-', 'not included', 'not available', 'false']
        
        cell_value = cell_value.lower()
        
        if any(indicator in cell_value for indicator in positive):
            return True
        if any(indicator in cell_value for indicator in negative):
            return False
            
        # If no clear indicators, check for special cases
        if 'add-on' in cell_value or 'addon' in cell_value or 'additional' in cell_value:
            return False  # Available as an add-on means not included by default
            
        # Default - if cell has content that wasn't obviously negative, assume it's available
        return bool(cell_value.strip())
    
    def _analyze_content(self, content_list: List[str], feature: str, tables: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Analyze content to determine feature availability by license tier.
        
        Args:
            content_list: List of slide content strings
            feature: The feature to analyze
            tables: Extracted tables
            
        Returns:
            Dictionary mapping license tiers to availability
        """
        # Initialize result with unknown for all tiers
        result = {tier: None for tier in self.license_tiers}
        
        # First check tables for structured information
        for table in tables:
            if table['type'] == 'license_table' and 'features' in table:
                for feature_name, availability in table['features'].items():
                    # Check if this row corresponds to our feature of interest
                    if feature in feature_name or self._are_similar_features(feature, feature_name):
                        # Update result with table data
                        for tier, available in availability.items():
                            if tier in result:
                                result[tier] = available
            
            elif table['type'] == 'tier_features' and 'features_by_tier' in table:
                # For tier_features, a feature is available if it's in that tier's list
                for tier, features in table['features_by_tier'].items():
                    if tier in result:
                        for feature_name in features:
                            if feature in feature_name or self._are_similar_features(feature, feature_name):
                                result[tier] = True
        
        # Next, scan content for textual indications
        for content in content_list:
            content_lower = content.lower()
            
            # Look for clear statements about feature availability in specific tiers
            for tier in self.license_tiers:
                # Positive patterns
                positive_patterns = [
                    f"{feature} is included in {tier}",
                    f"{feature} is available in {tier}",
                    f"{tier} includes {feature}",
                    f"{tier} license includes {feature}"
                ]
                
                # Negative patterns
                negative_patterns = [
                    f"{feature} is not included in {tier}",
                    f"{feature} is not available in {tier}",
                    f"{tier} does not include {feature}",
                    f"{tier} license does not include {feature}"
                ]
                
                for pattern in positive_patterns:
                    if pattern in content_lower:
                        result[tier] = True
                
                for pattern in negative_patterns:
                    if pattern in content_lower:
                        result[tier] = False
        
        # For any remaining unknowns, apply knowledge inferences
        # In ServiceNow, if a feature exists in a lower tier, it exists in all higher tiers
        has_any_info = any(v is not None for v in result.values())
        if has_any_info:
            # Find the lowest tier where we have info
            known_tiers = [tier for tier in self.license_tiers if result[tier] is not None]
            if known_tiers:
                lowest_known = min(known_tiers, key=lambda t: self.license_tiers.index(t))
                lowest_idx = self.license_tiers.index(lowest_known)
                
                # If this tier has the feature, all higher tiers do too
                if result[lowest_known]:
                    for tier in self.license_tiers[lowest_idx:]:
                        if result[tier] is None:
                            result[tier] = True
                
                # Look for the lowest tier with the feature
                for tier in self.license_tiers:
                    if result[tier]:
                        # All lower tiers don't have it
                        for lower_tier in self.license_tiers[:self.license_tiers.index(tier)]:
                            if result[lower_tier] is None:
                                result[lower_tier] = False
                        break
        
        return result
    
    def _are_similar_features(self, feature1: str, feature2: str) -> bool:
        """
        Check if two feature names likely refer to the same feature.
        
        Args:
            feature1: First feature name
            feature2: Second feature name
            
        Returns:
            True if they are likely the same feature
        """
        feature1 = feature1.lower()
        feature2 = feature2.lower()
        
        # Direct substring match
        if feature1 in feature2 or feature2 in feature1:
            return True
        
        # Common abbreviations and variations
        variations = {
            'virtual agent': ['va', 'chatbot', 'chat bot', 'conversational bot'],
            'now assist': ['assist', 'gen ai', 'generative ai', 'llm'],
            'predictive intelligence': ['pi', 'prediction', 'machine learning', 'ml'],
            'performance analytics': ['pa', 'analytics', 'reporting']
        }
        
        # Check if features match through variations
        for base, variants in variations.items():
            if (feature1 == base or feature1 in variants) and (feature2 == base or feature2 in variants):
                return True
        
        return False
    
    def generate_license_summary(self, analysis_result: Dict[str, Any], query: str) -> str:
        """
        Generate a summary of license differences based on analysis.
        
        Args:
            analysis_result: The analysis result
            query: The original query
            
        Returns:
            Formatted summary of license differences
        """
        feature = analysis_result['feature']
        tiers = analysis_result['tiers']
        has_concrete_info = analysis_result['has_concrete_info']
        
        # Start building the summary
        summary = []
        
        # Feature name with capitalization
        feature_display = ' '.join(word.capitalize() for word in feature.split())
        
        summary.append(f"<h2>{feature_display} License Differences</h2>")
        
        if not has_concrete_info:
            summary.append("<p><em>Based on ServiceNow's typical licensing patterns:</em></p>")
        
        # Create sections for each tier
        for tier in self.license_tiers:
            tier_display = tier.capitalize()
            available = tiers.get(tier)
            
            section = [f"<h3>🔹 {tier_display}</h3>"]
            
            if available is True:
                section.append(f"<p>{feature_display} is <span style='color:green;font-weight:bold;'>included</span> in the {tier_display} license.</p>")
                
                # Add typical capabilities for this feature in this tier
                if tier == 'standard':
                    section.append("<p>Typically includes basic functionality:</p>")
                    section.append("<ul>")
                    section.append(f"<li>Basic {feature} capabilities</li>")
                    section.append(f"<li>Self-service portal integration</li>")
                    section.append("</ul>")
                elif tier == 'pro':
                    section.append("<p>Includes enhanced functionality:</p>")
                    section.append("<ul>")
                    section.append(f"<li>Advanced {feature} capabilities</li>")
                    section.append("<li>Integration with other ServiceNow modules</li>")
                    if 'virtual agent' in feature.lower():
                        section.append("<li>Pre-built topic templates</li>")
                        section.append("<li>NLU capabilities</li>")
                        section.append("<li>Multi-channel support</li>")
                    section.append("</ul>")
                elif tier == 'pro+' or tier == 'enterprise':
                    section.append("<p>Includes premium functionality:</p>")
                    section.append("<ul>")
                    section.append("<li>All Pro capabilities</li>")
                    if 'virtual agent' in feature.lower():
                        section.append("<li>Advanced AI capabilities</li>")
                        section.append("<li>LLM integration with Now Assist</li>")
                        section.append("<li>Knowledge Graph integration</li>")
                    section.append("<li>Enterprise-grade features</li>")
                    section.append("</ul>")
                
            elif available is False:
                section.append(f"<p>{feature_display} is <span style='color:red;font-weight:bold;'>not included</span> in the {tier_display} license.</p>")
                
                # For Standard tier, offer alternatives
                if tier == 'standard' and 'virtual agent' in feature.lower():
                    section.append("<p>Customers on Standard would typically rely on:</p>")
                    section.append("<ul>")
                    section.append("<li>Basic self-service portals</li>")
                    section.append("<li>Standard request forms</li>")
                    section.append("<li>Knowledge base articles</li>")
                    section.append("</ul>")
            else:
                section.append(f"<p>No specific information available about {feature_display} in the {tier_display} license.</p>")
            
            summary.append('\n'.join(section))
        
        # Add a conclusion
        summary.append("<h3>Summary</h3>")
        if all(v is False for v in tiers.values()):
            summary.append(f"<p>{feature_display} appears to be an add-on purchase not included in standard license tiers.</p>")
        elif tiers.get('standard') is False and any(tiers.get(t) is True for t in ['pro', 'pro+', 'enterprise']):
            min_tier = next((t for t in ['pro', 'pro+', 'enterprise'] if tiers.get(t) is True), None)
            if min_tier:
                summary.append(f"<p>{feature_display} requires at minimum a <strong>{min_tier.capitalize()}</strong> license.</p>")
        
        return '\n'.join(summary) 