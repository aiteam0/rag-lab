#!/usr/bin/env python3
"""
Simple script to convert PDF files to images
Usage: python convert_pdf_to_images.py <pdf_file_path>
"""

import sys
import os
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ingest.pdf_to_image import PDFImageExtractor


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to page images"
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the PDF file to convert"
    )
    parser.add_argument(
        "--output-dir",
        default="data/images",
        help="Output directory for images (default: data/images)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for image extraction (default: 150)"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        help="Start page (1-based)"
    )
    parser.add_argument(
        "--end-page",
        type=int,
        help="End page (1-based, inclusive)"
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg", "jpeg"],
        help="Output image format (default: png)"
    )
    
    args = parser.parse_args()
    
    # Check if PDF exists
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Create extractor
    extractor = PDFImageExtractor(
        output_dir=args.output_dir,
        dpi=args.dpi,
        image_format=args.format
    )
    
    print(f"📄 Converting PDF: {args.pdf_path}")
    print(f"📁 Output directory: {args.output_dir}")
    print(f"🎯 DPI: {args.dpi}")
    
    if args.start_page or args.end_page:
        print(f"📑 Page range: {args.start_page or 'start'} to {args.end_page or 'end'}")
    
    try:
        # Convert PDF
        results = extractor.convert_pdf_to_images(
            args.pdf_path,
            start_page=args.start_page,
            end_page=args.end_page
        )
        
        print(f"\n✅ Successfully extracted {len(results)} pages:")
        
        # Show first few and last page
        for i, result in enumerate(results):
            if i < 3 or i == len(results) - 1:
                filename = Path(result['image_path']).name
                print(f"  Page {result['page_number']:3d}: {filename}")
            elif i == 3:
                print(f"  ... ({len(results) - 4} more pages)")
        
        # Calculate total size
        total_size = sum(
            os.path.getsize(r['image_path']) 
            for r in results 
            if os.path.exists(r['image_path'])
        ) / (1024 * 1024)  # MB
        
        print(f"\n📊 Total size: {total_size:.1f} MB")
        print(f"📊 Average size per page: {total_size/len(results):.2f} MB")
        
    except Exception as e:
        print(f"❌ Error during conversion: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    """
    사용 방법:
  # PyMuPDF 설치
  uv add PyMuPDF

  # 단일 PDF 변환
  python scripts/convert_pdf_to_images.py data/sample.pdf

  # 옵션 지정
  python scripts/convert_pdf_to_images.py data/sample.pdf --dpi 200
  --start-page 1 --end-page 5

  # Python 코드에서 사용
  from ingest import PDFImageExtractor
  extractor = PDFImageExtractor(output_dir="data/images", dpi=150)
  results = extractor.convert_pdf_to_images("data/sample.pdf")
    """
    main()