rm -rf /tmp/escmd
nuitka --standalone --onefile --onefile-tempdir-spec=/tmp/escmd --follow-imports --static-libpython=no  --clang --include-package=rich._unicode_data  escmd.py 
#nuitka --standalone  --follow-imports --static-libpython=no  --clang --include-package=rich._unicode_data  escmd.py 
