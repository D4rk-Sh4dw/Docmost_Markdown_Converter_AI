import re
import base64
import logging
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def clean_markdown(md_content: str, title: str = None) -> str:
    """
    Cleans markdown content according to Docmost compatibility rules.
    - Adds Title as H1 if provided.
    - Removes multiple blank lines.
    - Fixes broken line breaks (heuristic).
    - Removes metadata/YAML headers if any.
    - Removes Docling specific artifacts (<!-- image -->, etc.)
    """
    # Remove YAML frontmatter if present (lines between --- and --- at start)
    md_content = re.sub(r'^---\n.*?\n---\n', '', md_content, flags=re.DOTALL)
    
    # Docling often leaves <!-- image --> or <!-- table --> comments
    md_content = re.sub(r'<!--.*?-->', '', md_content, flags=re.DOTALL)

    # Remove multiple blank lines (more than 2)
    md_content = re.sub(r'\n{3,}', '\n\n', md_content)
    
    # Ensure headers have space after #
    md_content = re.sub(r'^(#+)([^ \n])', r'\1 \2', md_content, flags=re.MULTILINE)
    
    # Docmost specific: Remove known structural HTML tags that might break layout
    # but preserve generic text like <Value> by not using a blanket remove.
    # We remove common block tags that Docling might allow through.
    md_content = re.sub(r'</?(div|span|html|body|head|script|style|iframe|link|meta).*?>', '', md_content, flags=re.IGNORECASE)
    
    # Unescape HTML entities (e.g. &gt; -> >)
    import html as html_lib
    md_content = html_lib.unescape(md_content)

    # Ensure blank lines around images for better spacing/rendering in Docmost
    # Docmost/Markdown prefers blank lines before block elements.
    # Replace newline+image with newline+newline+image, but avoid triple newlines.
    md_content = re.sub(r'([^\n])\n!\[', r'\1\n\n![', md_content)


    
    # Add Title if provided
    if title:
        # Check if title already exists as first line H1
        first_line = md_content.strip().split('\n')[0]
        if not first_line.startswith(f"# {title}"):
            md_content = f"# {title}\n\n{md_content}"
    
    # Renumber ordered lists (1. ... 1. ... -> 1. ... 2. ...)
    # Logic: If we see a "1." and we recently saw a list item, increment.
    # Reset if we see a Header.
    lines = md_content.split('\n')
    new_lines = []
    counter = 0
    
    for line in lines:
        # Match lines starting with "1. " or "2. " etc
        match = re.match(r'^(\d+)\.\s(.*)', line)
        if match:
            # If it's "1." specifically, or if we are in a sequence
            # We assume it's a continuation if counter > 0
            # But if it's "1." again, it might be a restart or a broken list.
            # Given the user's case (Docling outputting 1. 1. 1.), we should increment.
            
            # If we see a "1." and counter is 0, start at 1.
            # If we see a "1." and counter is > 0, treat as next item (counter+1).
            
            original_num = int(match.group(1))
            
            if original_num == 1:
                # It could be the start of a new list OR the next item in a broken list.
                # Heuristic: If we are 'tracking' a list (counter>0), treat 1. as the next item.
                counter += 1
            else:
                # If it's "2.", "3.", trust it but sync counter
                counter = original_num
            
            new_lines.append(f"{counter}. {match.group(2)}")
        else:
            new_lines.append(line)
            # Reset counter on Headers or significant layout breaks?
            # Images should NOT reset counter.
            # Empty lines should NOT reset counter.
            # Regular text? Maybe. But let's be loose -> Only headers reset.
            if line.strip().startswith('#'):
                counter = 0

    md_content = '\n'.join(new_lines)
    
    return md_content.strip()


def create_docmost_zip(markdown_content: str, images: List[Dict[str, Any]] = None, title: str = None) -> bytes:
    """
    Creates a ZIP file compatible with Docmost import.
    Structure:
    ZIP_ROOT/
    ├── document.md
    └── images/
        ├── image_001.png
        └── ...
        
    Handles both:
    1. Images passed in 'images' list (legacy/internal server)
    2. Images embedded in Markdown as Data URIs (official docling-serve)
    """
    final_images = {}
    current_image_idx = 0

    # 1. Handle passed images (if any)
    if images:
        for img_data in images:
            current_image_idx += 1
            # ... (logic for passed images if we ever use them again)
            # keeping it simple: currently we ignore this as we switched to official serve
            pass

    # 2. Extract Data URIs from Markdown
    # Pattern: ![alt](data:image/png;base64,......)
    # We regex for this, decode, save to files, and replace link.

    def replace_data_uri(match):
        nonlocal current_image_idx
        alt_text = match.group(1)
        mime_type = match.group(2) # e.g. image/png
        b64_data = match.group(3)
        
        # Determine extension
        ext = "png"
        if "jpeg" in mime_type or "jpg" in mime_type:
            ext = "jpg"
        elif "gif" in mime_type:
            ext = "gif"
        elif "webp" in mime_type:
            ext = "webp"
            
        current_image_idx += 1
        filename = f"image_{current_image_idx:03d}.{ext}"
        
        try:
            final_images[filename] = base64.b64decode(b64_data)
            return f"![{alt_text}](images/{filename})"
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            return f"![{alt_text}](MISSING_IMAGE)"

    # Regex search for ![...](data:...)
    # We use a non-greedy match for content
    data_uri_pattern = re.compile(r'!\[(.*?)\]\(data:(image/[a-zA-Z]+);base64,(.*?)\)')
    
    new_markdown = data_uri_pattern.sub(replace_data_uri, markdown_content)
    
    # Clean up the markdown finally
    new_markdown = clean_markdown(new_markdown, title=title)
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Write Markdown
        zf.writestr('document.md', new_markdown)
        
        # Write Images
        for fname, data in final_images.items():
            zf.writestr(f'images/{fname}', data)
            
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
