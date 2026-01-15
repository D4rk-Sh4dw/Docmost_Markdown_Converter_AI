import os
import shutil
import zipfile
import base64
import logging
from pathlib import Path
from typing import Dict, Union

def save_images(images_data: Dict[str, Union[str, bytes]], output_dir: Path) -> Dict[str, str]:
    """
    Saves images to output_dir/images/, renames them to image_001.png etc.
    Returns a mapping of {original_name: new_relative_path}
    
    images_data: Dict where key is original filename/id, value is base64 string or bytes.
    """
    images_dir = output_dir / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)
    
    mapping = {}
    counter = 1
    
    if images_data is None:
        logging.warning("save_images received None")
        return {}
        
    logging.info(f"Saving {len(images_data)} images...")
    
    for original_name, data in images_data.items():
        logging.debug(f"Processing image: {original_name}")
        # Determine extension (default to png if unknown)
        ext = '.png'
        if original_name.lower().endswith('.jpg') or original_name.lower().endswith('.jpeg'):
            ext = '.jpg'
            
        new_filename = f"image_{counter:03d}{ext}"
        new_path = images_dir / new_filename
        
        try:
            with open(new_path, 'wb') as f:
                if isinstance(data, str):
                    f.write(base64.b64decode(data))
                else:
                    f.write(data)
            
            mapping[original_name] = f"images/{new_filename}"
            counter += 1
        except Exception as e:
            logging.error(f"Failed to save image {original_name}: {e}")
            
    return mapping

def create_zip_package(source_dir: Path, output_path: str):
    """
    Zips the contents of source_dir into output_path.
    """
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                zipf.write(abs_path, rel_path)
