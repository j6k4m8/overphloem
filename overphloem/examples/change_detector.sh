#!/bin/bash
# change_detector.sh - Example script to be used with overphloem attach command
#
# This script detects changes in an Overleaf project and prints out details
# about the changes.
#
# Usage with overphloem:
#   uv run overphloem attach --project-id YOUR_PROJECT_ID --script ./change_detector.sh --on change
#
# Make this script executable before using:
#   chmod +x change_detector.sh

echo "============================================================"
echo "Change detected at $(date)"
echo "============================================================"

# Get a list of all files in the project
echo "Project files:"
find . -type f -not -path "*/\.*" | sort | while read -r file; do
    # Get file extension
    ext="${file##*.}"

    # Skip binary files and large files
    if [[ "$ext" == "pdf" || "$ext" == "png" || "$ext" == "jpg" || "$ext" == "jpeg" ]]; then
        echo "  $file (binary file)"
    else
        # Get file size
        size=$(wc -c < "$file")
        if [[ $size -lt 10000 ]]; then
            # For smaller files, show line count
            lines=$(wc -l < "$file")
            echo "  $file ($lines lines)"

            # For .tex files, extract section titles
            if [[ "$ext" == "tex" ]]; then
                echo "    Sections:"
                grep -E "\\\\(section|subsection|chapter)\{" "$file" |
                  sed 's/.*{\(.*\)}/    - \1/' | head -5

                # Show if there are more sections
                section_count=$(grep -E "\\\\(section|subsection|chapter)\{" "$file" | wc -l)
                if [[ $section_count -gt 5 ]]; then
                    echo "    ... and $((section_count - 5)) more sections"
                fi
            fi
        else
            echo "  $file (large file, $size bytes)"
        fi
    fi
done

echo ""
echo "Recent changes:"
# Use git to show recent changes (latest commit)
git show --stat

echo ""
echo "Changes complete"
exit 0