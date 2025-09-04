def format_size(size_bytes):
    """Format file size in human readable format"""
    # Convert to float if it's a Decimal
    if hasattr(size_bytes, '__float__'):
        size_bytes = float(size_bytes)
    
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"