#!/bin/bash
# Package diskcleanup files into a versioned tar.gz

if [ $# -lt 2 ]; then
    echo "Usage: $0 <version> <file1> [file2] [file3] ..."
    echo "Example: $0 2.6.0 diskcleanup.py diskcleanup_core.py diskcleanup.yaml"
    exit 1
fi

VERSION="$1"
shift
PKG_DIR="diskcleanup-${VERSION}"
TARBALL="diskcleanup-${VERSION}.tar.gz"

# Verify all files exist before proceeding
for f in "$@"; do
    if [ ! -e "$f" ]; then
        echo "Error: '$f' not found"
        exit 1
    fi
done

# Create temp directory, copy files, and tar it up
mkdir -p "$PKG_DIR"
cp -r "$@" "$PKG_DIR/"
# Use COPYFILE_DISABLE to prevent macOS extended attributes in the tar
COPYFILE_DISABLE=1 tar czf "$TARBALL" --no-xattrs "$PKG_DIR" 2>/dev/null || \
COPYFILE_DISABLE=1 tar czf "$TARBALL" "$PKG_DIR"
rm -rf "$PKG_DIR"

echo "Created $TARBALL"
