
import sys
import os
import re

def create_html_preview(markdown_file):
    if not os.path.exists(markdown_file):
        print(f"Error: File '{markdown_file}' not found.")
        return

    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract mermaid content: Find code blocks with ```mermaid
    match = re.search(r'```mermaid\n(.*?)\n```', content, re.DOTALL)
    if not match:
        print("No mermaid diagram found in the file.")
        return

    mermaid_code = match.group(1)
    
    # HTML Template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mermaid Diagram Preview</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-width: 100%;
            overflow-x: auto;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
    </style>
</head>
<body>
    <h1>Diagram Preview: {os.path.basename(markdown_file)}</h1>
    <div class="container">
        <pre class="mermaid">
{mermaid_code}
        </pre>
    </div>

    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>"""

    output_file = markdown_file.replace('.md', '.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Successfully created preview file: {output_file}")
    print(f"Open this file in your browser to view the diagram.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_diagram_html.py <markdown_file>")
    else:
        create_html_preview(sys.argv[1])
