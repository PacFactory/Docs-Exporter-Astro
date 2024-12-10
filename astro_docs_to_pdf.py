"""
Astro Documentation PDF Generator
Modified version of Docs-Exporter for Astro documentation

Original work Copyright (C) 2024 Riyooo
Modified work Copyright (C) 2024 PacNPal

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Modifications:
- Replaced wkhtmltopdf with Playwright for PDF generation
- Added support for Astro's MDX format and frontmatter
- Enhanced frontmatter parsing
- Added automatic CSS generation
- Improved error handling and reporting
"""

import os
import markdown
import tempfile
import yaml
import re
import html
import shutil
from pathlib import Path
from git import Repo, RemoteProgress, GitCommandError
from datetime import datetime
from packaging import version
from tqdm import tqdm
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def get_license_notice():
    """Return a formatted license notice for inclusion in output"""
    return """
This PDF was generated by Astro Documentation PDF Generator
Original work Copyright (C) 2024 Riyooo
Modified work Copyright (C) 2024 PacNPal

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License version 3.
Source code is available at: https://github.com/PacFactory/Docs-Exporter-Astro
"""

def add_license_page(html_content):
    """Add a license notice page to the HTML content"""
    license_html = f"""
    <div class="license-notice" style="page-break-before: always;">
        <h2>License Notice</h2>
        <pre style="white-space: pre-wrap; font-family: monospace;">
            {get_license_notice()}
        </pre>
        <p>Complete source code for this program is available at: https://github.com/PacFactory/Docs-Exporter-Astro</p>
        <p>This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you 
        are welcome to redistribute it under certain conditions. See the GNU Affero General 
        Public License version 3 for details.</p>
    </div>
    """
    return html_content + license_html

class DocumentationProcessingError(Exception):
    """Custom exception for documentation processing errors"""
    pass


class CloneProgress(RemoteProgress):
    def __init__(self):
        super().__init__()
        self.pbar = tqdm()

    def update(self, op_code, cur_count, max_count=None, message=''):
        if max_count is not None:
            self.pbar.total = max_count
        self.pbar.update(cur_count - self.pbar.n)

    def finalize(self):
        self.pbar.close()


def cleanup_directory(directory):
    """Safely clean up a directory"""
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
    except Exception as e:
        print(f"Warning: Failed to clean up directory {directory}: {e}")


