"""
PDF to Image Converter Module
Converts PDF files to page images for multimodal processing
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from tqdm import tqdm

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError(
        "PyMuPDF is required for PDF to image conversion. "
        "Install it with: uv add PyMuPDF"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFImageExtractor:
    """Extract pages from PDF files as images"""
    
    def __init__(
        self,
        output_dir: str = "data/images",
        dpi: int = 150,
        image_format: str = "png"
    ):
        """
        Initialize PDF Image Extractor
        
        Args:
            output_dir: Directory to save extracted images
            dpi: Resolution for image extraction (default: 150)
            image_format: Image format (default: 'png')
        """
        self.output_dir = Path(output_dir)
        self.dpi = dpi
        self.image_format = image_format
        self._ensure_output_directory()
    
    def _ensure_output_directory(self) -> None:
        """Create output directory if it doesn't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory ready: {self.output_dir}")
    
    def convert_pdf_to_images(
        self,
        pdf_path: str,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert PDF pages to images
        
        Args:
            pdf_path: Path to the PDF file
            start_page: Starting page number (1-based, inclusive)
            end_page: Ending page number (1-based, inclusive)
        
        Returns:
            List of dictionaries containing image paths and metadata
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"File is not a PDF: {pdf_path}")
        
        # Extract filename without extension
        filename_base = pdf_path.stem
        
        results = []
        
        try:
            # Open PDF document
            pdf_document = fitz.open(str(pdf_path))
            total_pages = len(pdf_document)
            
            # Determine page range
            start_idx = (start_page - 1) if start_page else 0
            end_idx = end_page if end_page else total_pages
            
            # Validate page range
            if start_idx < 0 or end_idx > total_pages:
                raise ValueError(f"Invalid page range. PDF has {total_pages} pages.")
            
            logger.info(f"Processing {pdf_path.name}: {end_idx - start_idx} pages")
            
            # Convert each page
            for page_idx in range(start_idx, end_idx):
                page = pdf_document[page_idx]
                page_num = page_idx + 1  # 1-based page number
                
                # Set up the transformation matrix for the desired DPI
                zoom = self.dpi / 72.0  # PDF default is 72 DPI
                matrix = fitz.Matrix(zoom, zoom)
                
                # Render page to image
                pix = page.get_pixmap(matrix=matrix)
                
                # Generate output filename (1-based indexing)
                output_filename = f"{filename_base}-page-{page_num}.{self.image_format}"
                output_path = self.output_dir / output_filename
                
                # Save image
                pix.save(str(output_path))
                
                # Collect metadata
                result = {
                    "source_pdf": str(pdf_path),
                    "page_number": page_num,
                    "image_path": str(output_path),
                    "width": pix.width,
                    "height": pix.height,
                    "dpi": self.dpi
                }
                results.append(result)
                
                logger.debug(f"Saved page {page_num} to {output_path}")
            
            pdf_document.close()
            logger.info(f"Successfully converted {len(results)} pages from {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
        
        return results
    
    def batch_convert(
        self,
        pdf_files: List[str],
        show_progress: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert multiple PDF files to images
        
        Args:
            pdf_files: List of PDF file paths
            show_progress: Show progress bar
        
        Returns:
            Dictionary mapping PDF paths to their extracted image metadata
        """
        all_results = {}
        
        # Use tqdm for progress if requested
        iterator = tqdm(pdf_files, desc="Converting PDFs") if show_progress else pdf_files
        
        for pdf_path in iterator:
            try:
                results = self.convert_pdf_to_images(pdf_path)
                all_results[pdf_path] = results
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                all_results[pdf_path] = []
        
        # Summary
        total_pages = sum(len(results) for results in all_results.values())
        successful_pdfs = sum(1 for results in all_results.values() if results)
        
        logger.info(
            f"Batch conversion complete: "
            f"{successful_pdfs}/{len(pdf_files)} PDFs, "
            f"{total_pages} total pages extracted"
        )
        
        return all_results
    
    def extract_single_page(
        self,
        pdf_path: str,
        page_number: int
    ) -> Dict[str, Any]:
        """
        Extract a single page from a PDF as an image
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to extract (1-based)
        
        Returns:
            Dictionary containing image path and metadata
        """
        results = self.convert_pdf_to_images(
            pdf_path,
            start_page=page_number,
            end_page=page_number
        )
        
        if not results:
            raise ValueError(f"Failed to extract page {page_number} from {pdf_path}")
        
        return results[0]


def main():
    """
    Example usage and testing
    """
    # Create extractor instance
    extractor = PDFImageExtractor(
        output_dir="data/images",
        dpi=150  # Good balance between quality and file size
    )
    
    # Example: Convert a single PDF
    pdf_file = "data/gv80_owners_manual_TEST6P.pdf"
    
    if os.path.exists(pdf_file):
        try:
            # Convert entire PDF
            results = extractor.convert_pdf_to_images(pdf_file)
            
            print(f"\nExtracted {len(results)} pages:")
            for result in results:
                print(f"  Page {result['page_number']}: {result['image_path']}")
                print(f"    Size: {result['width']}x{result['height']} @ {result['dpi']} DPI")
        
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print(f"Sample PDF not found: {pdf_file}")
        print("Please specify a valid PDF file path")
    
    # Example: Batch conversion
    pdf_files = [
        "data/sample1.pdf",
        "data/sample2.pdf"
    ]
    
    # Filter existing files
    existing_pdfs = [pdf for pdf in pdf_files if os.path.exists(pdf)]
    
    if existing_pdfs:
        batch_results = extractor.batch_convert(existing_pdfs)
        
        print("\nBatch conversion results:")
        for pdf_path, results in batch_results.items():
            print(f"  {pdf_path}: {len(results)} pages extracted")


if __name__ == "__main__":
    main()