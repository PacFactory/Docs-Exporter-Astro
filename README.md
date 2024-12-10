# README.md
# Astro Documentation to PDF Converter

A Python script that automatically generates a well-formatted PDF from Astro's documentation repository. The script clones the documentation, processes all markdown files, and creates a PDF with a table of contents, proper formatting, and consistent styling.

## Features

- Automatic repository cloning and updating
- Comprehensive documentation processing
- Table of contents generation
- Code block syntax highlighting
- Image path handling
- Proper page breaks
- Custom header and footer
- Error handling and recovery
- Progress reporting
- Clean temporary file management

## Requirements

### System Requirements
- Python 3.7 or higher
- Git installed and accessible from command line
- Internet connection for repository access

### Python Dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```

Install Playwright's browser:
```bash
playwright install chromium
```

## Installation

1. Clone this repository or download the script files:
```bash
git clone 
cd 
```

2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

3. Ensure you have the following files in your directory:
   - `astro_docs_to_pdf.py` (main script)
   - `requirements.txt`
   - `styles.css` (will be created automatically if missing)

## Usage

Run the script:
```bash
python astro_docs_to_pdf.py
```

The script will:
1. Clone/update the Astro documentation repository
2. Process all documentation files
3. Generate a PDF with proper formatting
4. Create a table of contents
5. Output the final PDF as `Astro_Documentation_YYYY-MM-DD.pdf`

## Output

The generated PDF includes:
- Cover page with title and date
- Table of contents with page numbers
- Formatted documentation content
- Code syntax highlighting
- Properly sized images
- Headers and footers with page numbers
- Consistent styling throughout

## Customization

### CSS Styling
The script creates a default `styles.css` file if none exists. You can modify this file to customize the PDF's appearance.

### Output Options
You can modify these variables in the script:
```python
repo_dir = "astro-docs"  # Local directory for cloned repo
output_pdf = f"Astro_Documentation_{datetime.now().strftime('%Y-%m-%d')}.pdf"  # Output filename
```

### PDF Format
Adjust the PDF format options in the `generate_pdf` function:
```python
format_options = {
    'format': 'A4',
    'margin': {
        'top': '50px',
        'right': '50px',
        'bottom': '50px',
        'left': '50px'
    },
    'print_background': True,
    # ... other options
}
```

## Troubleshooting

### Common Issues

1. **Git Clone Failures**
   - Ensure you have git installed
   - Check your internet connection
   - Verify repository access permissions

2. **PDF Generation Errors**
   - Check if output PDF is already open
   - Ensure enough disk space
   - Verify Playwright browser installation

3. **Image Loading Issues**
   - Check internet connection
   - Verify image paths in documentation
   - Ensure Playwright timeouts are sufficient

4. **Styling Problems**
   - Verify styles.css exists and is readable
   - Check CSS syntax
   - Ensure no conflicting styles

### Error Messages

The script provides detailed error messages for common issues:
- Repository cloning failures
- File processing errors
- PDF generation problems
- Resource cleanup issues

## Limitations

- Requires active internet connection
- May take several minutes for large documentation sets
- Memory usage scales with documentation size
- Some complex MDX components may not render perfectly

## Contributing

Contributions are welcome! Please feel free to:
1. Report bugs
2. Suggest improvements
3. Submit pull requests

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built using Playwright for PDF generation
- Processes documentation from the official Astro docs repository
- Uses Python's markdown library for processing
