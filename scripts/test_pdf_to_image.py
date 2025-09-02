#!/usr/bin/env python3
"""
Test script for PDF to Image conversion
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ingest.pdf_to_image import PDFImageExtractor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_pdf_conversion():
    """Test converting a single PDF to images"""
    print("\n" + "="*60)
    print("TEST: Single PDF Conversion")
    print("="*60)
    
    # Initialize extractor
    extractor = PDFImageExtractor(
        output_dir="data/images",
        dpi=150  # Good quality for text documents
    )
    
    # Look for test PDF
    test_pdfs = [
        "data/gv80_owners_manual_TEST6P.pdf",
        "data/디지털정부혁신_추진계획.pdf",
        "data/sample.pdf"
    ]
    
    pdf_file = None
    for pdf in test_pdfs:
        if os.path.exists(pdf):
            pdf_file = pdf
            break
    
    if not pdf_file:
        print("❌ No test PDF found in data folder")
        print("   Please place a PDF file in the data folder")
        return False
    
    print(f"📄 Found test PDF: {pdf_file}")
    
    try:
        # Convert PDF to images
        results = extractor.convert_pdf_to_images(pdf_file)
        
        print(f"\n✅ Successfully extracted {len(results)} pages:")
        for i, result in enumerate(results[:5], 1):  # Show first 5 pages
            print(f"\n  Page {result['page_number']}:")
            print(f"    📁 Image: {result['image_path']}")
            print(f"    📐 Size: {result['width']}x{result['height']} pixels")
            print(f"    🎯 DPI: {result['dpi']}")
            
            # Check if file was actually created
            if os.path.exists(result['image_path']):
                file_size = os.path.getsize(result['image_path']) / 1024  # KB
                print(f"    💾 File size: {file_size:.1f} KB")
        
        if len(results) > 5:
            print(f"\n  ... and {len(results) - 5} more pages")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during conversion: {str(e)}")
        return False


def test_page_range_extraction():
    """Test extracting specific page ranges"""
    print("\n" + "="*60)
    print("TEST: Page Range Extraction")
    print("="*60)
    
    extractor = PDFImageExtractor(
        output_dir="data/images",
        dpi=100  # Lower DPI for faster testing
    )
    
    # Look for test PDF
    pdf_file = None
    for pdf in ["data/gv80_owners_manual_TEST6P.pdf", "data/sample.pdf"]:
        if os.path.exists(pdf):
            pdf_file = pdf
            break
    
    if not pdf_file:
        print("❌ No test PDF found")
        return False
    
    try:
        # Extract pages 1-3 only
        print(f"📄 Extracting pages 1-3 from {pdf_file}")
        results = extractor.convert_pdf_to_images(
            pdf_file,
            start_page=1,
            end_page=3
        )
        
        print(f"✅ Extracted {len(results)} pages:")
        for result in results:
            print(f"  - Page {result['page_number']}: {Path(result['image_path']).name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_single_page_extraction():
    """Test extracting a single page"""
    print("\n" + "="*60)
    print("TEST: Single Page Extraction")
    print("="*60)
    
    extractor = PDFImageExtractor(
        output_dir="data/images",
        dpi=200  # Higher DPI for single page
    )
    
    pdf_file = None
    for pdf in ["data/gv80_owners_manual_TEST6P.pdf", "data/sample.pdf"]:
        if os.path.exists(pdf):
            pdf_file = pdf
            break
    
    if not pdf_file:
        print("❌ No test PDF found")
        return False
    
    try:
        # Extract page 1 only
        print(f"📄 Extracting page 1 from {pdf_file}")
        result = extractor.extract_single_page(pdf_file, page_number=1)
        
        print(f"✅ Extracted page {result['page_number']}:")
        print(f"   📁 Saved to: {result['image_path']}")
        print(f"   📐 Resolution: {result['width']}x{result['height']} @ {result['dpi']} DPI")
        
        if os.path.exists(result['image_path']):
            file_size = os.path.getsize(result['image_path']) / 1024
            print(f"   💾 File size: {file_size:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_batch_conversion():
    """Test batch conversion of multiple PDFs"""
    print("\n" + "="*60)
    print("TEST: Batch PDF Conversion")
    print("="*60)
    
    extractor = PDFImageExtractor(
        output_dir="data/images",
        dpi=100  # Lower DPI for batch processing
    )
    
    # Find all PDFs in data folder
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in data folder")
        return False
    
    print(f"📚 Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files[:3]:  # Show first 3
        print(f"  - {pdf.name}")
    
    if len(pdf_files) > 3:
        print(f"  ... and {len(pdf_files) - 3} more")
    
    try:
        # Convert all PDFs
        pdf_paths = [str(pdf) for pdf in pdf_files[:2]]  # Limit to first 2 for testing
        batch_results = extractor.batch_convert(pdf_paths, show_progress=True)
        
        print(f"\n✅ Batch conversion complete:")
        total_pages = 0
        for pdf_path, results in batch_results.items():
            pdf_name = Path(pdf_path).name
            print(f"  📄 {pdf_name}: {len(results)} pages")
            total_pages += len(results)
        
        print(f"\n📊 Total: {total_pages} pages extracted from {len(batch_results)} PDFs")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🔧 "*20)
    print("PDF TO IMAGE CONVERTER TEST SUITE")
    print("🔧 "*20)
    
    # First, install PyMuPDF if needed
    try:
        import fitz
        print("✅ PyMuPDF is installed")
    except ImportError:
        print("⚠️  PyMuPDF not installed. Installing...")
        os.system("uv add PyMuPDF")
        print("✅ PyMuPDF installed")
    
    # Create data/images directory if it doesn't exist
    images_dir = Path("data/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory ready: {images_dir}")
    
    # Run tests
    tests = [
        ("Single PDF Conversion", test_single_pdf_conversion),
        ("Page Range Extraction", test_page_range_extraction),
        ("Single Page Extraction", test_single_page_extraction),
        ("Batch Conversion", test_batch_conversion)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with error: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed successfully!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    main()