def process_image_paths(md_content):
    """Process both MDX imports and markdown images, including SVGs"""
    try:
        # Handle MDX image imports
        mdx_pattern = r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        def mdx_replace(match):
            var_name = match.group(1)
            image_path = match.group(2)
            image_path = re.sub(r'^[./~]+', '', image_path)
            return f'![{var_name}](https://docs.astro.build/{image_path})'
        
        md_content = re.sub(mdx_pattern, mdx_replace, md_content)
        
        # Handle standard markdown images and SVGs
        md_pattern = r'!\[(.*?)\]\(([^http].*?)\)'
        def md_replace(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            image_path = re.sub(r'^[./~]+', '', image_path)
            return f'![{alt_text}](https://docs.astro.build/{image_path})'
        
        md_content = re.sub(md_pattern, md_replace, md_content)
        
        # Handle Astro image components
        component_pattern = r'<Image\s+src={([^}]+)}\s+alt="([^"]+)"[^>]*>'
        def component_replace(match):
            src = match.group(1).strip('{}').strip('"\'')
            alt = match.group(2)
            src = re.sub(r'^[./~]+', '', src)
            return f'![{alt}](https://docs.astro.build/{src})'
        
        return re.sub(component_pattern, component_replace, md_content)
    except Exception as e:
        raise DocumentationProcessingError(f"Error processing image paths: {e}")


def preprocess_code_blocks(md_content):
    """Handle Astro's code blocks with advanced features"""
    try:
        pattern = r'```(?:(\w+))?\s*(?:\{([^}]*)\})?\s*(.*?)```'
        
        def replace(match):
            language = match.group(1) or ''
            attributes = match.group(2) or ''
            code_block = match.group(3)
            
            # Parse attributes
            title = ''
            if attributes:
                title_match = re.search(r'title="([^"]+)"', attributes)
                if title_match:
                    title = title_match.group(1)
            
            # Build header
            header_parts = []
            if title:
                header_parts.append(title)
            if language:
                header_parts.append(f"({language})")
            
            header_html = (f'<div class="code-header"><i>{" ".join(header_parts)}</i></div>' 
                         if header_parts else '')
            
            return f'{header_html}\n```{language}\n{code_block.strip()}\n```'
        
        return re.sub(pattern, replace, md_content, flags=re.DOTALL)
    except Exception as e:
        raise DocumentationProcessingError(f"Error processing code blocks: {e}")


def parse_frontmatter(md_content):
    """Parse frontmatter with support for Astro's format"""
    try:
        lines = md_content.split('\n')
        if lines[0].strip() == '---':
            try:
                end_of_frontmatter = lines[1:].index('---') + 1
                frontmatter = '\n'.join(lines[1:end_of_frontmatter])
                content = '\n'.join(lines[end_of_frontmatter + 1:])
                
                # Remove import statements from content
                content = re.sub(r'import.*?\n', '', content)
                
                return frontmatter, content
            except ValueError:
                return None, md_content
        return None, md_content
    except Exception as e:
        raise DocumentationProcessingError(f"Error parsing frontmatter: {e}")


def safe_load_frontmatter(frontmatter_content):
    """Safely load YAML frontmatter with robust error handling"""
    if not frontmatter_content:
        return None

    try:
        # First pass: try to extract title and description using regex
        title_match = re.search(r'title:\s*[\'"]?(.*?)(?:[\'"]?\s*$|[\'"]?\s+\w+:)', frontmatter_content, re.MULTILINE)
        desc_match = re.search(r'description:\s*[\'"]?(.*?)(?:[\'"]?\s*$|[\'"]?\s+\w+:)', frontmatter_content, re.MULTILINE)
        
        # Initialize metadata with found values
        metadata = {}
        if title_match:
            title = title_match.group(1).strip(' \'"')
            metadata['title'] = title
        if desc_match:
            description = desc_match.group(1).strip(' \'"')
            metadata['description'] = description

        # Clean up the frontmatter
        lines = []
        for line in frontmatter_content.split('\n'):
            # Skip problematic lines
            if any(skip in line for skip in ['githubIntegrationURL:', 'label:', 'maxHeadingLevel:']):
                continue
                
            # Clean up quotes and URLs
            if ':' in line:
                key, *value_parts = line.split(':', 1)
                if value_parts:
                    value = value_parts[0]
                    # Handle truncated URLs
                    if 'http' in value and "'" in value and not value.endswith("'"):
                        continue
                    # Handle other truncated quoted strings
                    if value.count("'") == 1 or value.count('"') == 1:
                        continue
                    lines.append(line)
                else:
                    lines.append(line)

        # Try to parse cleaned content
        cleaned_content = '\n'.join(lines)
        try:
            parsed_data = yaml.safe_load(cleaned_content)
            if isinstance(parsed_data, dict):
                # Update metadata with any additional valid fields
                metadata.update(parsed_data)
        except:
            pass  # Use regex-extracted metadata if YAML parsing fails

        return metadata if metadata else None

    except Exception as e:
        print(f"Warning: Error processing frontmatter: {e}")
        return None


def parse_frontmatter(md_content):
    """Parse frontmatter with improved error handling"""
    try:
        lines = md_content.split('\n')
        if lines[0].strip() == '---':
            try:
                # Find the closing --- marker
                end_of_frontmatter = lines[1:].index('---') + 1
                frontmatter = '\n'.join(lines[1:end_of_frontmatter])
                content = '\n'.join(lines[end_of_frontmatter + 1:])
                
                # Clean up frontmatter
                frontmatter = re.sub(r'\s+i18nReady:\s*true', '', frontmatter)
                frontmatter = re.sub(r':\s*\|', ': ', frontmatter)  # Handle YAML block indicators
                
                return frontmatter, content
            except ValueError:
                return None, md_content
        return None, md_content
    except Exception as e:
        print(f"Warning: Error in document structure: {e}")
        return None, md_content

def clone_repo(repo_url, branch, docs_dir, repo_dir):
    """Clone repository with proper error handling and cleanup"""
    progress = None
    try:
        if os.path.exists(repo_dir):
            print("Updating existing repository...")
            repo = Repo(repo_dir)
            origin = repo.remotes.origin
            origin.fetch()
            repo.git.checkout(branch)
            origin.pull()
            print("Repository updated successfully.")
            return

        print("Cloning repository...")
        os.makedirs(repo_dir, exist_ok=True)
        progress = CloneProgress()
        
        # Initialize repository
        repo = Repo.init(repo_dir)
        with repo.config_writer() as git_config:
            git_config.set_value("core", "sparseCheckout", "true")

        # Setup sparse checkout
        sparse_checkout_path = Path(repo_dir) / ".git" / "info" / "sparse-checkout"
        sparse_checkout_path.parent.mkdir(exist_ok=True)
        sparse_checkout_path.write_text(f"/{docs_dir}/*\n")

        # Clone and checkout
        origin = repo.create_remote("origin", repo_url)
        origin.fetch(progress=progress)
        repo.git.checkout(branch)
        print("Repository cloned successfully.")

    except GitCommandError as e:
        cleanup_directory(repo_dir)
        raise DocumentationProcessingError(f"Git operation failed: {e}")
    except Exception as e:
        cleanup_directory(repo_dir)
        raise DocumentationProcessingError(f"Repository operation failed: {e}")
    finally:
        if progress:
            progress.finalize()


def get_files_sorted(root_dir):
    """Get sorted files with comprehensive filtering"""
    try:
        all_files = []
        excluded_dirs = {'node_modules', '.git', '_internal', 'dist', 'temp', '__pycache__'}
        
        for root, dirs, files in os.walk(root_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith('_')]
            
            for file in files:
                if file.endswith(('.md', '.mdx')):
                    full_path = os.path.join(root, file)
                    
                    # Skip excluded paths
                    if any(x in Path(full_path).parts for x in excluded_dirs):
                        continue
                        
                    # Prioritize index files within their directories
                    is_index = file == 'index.md'
                    dir_path = os.path.dirname(full_path)
                    sort_key = f"{dir_path}/{'0' if is_index else '1'}{file}"
                    all_files.append((full_path, sort_key))
        
        if not all_files:
            raise DocumentationProcessingError(f"No markdown files found in {root_dir}")
        
        all_files.sort(key=lambda x: x[1])
        return [full_path for full_path, _ in all_files]
    except Exception as e:
        raise DocumentationProcessingError(f"Error getting sorted files: {e}")


def create_default_css():
    """Create a default CSS file if it doesn't exist"""
    css_content = """
body { 
    font-family: 'Arial', sans-serif; 
    line-height: 1.6; 
    margin: 0; 
    padding: 20px;
    color: #1a1a1a;
}
.master-container { 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    min-height: 100vh;
}
.container { 
    text-align: center; 
    max-width: 800px;
    margin: 0 auto;
}
.title { 
    font-size: 28px; 
    font-weight: bold; 
    margin-bottom: 20px;
    color: #000;
}
.date { 
    font-size: 16px; 
    color: #666;
}
.page-break { 
    page-break-after: always;
}
code { 
    background-color: #f4f4f4; 
    padding: 2px 4px; 
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
}
pre { 
    background-color: #f8f8f8; 
    padding: 15px; 
    border-radius: 5px; 
    overflow-x: auto;
    border: 1px solid #e1e1e1;
}
.code-header { 
    background-color: #e0e0e0; 
    padding: 8px 15px; 
    border-radius: 5px 5px 0 0;
    font-size: 0.9em;
    color: #333;
}
table { 
    border-collapse: collapse; 
    width: 100%; 
    margin: 15px 0;
}
th, td { 
    border: 1px solid #ddd; 
    padding: 12px; 
    text-align: left;
}
th { 
    background-color: #f5f5f5;
    font-weight: bold;
}
img { 
    max-width: 100%; 
    height: auto; 
    margin: 10px 0;
    border-radius: 5px;
}
h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 24px;
    margin-bottom: 16px;
}
h1 { font-size: 2em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
blockquote {
    margin: 0;
    padding: 0 1em;
    color: #6a737d;
    border-left: 0.25em solid #dfe2e5;
}
.doc-path {
    color: #666;
    font-size: 0.9em;
    margin-bottom: 20px;
    padding: 8px;
    background-color: #f8f9fa;
    border-radius: 4px;
}
"""
    try:
        with open('styles.css', 'w', encoding='utf8') as f:
            f.write(css_content.strip())
    except Exception as e:
        raise DocumentationProcessingError(f"Failed to create CSS file: {e}")


def process_files(files, repo_dir, docs_dir):
    """Process markdown files into HTML with error handling"""
    try:
        if not os.path.exists('styles.css'):
            create_default_css()
            
        with open('styles.css', 'r', encoding='utf8') as f:
            css_content = f.read()
            
        toc = []
        html_all_pages_content = []
        numbering = [0]

        html_header = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>{css_content}</style>
        </head>
        <body>
        """

        for index, file_path in enumerate(files):
            try:
                with open(file_path, 'r', encoding='utf8') as f:
                    md_content = f.read()

                md_content = process_image_paths(md_content)
                md_content = preprocess_code_blocks(md_content)
                frontmatter, md_content = parse_frontmatter(md_content)

                if frontmatter:
                    data = safe_load_frontmatter(frontmatter)
                    if data is not None:
                        rel_path = os.path.relpath(file_path, os.path.join(repo_dir, docs_dir))
                        depth = rel_path.count(os.sep)
                        
                        if os.path.basename(file_path) == 'index.md' and depth > 0:
                            depth -= 1
                            
                        indent = '&nbsp;' * 5 * depth

                        while len(numbering) <= depth:
                            numbering.append(0)

                        numbering[depth] += 1
                        for i in range(depth + 1, len(numbering)):
                            numbering[i] = 0

                        toc_numbering = '.'.join(map(str, numbering[:depth + 1]))
                        toc_title = data.get('title', Path(file_path).stem.title())
                        toc_full_title = f"{toc_numbering} - {toc_title}"
                        
                        toc.append(f"{indent}<a href='#{toc_full_title}'>{toc_full_title}</a><br/>")

                        html_page_content = [
                            f"<h1 id='{toc_full_title}'>{toc_full_title}</h1>",
                            f"<div class='doc-path'><p>Documentation path: {Path(file_path).relative_to(Path(repo_dir) / docs_dir).as_posix()}</p></div>"
                        ]

                        if 'description' in data:
                            html_page_content.append(f"<p><strong>Description:</strong> {data['description']}</p>")
                            html_page_content.append('<br/>')
                        
                        # Convert Markdown to HTML with extended features
                        html_page_content.append(markdown.markdown(
                            md_content,
                            extensions=['fenced_code', 'codehilite', 'tables', 'footnotes', 'toc', 'attr_list', 'def_list']
                        ))
                        
                        html_all_pages_content.append('\n'.join(html_page_content))

                        if index < len(files) - 1:
                            html_all_pages_content.append('<div class="page-break"></div>')
                            
            except Exception as e:
                print(f"Warning: Error processing file {file_path}: {e}")
                continue

        if not html_all_pages_content:
            raise DocumentationProcessingError("No content was successfully processed")

        # Create table of contents
        toc_html = f"""
        <div style="padding-bottom: 10px">
            <div style="padding-bottom: 20px">
                <h1>Table of Contents</h1>
            </div>
            {''.join(toc)}
        </div>
        <div style="page-break-before: always;">
        """

        # Combine all content
        final_content = '\n'.join(html_all_pages_content)
        html_all_content = f"{html_header}{toc_html}{final_content}</body></html>"

        return html_all_content

    except Exception as e:
        raise DocumentationProcessingError(f"Error processing documentation: {e}")


def generate_pdf(html_content, output_pdf, format_options=None):
    """Generate PDF using Playwright with enhanced error handling"""
    default_format = {
        'format': 'A4',
        'margin': {
            'top': '50px',
            'right': '50px',
            'bottom': '50px',
            'left': '50px'
        },
        'print_background': True,
        'display_header_footer': True,
        'header_template': '<div style="font-size: 10px; text-align: right; width: 100%; padding-right: 20px; margin-top: 20px;"><span class="pageNumber"></span> of <span class="totalPages"></span></div>',
        'footer_template': '<div style="font-size: 10px; text-align: center; width: 100%; margin-bottom: 20px;"><span class="url"></span></div>'
    }
    
    format_options = format_options or default_format

    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        
        # Set viewport size for consistent rendering
        page.set_viewport_size({"width": 1280, "height": 1024})
        
        # Increase timeouts for better reliability
        page.set_default_timeout(120000)  # 2 minutes
        
        # Set content and wait for loading
        page.set_content(html_content, wait_until='networkidle')
        
        # Additional waits for content
        page.wait_for_load_state('networkidle')
        page.wait_for_load_state('domcontentloaded')
        
        # Generate PDF
        page.pdf(path=output_pdf, **format_options)
        
    except Exception as e:
        raise DocumentationProcessingError(f"Error generating PDF: {str(e)}")
    finally:
        if 'page' in locals():
            page.close()
        if 'context' in locals():
            context.close()
        if 'browser' in locals():
            browser.close()
        if 'playwright' in locals():
            playwright.stop()

def main():
    """Main execution function with error handling"""
    repo_dir = "astro-docs"
    repo_url = "https://github.com/withastro/docs.git"
    branch = "main"
    docs_dir = "src/content/docs/en"
    
    output_pdf = f"Astro_Documentation_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    temp_dir = None

    try:
        # Add version and license information to console
        print(f"""
Astro Documentation PDF Generator v1.0.0
Copyright (C) 2024 PacNPal
This program comes with ABSOLUTELY NO WARRANTY; for details see the LICENSE file.
This is free software, and you are welcome to redistribute it
under certain conditions; see the LICENSE file for details.
""")
        # Create CSS if it doesn't exist
        if not os.path.exists('styles.css'):
            print("Creating default styles.css...")
            create_default_css()
            print("Default CSS file created.")
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Clone repository
        print("Cloning Astro documentation repository...")
        clone_repo(repo_url, branch, docs_dir, repo_dir)

        # Get and sort files
        print("Finding and sorting documentation files...")
        docs_dir_full_path = os.path.join(repo_dir, docs_dir)
        files_to_process = get_files_sorted(docs_dir_full_path)
        print(f"Found {len(files_to_process)} files to process")

        # Create cover page
        with open('styles.css', 'r', encoding='utf8') as f:
            css_content = f.read()
            
        cover_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>{css_content}</style>
        </head>
        <body>
            <div class="master-container">
                <div class="container">
                    <div class="title">Astro Documentation</div>
                    <div class="date">Generated on {datetime.now().strftime('%Y-%m-%d')}</div>
                </div>
            </div>
        </body>
        </html>
        """

        # Process files and generate HTML
        print("Processing documentation files...")
        html_content = process_files(files_to_process, repo_dir, docs_dir)
        
        # Combine cover and content
        final_html = f"{cover_html}<div class='page-break'></div>{html_content}"
        final_html = add_license_page(final_html)

        # Generate PDF
        print(f"Generating PDF: {output_pdf}")
        generate_pdf(final_html, output_pdf)
        
        print(f"Documentation successfully generated: {output_pdf}")
        
    except DocumentationProcessingError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("This program is licensed under AGPL-3.0. Source code is available at: [Your Repository URL]")
        return 1
    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    exit(main())