try:
    import defusedxml.ElementTree as ET
    print("defusedxml is installed")
    try:
        _ = ET.ParseError
        print("ET.ParseError exists")
    except AttributeError:
        print("ET.ParseError DOES NOT exist")
except ImportError:
    print("defusedxml is NOT installed")
