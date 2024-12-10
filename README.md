# Astro Documentation PDF Generator

A Python script to generate a PDF from Astro's documentation. Forked from [Docs-Exporter](https://github.com/Riyooo/Docs-Exporter) and modified to work with Astro's documentation format.

## Overview

This script:
- Clones the Astro documentation repository
- Processes Markdown/MDX files
- Generates a PDF with:
  - Cover page
  - Table of contents
  - Formatted content
  - Headers and footers
  - Code syntax highlighting
  - Proper page breaks

## Requirements

### System Requirements
- Python 3.7+
- Git installed and accessible from command line
- Internet connection for cloning repositories

### Python Dependencies
```bash
pip install gitpython markdown packaging playwright pyyaml tqdm
playwright install chromium
```

## Usage

1. Clone this repository:
```bash
git clone <your-repo-url>
cd <repo-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

3. Run the script:
```bash
python astro_docs_to_pdf.py
```

The script will:
- Create a default styles.css if none exists
- Clone the Astro documentation
- Process all documentation files
- Generate a PDF with table of contents

## Output

The script generates:
- A PDF file named `Astro_Documentation_YYYY-MM-DD.pdf`
- Default styling for documentation content
- Hierarchical table of contents
- Page numbers and generation date

## Features

- Automatic table of contents generation
- Code block syntax highlighting
- Image processing
- Proper handling of Astro's MDX format
- Frontmatter parsing
- Clean page breaks
- Responsive design
- Error handling and reporting

## Modifications from Original

This fork includes several modifications from the original Docs-Exporter:
- Updated to use Playwright instead of wkhtmltopdf
- Added support for Astro's specific MDX format
- Enhanced frontmatter parsing
- Improved error handling
- Automatic CSS generation
- Better image handling

## Credits

- Original project: [Docs-Exporter](https://github.com/Riyooo/Docs-Exporter) by Riyooo
- Modified for Astro documentation format

## License

[Include the original project's license information here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
