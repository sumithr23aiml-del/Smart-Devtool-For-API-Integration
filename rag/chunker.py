import re
import uuid
from typing import List, Dict, Any

class MarkdownChunker:
    """
    Splits Markdown text into chunks of text, keeping track of header hierarchies (H1, H2, H3)
    to preserve context for RAG retrieval.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Regex to match markdown headings
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def split(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Splits markdown text based on header sections, then subdivides each section 
        recursively if it exceeds the chunk_size.
        """
        if markdown_text is None:
            raise ValueError("Markdown text cannot be None")
        if not isinstance(markdown_text, str):
            raise TypeError("Markdown text must be a string")
            
        if not markdown_text.strip():
            return []

        # Find all headings with their positions
        headings = []
        for match in self.heading_pattern.finditer(markdown_text):
            headings.append({
                'level': len(match.group(1)),
                'title': match.group(2).strip(),
                'start': match.start(),
                'end': match.end()
            })

        chunks = []
        
        # If no headings exist, split the entire document recursively
        if not headings:
            raw_splits = self._recursive_split(markdown_text)
            for i, text in enumerate(raw_splits):
                chunks.append({
                    "id": f"chunk_raw_{uuid.uuid4().hex}",
                    "text": text,
                    "metadata": {
                        "headers": []
                    }
                })
            return chunks

        # Divide text into sections based on headings
        sections = []
        for idx, heading in enumerate(headings):
            section_start = heading['end']
            section_end = headings[idx + 1]['start'] if idx + 1 < len(headings) else len(markdown_text)
            
            # Find the path of headers leading to this heading
            header_path = []
            for prev_h in headings[:idx + 1]:
                if prev_h['level'] < heading['level']:
                    header_path.append(prev_h['title'])
            header_path.append(heading['title'])
            
            sections.append({
                "headers": header_path,
                "text": markdown_text[section_start:section_end].strip()
            })

        # Split each section content
        chunk_counter = 0
        for section in sections:
            header_prefix = " > ".join(section['headers'])
            full_section_text = f"Context: {header_prefix}\n\n{section['text']}"
            
            if len(full_section_text) <= self.chunk_size:
                chunks.append({
                    "id": f"chunk_{uuid.uuid4().hex}",
                    "text": full_section_text,
                    "metadata": {
                        "headers": section['headers']
                    }
                })
                chunk_counter += 1
            else:
                # Recursively split large text blocks
                sub_chunks = self._recursive_split(section['text'])
                for sub_text in sub_chunks:
                    chunk_text = f"Context: {header_prefix}\n\n{sub_text}"
                    chunks.append({
                        "id": f"chunk_{uuid.uuid4().hex}",
                        "text": chunk_text,
                        "metadata": {
                            "headers": section['headers']
                        }
                    })
                    chunk_counter += 1

        return chunks

    def _recursive_split(self, text: str) -> List[str]:
        """
        Splits text recursively by paragraphs, lines, and space characters.
        """
        if len(text) <= self.chunk_size:
            return [text]

        separators = ["\n\n", "\n", " ", ""]
        final_chunks = []
        
        # Simple sliding-window recursive splitter
        def split_helper(txt: str) -> List[str]:
            if len(txt) <= self.chunk_size:
                return [txt]
                
            # Find separator to split on
            chosen_sep = ""
            for sep in separators:
                if sep in txt:
                    chosen_sep = sep
                    break
            
            if chosen_sep == "":
                # Hard cut
                return [txt[i:i+self.chunk_size] for i in range(0, len(txt), self.chunk_size)]
                
            parts = txt.split(chosen_sep)
            temp_chunks = []
            current_chunk = []
            current_len = 0
            
            for part in parts:
                part_len = len(part) + len(chosen_sep)
                if current_len + part_len > self.chunk_size:
                    if current_chunk:
                        temp_chunks.append(chosen_sep.join(current_chunk))
                    current_chunk = [part]
                    current_len = len(part)
                else:
                    current_chunk.append(part)
                    current_len += part_len
            
            if current_chunk:
                temp_chunks.append(chosen_sep.join(current_chunk))
                
            # Recursively split any sub-chunks that are still too big
            results = []
            for chunk in temp_chunks:
                if len(chunk) > self.chunk_size:
                    # Avoid infinite recursion on single huge strings
                    if len(chunk) == len(txt):
                        results.append(chunk[:self.chunk_size])
                    else:
                        results.extend(split_helper(chunk))
                else:
                    results.append(chunk)
            return results

        # Simple overlap consolidation helper
        raw_splits = split_helper(text)
        consolidated = []
        for segment in raw_splits:
            if not consolidated:
                consolidated.append(segment)
            else:
                prev = consolidated[-1]
                # If merging is within size, merge
                if len(prev) + len(segment) <= self.chunk_size:
                    consolidated[-1] = prev + "\n" + segment
                else:
                    consolidated.append(segment)
        return consolidated