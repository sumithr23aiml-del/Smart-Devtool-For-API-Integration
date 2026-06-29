import re
import time
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Dict, Any

class HTMLCleaner:
    """
    Cleans raw HTML documents, strips boilerplate elements (headers, footers, sidebars),
    and converts standard API documentation structures into clean, structured Markdown.
    """
    def __init__(self):
        # Tags that should be completely removed along with their content
        self.ignored_tags = [
            'script', 'style', 'noscript', 'iframe', 'svg', 'form', 
            'button', 'input', 'select', 'textarea', 'nav', 'footer', 
            'header', 'aside'
        ]
        
        # Attributes or classes commonly indicating boilerplate/layout noise
        self.ignored_patterns = re.compile(
            r'sidebar|navbar|menu|footer|header|nav|ad-wrapper|banner|cookie|promo', 
            re.IGNORECASE
        )

    def clean(self, html_content: str) -> str:
        """
        Main entry point to parse, clean, and convert HTML to Markdown.
        """
        if html_content is None:
            raise ValueError("HTML content cannot be None")
        if not isinstance(html_content, str):
            raise TypeError("HTML content must be a string")
            
        print("\n[CLEANER]\nStarting...\n")
        start_time = time.time()
        
        if not html_content.strip():
            elapsed = time.time() - start_time
            print(f"Completed\n\nTime: {elapsed:.1f}s\n")
            return ""
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. Strip ignored elements
        for tag in self.ignored_tags:
            for element in soup.find_all(tag):
                element.decompose()
                
        # 2. Decompose elements with boilerplate class/id patterns
        for element in soup.find_all(True):  # True matches all tags
            if element.attrs is None:
                continue
            attrs_to_check = []
            if element.get('class'):
                # class can be a list in bs4
                classes = element.get('class')
                if isinstance(classes, list):
                    attrs_to_check.extend(classes)
                else:
                    attrs_to_check.append(str(classes))
            if element.get('id'):
                attrs_to_check.append(str(element.get('id')))
                
            for attr in attrs_to_check:
                if self.ignored_patterns.search(attr):
                    # Be careful not to decompose high-level content elements that accidentally match
                    # (e.g., article-header is fine to keep if it contains the main text, but let's decompose global headers)
                    if element.name in ['div', 'section', 'aside', 'nav', 'footer']:
                        element.decompose()
                        break

        # 3. Convert remaining DOM structure to Markdown
        markdown_output = self._node_to_markdown(soup)
        
        # 4. Clean up consecutive blank lines
        markdown_output = re.sub(r'\n{3,}', '\n\n', markdown_output)
        
        elapsed = time.time() - start_time
        print(f"Completed\n\nTime: {elapsed:.1f}s\n")
        
        return markdown_output.strip()

    def _node_to_markdown(self, node: Any) -> str:
        """
        Recursively converts a BeautifulSoup node into Markdown syntax.
        """
        if isinstance(node, NavigableString):
            # Strip extra spaces but preserve structure
            return str(node)
            
        if not isinstance(node, Tag) or node.attrs is None:
            return ""
            
        # Recursive processing of child nodes
        result = []
        
        # Handle specific tags
        tag_name = node.name.lower()
        
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            header_text = "".join(self._node_to_markdown(child) for child in node.children).strip()
            if header_text:
                return f"\n\n{'#' * level} {header_text}\n\n"
            return ""
            
        elif tag_name == 'p':
            paragraph_text = "".join(self._node_to_markdown(child) for child in node.children).strip()
            if paragraph_text:
                return f"\n\n{paragraph_text}\n\n"
            return ""
            
        elif tag_name in ['pre', 'code']:
            # If code is nested inside pre, let pre handle it
            if tag_name == 'code' and node.parent and node.parent.name == 'pre':
                return "".join(self._node_to_markdown(child) for child in node.children)
                
            code_text = node.get_text()
            # Try to identify language from class (e.g., class="language-python")
            lang = ""
            classes = node.get('class', [])
            for c in classes:
                if c.startswith('language-'):
                    lang = c.replace('language-', '')
                    break
                    
            if tag_name == 'pre' or '\n' in code_text:
                return f"\n\n```{lang}\n{code_text.strip()}\n```\n\n"
            else:
                return f" `{code_text.strip()}` "
                
        elif tag_name == 'table':
            return self._table_to_markdown(node)
            
        elif tag_name == 'ul':
            items = []
            for child in node.children:
                item_text = self._node_to_markdown(child).strip()
                if item_text:
                    items.append(f"- {item_text}")
            if items:
                return "\n" + "\n".join(items) + "\n"
            return ""
            
        elif tag_name == 'ol':
            items = []
            index = 1
            for child in node.children:
                item_text = self._node_to_markdown(child).strip()
                if item_text:
                    items.append(f"{index}. {item_text}")
                    index += 1
            if items:
                return "\n" + "\n".join(items) + "\n"
            return ""
            
        elif tag_name == 'li':
            return "".join(self._node_to_markdown(child) for child in node.children)
            
        elif tag_name == 'a':
            link_text = "".join(self._node_to_markdown(child) for child in node.children).strip()
            href = node.get('href', '')
            if link_text and href:
                # Do not write out empty links or javascript voids
                if not href.startswith('javascript:'):
                    return f"[{link_text}]({href})"
            return link_text
            
        elif tag_name in ['strong', 'b']:
            text = "".join(self._node_to_markdown(child) for child in node.children).strip()
            return f"**{text}**" if text else ""
            
        elif tag_name in ['em', 'i']:
            text = "".join(self._node_to_markdown(child) for child in node.children).strip()
            return f"*{text}*" if text else ""
            
        elif tag_name in ['br']:
            return "\n"
            
        # Default traversal for other block or inline elements (div, section, span, etc.)
        for child in node.children:
            result.append(self._node_to_markdown(child))
            
        return "".join(result)

    def _table_to_markdown(self, table_tag: Tag) -> str:
        """
        Converts an HTML table element to Markdown table format.
        """
        rows = table_tag.find_all('tr')
        if not rows:
            return ""
            
        markdown_rows = []
        max_cols = 0
        
        # Process header (th or first tr)
        headers = []
        header_row = rows[0]
        header_cells = header_row.find_all(['th', 'td'])
        for cell in header_cells:
            headers.append(cell.get_text().strip().replace('\n', ' '))
            
        max_cols = len(headers)
        if headers:
            markdown_rows.append("| " + " | ".join(headers) + " |")
            markdown_rows.append("| " + " | ".join(['---'] * max_cols) + " |")
            
        # Process details rows
        start_idx = 1 if headers else 0
        for r in rows[start_idx:]:
            cells = r.find_all('td')
            row_vals = []
            for cell in cells:
                row_vals.append(cell.get_text().strip().replace('\n', ' '))
            # Normalize row length
            if len(row_vals) < max_cols:
                row_vals.extend([''] * (max_cols - len(row_vals)))
            elif len(row_vals) > max_cols:
                row_vals = row_vals[:max_cols]
                
            if row_vals:
                markdown_rows.append("| " + " | ".join(row_vals) + " |")
                
        if markdown_rows:
            return "\n\n" + "\n".join(markdown_rows) + "\n\n"
        return ""

def clean_html(html_content: str) -> str:
    """Helper function to clean HTML using HTMLCleaner."""
    cleaner = HTMLCleaner()
    return cleaner.clean(html_content)

def extract_api_sections(markdown_content: str) -> List[Dict[str, Any]]:
    """
    Parses structural tables or header blocks matching patterns like /endpoints, 
    Parameters, Headers, schemas, etc.
    """
    sections = []
    # Identify heading blocks and paragraphs
    pattern = re.compile(r'(^#+\s+.*$)', re.MULTILINE)
    parts = pattern.split(markdown_content)
    
    current_heading = "General"
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith('#'):
            current_heading = part.lstrip('#').strip()
        else:
            sections.append({
                "section": current_heading,
                "content": part
            })
            
    return sections