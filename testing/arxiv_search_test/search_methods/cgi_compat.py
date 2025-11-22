"""
Compatibility shim for the deprecated cgi module in Python 3.13+
This provides the parse_header function that feedparser needs.
"""
import sys

def parse_header(line):
    """Parse a Content-type like header.
    
    Return the main content-type and a dictionary of options.
    This is a simplified version of the old cgi.parse_header function.
    """
    parts = line.split(';')
    main_type = parts[0].strip()
    pdict = {}
    for p in parts[1:]:
        if '=' in p:
            name, val = p.split('=', 1)
            name = name.strip().lower()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] == '"':
                val = val[1:-1]
                val = val.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = val
    return main_type, pdict

# Install the compatibility shim if cgi module is missing
if sys.version_info >= (3, 13):
    try:
        import cgi
    except ModuleNotFoundError:
        # Create a fake cgi module with parse_header
        import types
        cgi = types.ModuleType('cgi')
        cgi.parse_header = parse_header
        sys.modules['cgi'] = cgi
