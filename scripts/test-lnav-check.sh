#!/usr/bin/env bash
# Check for lnav installation
if ! command -v lnav &> /dev/null; then
    echo "Error: lnav is not installed" >&2
    echo "To install on macOS: brew install lnav" >&2
    echo "To install on Linux: sudo apt-get install lnav" >&2
    exit 127
fi
echo "lnav found"
exit 0
