#!/bin/bash

update_mermaid_diagram() {
  local diagram_file="$1"
  local output_html="${2:-mermaid_output.html}"
  
  if [[ ! -f "$diagram_file" ]]; then
    echo "Error: Diagram file '$diagram_file' not found."
    return 1
  fi
  
  # Read the Mermaid content
  local mermaid_content=$(cat "$diagram_file")
  
  # Create HTML with Mermaid.js
  cat > "$output_html" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mermaid Diagram Viewer</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default'
    });
  </script>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 20px;
    }
    .mermaid {
      margin: 20px auto;
    }
    .info {
      margin-bottom: 20px;
      color: #555;
    }
  </style>
</head>
<body>
  <div class="info">
    <h1>Mermaid Diagram Viewer</h1>
    <p>Source file: $diagram_file</p>
    <p>Last updated: $(date)</p>
  </div>
  <div class="mermaid">
$mermaid_content
  </div>
</body>
</html>
EOF

  echo "Mermaid diagram HTML generated at '$output_html'"
  
  # Open in browser
  if command -v xdg-open &>/dev/null; then
    xdg-open "$output_html"
  elif command -v open &>/dev/null; then
    open "$output_html"
  elif command -v start &>/dev/null; then
    start "$output_html"
  else
    echo "Could not detect a command to open the browser. Please open '$output_html' manually."
  fi
}

# If the script is being run directly rather than sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <mermaid_diagram_file> [output_html_file]"
    exit 1
  fi
  
  update_mermaid_diagram "$1" "${2:-}"
fi
