from bs4 import BeautifulSoup
import re
import logging
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ContextExtractor:
    """
    Service for extracting meaningful context from HTML content.
    Uses BeautifulSoup to parse HTML and extract relevant information.
    """
    
    def __init__(self):
        """Initialize the context extractor with feature-related keywords"""
        # Keywords that might indicate features in the UI
        self.feature_keywords = [
            'feature', 'tool', 'function', 'capability', 'module', 
            'dashboard', 'report', 'analytics', 'automation', 'integration',
            'export', 'import', 'settings', 'configuration', 'customize',
            'workflow', 'template', 'notification', 'alert', 'monitor'
        ]
        
        # Common UI elements that might contain feature information
        self.ui_elements = [
            'menu', 'sidebar', 'navbar', 'toolbar', 'panel', 'card',
            'tab', 'dropdown', 'button', 'link', 'icon', 'widget'
        ]
    
    def extract(self, html_content: str, current_url: str) -> Dict[str, Any]:
        """
        Extract meaningful context from HTML content.
        
        Args:
            html_content (str): The HTML content of the page
            current_url (str): The current URL the user is on
            
        Returns:
            dict: Extracted context information
        """
        if not html_content:
            logger.warning("Empty HTML content provided")
            return self._create_minimal_context(current_url, "Empty HTML content provided")
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract page title
            title = self._extract_title(soup, current_url)
            
            # Extract current form fields
            form_fields = self._extract_form_fields(soup)
            
            # Extract navigation menu items
            nav_items = self._extract_navigation(soup, current_url)
            
            # Extract main content headings
            headings = self._extract_headings(soup)
            
            # Extract visible buttons
            buttons = self._extract_buttons(soup)
            
            # Extract potential feature names from the page
            potential_features = self._extract_potential_features(soup)
            
            # Extract error messages
            error_messages = self._extract_error_messages(soup)
            
            # Determine current page section
            current_section = self._determine_section(soup, current_url)
            
            # Extract page metadata if available
            metadata = self._extract_metadata(soup)
            
            # Extract user-specific information if available
            user_info = self._extract_user_info(soup)
            
            return {
                'title': title,
                'url': current_url,
                'current_section': current_section,
                'form_fields': form_fields,
                'nav_items': nav_items,
                'headings': headings,
                'buttons': buttons,
                'potential_features': potential_features,
                'error_messages': error_messages,
                'metadata': metadata,
                'user_info': user_info,
                'domain': self._extract_domain(current_url)
            }
            
        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return self._create_minimal_context(current_url, str(e))
    
    def _extract_title(self, soup: BeautifulSoup, current_url: str) -> str:
        """Extract the page title"""
        try:
            if soup.title and soup.title.string:
                return soup.title.string.strip()
            
            # Try to find an h1 if no title
            h1 = soup.find('h1')
            if h1 and h1.text:
                return h1.text.strip()
            
            # Fall back to URL-based title
            parsed_url = urlparse(current_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if path_parts and path_parts[-1]:
                return path_parts[-1].replace('-', ' ').replace('_', ' ').title()
            
            return "Unknown Page"
        except Exception as e:
            logger.warning(f"Error extracting title: {e}")
            return "Unknown Page"
    
    def _extract_form_fields(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract form fields from the page"""
        form_fields = []
        try:
            for form in soup.find_all('form'):
                for input_tag in form.find_all(['input', 'select', 'textarea']):
                    if input_tag.name == 'input' and input_tag.get('type') in ['hidden', 'submit', 'button']:
                        continue
                    
                    field = {
                        'type': input_tag.name,
                        'id': input_tag.get('id', ''),
                        'name': input_tag.get('name', ''),
                        'placeholder': input_tag.get('placeholder', ''),
                        'label': self._find_label_for_input(input_tag, form),
                        'value': input_tag.get('value', '') if input_tag.name == 'input' else input_tag.text.strip()
                    }
                    form_fields.append(field)
        except Exception as e:
            logger.warning(f"Error extracting form fields: {e}")
        
        return form_fields
    
    def _find_label_for_input(self, input_tag: BeautifulSoup, form: BeautifulSoup) -> str:
        """Find the label associated with an input field"""
        try:
            # Check for id-based label
            if input_tag.get('id'):
                label = form.find('label', attrs={'for': input_tag['id']})
                if label:
                    return label.text.strip()
            
            # Check for parent label
            parent = input_tag.parent
            if parent and parent.name == 'label':
                return parent.text.replace(input_tag.text, '').strip()
            
            # Check for preceding label
            prev_sibling = input_tag.find_previous_sibling('label')
            if prev_sibling:
                return prev_sibling.text.strip()
            
            return ""
        except Exception:
            return ""
    
    def _extract_navigation(self, soup: BeautifulSoup, current_url: str) -> List[Dict[str, Any]]:
        """Extract navigation items from the page"""
        nav_items = []
        try:
            # Look for navigation elements
            nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu|sidebar', re.I))
            
            for nav in nav_elements:
                for link in nav.find_all('a'):
                    if not link.text.strip():
                        continue
                    
                    item = {
                        'text': link.text.strip(),
                        'href': link.get('href', ''),
                        'active': self._is_active_link(link, current_url),
                        'has_icon': bool(link.find(['i', 'svg', 'img']))
                    }
                    nav_items.append(item)
        except Exception as e:
            logger.warning(f"Error extracting navigation: {e}")
        
        return nav_items
    
    def _is_active_link(self, link: BeautifulSoup, current_url: str) -> bool:
        """Determine if a link is active based on classes and URL"""
        try:
            # Check for active class
            if link.get('class') and any(cls in ['active', 'selected', 'current'] for cls in link.get('class')):
                return True
            
            # Check if href matches current URL
            href = link.get('href', '')
            if href and href != '#' and href in current_url:
                return True
            
            # Check for aria-current attribute
            if link.get('aria-current') in ['page', 'true']:
                return True
            
            return False
        except Exception:
            return False
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extract headings from the page"""
        headings = []
        try:
            for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                text = h.text.strip()
                if text and text not in headings:
                    headings.append(text)
        except Exception as e:
            logger.warning(f"Error extracting headings: {e}")
        
        return headings
    
    def _extract_buttons(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract buttons from the page"""
        buttons = []
        try:
            # Find all button elements and links that look like buttons
            button_elements = soup.find_all(['button', 'a', 'input'])
            
            for button in button_elements:
                # Skip if it's not a button-like element
                if button.name == 'a' and not (
                    button.get('class') and any('btn' in c.lower() for c in button.get('class', []))
                ):
                    continue
                
                if button.name == 'input' and button.get('type') not in ['button', 'submit', 'reset']:
                    continue
                
                # Extract button text
                if button.name == 'input':
                    text = button.get('value', '')
                else:
                    text = button.text.strip()
                
                if not text:
                    continue
                
                btn = {
                    'text': text,
                    'id': button.get('id', ''),
                    'class': ' '.join(button.get('class', [])),
                    'disabled': button.has_attr('disabled') or 'disabled' in button.get('class', []),
                    'type': button.get('type', '') if button.name in ['button', 'input'] else 'link'
                }
                buttons.append(btn)
        except Exception as e:
            logger.warning(f"Error extracting buttons: {e}")
        
        return buttons
    
    def _extract_potential_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract potential feature names from the page"""
        potential_features = []
        try:
            # Look for elements that might contain feature information
            for element in soup.find_all(['p', 'div', 'span', 'li', 'a', 'h3', 'h4']):
                text = element.text.strip()
                if not text or len(text) > 100:
                    continue
                
                text_lower = text.lower()
                
                # Check if text contains feature keywords
                if any(keyword in text_lower for keyword in self.feature_keywords):
                    potential_features.append(text)
                    continue
                
                # Check if element has feature-related classes
                if element.get('class') and any(
                    any(keyword in cls.lower() for keyword in self.feature_keywords) 
                    for cls in element.get('class')
                ):
                    potential_features.append(text)
                    continue
                
                # Check if element is in a feature-related container
                parent = element.parent
                if parent and parent.get('class') and any(
                    any(keyword in cls.lower() for keyword in self.feature_keywords) 
                    for cls in parent.get('class')
                ):
                    potential_features.append(text)
            
            # Remove duplicates while preserving order
            seen = set()
            potential_features = [x for x in potential_features if not (x in seen or seen.add(x))]
        except Exception as e:
            logger.warning(f"Error extracting potential features: {e}")
        
        return potential_features
    
    def _extract_error_messages(self, soup: BeautifulSoup) -> List[str]:
        """Extract error messages from the page"""
        error_messages = []
        try:
            # Look for elements with error-related classes
            error_classes = ['error', 'alert', 'warning', 'danger', 'notification']
            for error_class in error_classes:
                for error in soup.find_all(class_=re.compile(f'{error_class}', re.I)):
                    text = error.text.strip()
                    if text and text not in error_messages:
                        error_messages.append(text)
            
            # Look for elements with error-related attributes
            for element in soup.find_all(attrs={'aria-invalid': 'true'}):
                # Find associated error message
                error_id = element.get('aria-errormessage') or element.get('aria-describedby')
                if error_id:
                    error_element = soup.find(id=error_id)
                    if error_element:
                        text = error_element.text.strip()
                        if text and text not in error_messages:
                            error_messages.append(text)
        except Exception as e:
            logger.warning(f"Error extracting error messages: {e}")
        
        return error_messages
    
    def _determine_section(self, soup: BeautifulSoup, current_url: str) -> str:
        """Determine the current section of the page"""
        try:
            # Check for breadcrumbs
            breadcrumbs = soup.find(class_=re.compile(r'breadcrumb', re.I))
            if breadcrumbs:
                crumbs = [a.text.strip() for a in breadcrumbs.find_all('a')]
                if crumbs:
                    return crumbs[-1]
            
            # Check for active navigation item
            nav_items = soup.find_all(['a', 'li'], class_=re.compile(r'active|selected|current', re.I))
            if nav_items:
                return nav_items[0].text.strip()
            
            # Try to determine from URL
            parsed_url = urlparse(current_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if path_parts:
                return path_parts[-1].replace('-', ' ').replace('_', ' ').title()
            
            return "Unknown"
        except Exception as e:
            logger.warning(f"Error determining section: {e}")
            return "Unknown"
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from the page"""
        metadata = {}
        try:
            # Extract meta tags
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    metadata[name] = content
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _extract_user_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract user-specific information from the page"""
        user_info = {}
        try:
            # Look for common user info containers
            user_elements = soup.find_all(class_=re.compile(r'user|profile|account', re.I))
            for element in user_elements:
                text = element.text.strip()
                if text:
                    # Try to extract username or email
                    if '@' in text:
                        user_info['email'] = text
                    else:
                        user_info['name'] = text
        except Exception as e:
            logger.warning(f"Error extracting user info: {e}")
        
        return user_info
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc
        except Exception:
            return ""
    
    def _create_minimal_context(self, current_url: str, error_message: str) -> Dict[str, Any]:
        """Create minimal context in case of failure"""
        return {
            'title': "Error extracting context",
            'url': current_url,
            'current_section': "Unknown",
            'form_fields': [],
            'nav_items': [],
            'headings': [],
            'buttons': [],
            'potential_features': [],
            'error_messages': [f"Context extraction failed: {error_message}"],
            'metadata': {},
            'user_info': {},
            'domain': self._extract_domain(current_url)
        }