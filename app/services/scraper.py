from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

class ContextExtractor:
    """
    Service for extracting meaningful context from HTML content.
    Uses BeautifulSoup to parse HTML and extract relevant information.
    """
    
    def extract(self, html_content, current_url):
        """
        Extract meaningful context from HTML content.
        
        Args:
            html_content (str): The HTML content of the page
            current_url (str): The current URL the user is on
            
        Returns:
            dict: Extracted context information
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract page title
            title = soup.title.string if soup.title else "Unknown Page"
            
            # Extract current form fields
            form_fields = []
            for form in soup.find_all('form'):
                for input_tag in form.find_all(['input', 'select', 'textarea']):
                    if input_tag.name == 'input' and input_tag.get('type') in ['hidden', 'submit', 'button']:
                        continue
                    
                    field = {
                        'type': input_tag.name,
                        'id': input_tag.get('id', ''),
                        'name': input_tag.get('name', ''),
                        'value': input_tag.get('value', '') if input_tag.name == 'input' else input_tag.text.strip()
                    }
                    form_fields.append(field)
            
            # Extract navigation menu items
            nav_items = []
            for nav in soup.find_all(['nav', 'ul']):
                for link in nav.find_all('a'):
                    item = {
                        'text': link.text.strip(),
                        'href': link.get('href', ''),
                        'active': 'active' in link.get('class', []) or current_url in link.get('href', '')
                    }
                    nav_items.append(item)
            
            # Extract main content headings
            headings = []
            for h in soup.find_all(['h1', 'h2', 'h3']):
                headings.append(h.text.strip())
            
            # Extract visible buttons
            buttons = []
            for button in soup.find_all(['button', 'a']):
                if button.name == 'a' and not (button.get('class') and any('btn' in c for c in button.get('class'))):
                    continue
                    
                btn = {
                    'text': button.text.strip(),
                    'id': button.get('id', ''),
                    'disabled': button.has_attr('disabled')
                }
                buttons.append(btn)
            
            # Extract potential feature names from the page
            potential_features = []
            keywords = ['feature', 'tool', 'function', 'capability']
            for p in soup.find_all(['p', 'div', 'span', 'li']):
                text = p.text.strip()
                if any(keyword in text.lower() for keyword in keywords) and len(text) < 100:
                    potential_features.append(text)
            
            # Extract error messages
            error_messages = []
            for error in soup.find_all(class_=re.compile(r'error|alert|warning')):
                error_messages.append(error.text.strip())
            
            # Determine current page section
            current_section = "Unknown"
            breadcrumbs = soup.find(class_=re.compile(r'breadcrumb'))
            if breadcrumbs:
                crumbs = [a.text.strip() for a in breadcrumbs.find_all('a')]
                if crumbs:
                    current_section = crumbs[-1]
            else:
                # Try to determine from URL
                url_parts = current_url.strip('/').split('/')
                if len(url_parts) > 0:
                    current_section = url_parts[-1].replace('-', ' ').replace('_', ' ').title()
            
            return {
                'title': title,
                'url': current_url,
                'current_section': current_section,
                'form_fields': form_fields,
                'nav_items': nav_items,
                'headings': headings,
                'buttons': buttons,
                'potential_features': potential_features,
                'error_messages': error_messages
            }
            
        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            # Return minimal context in case of failure
            return {
                'title': "Error extracting context",
                'url': current_url,
                'current_section': "Unknown",
                'form_fields': [],
                'nav_items': [],
                'headings': [],
                'buttons': [],
                'potential_features': [],
                'error_messages': [f"Context extraction failed: {str(e)}"]
            }