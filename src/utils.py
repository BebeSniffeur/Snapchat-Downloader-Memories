class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_color(text, color):
    print(f"{color}{text}{Colors.RESET}")

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def ask_organization_mode():
    print_color("\n" + "="*80, Colors.BLUE)
    print_color("📁 FILE ORGANIZATION", Colors.BOLD)
    print_color("="*80, Colors.BLUE)
    print("\nHow do you want to organize your memories?")
    print(f"{Colors.CYAN}1.{Colors.RESET} By date (year/month folders) - Recommended")
    print(f"{Colors.CYAN}2.{Colors.RESET} All in one folder")

    while True:
        choice = input(f"\n{Colors.BOLD}Your choice [1-2]:{Colors.RESET} ").strip()
        if choice == '1':
            return 'by_date'
        elif choice == '2':
            return 'flat'
        else:
            print_color("❌ Invalid choice. Enter 1 or 2.", Colors.RED)

def ask_filename_format():
    print_color("\n" + "="*80, Colors.BLUE)
    print_color("📝 FILENAME FORMAT", Colors.BOLD)
    print_color("="*80, Colors.BLUE)
    print("\nChoose the filename date format:")
    print(f"{Colors.CYAN}1.{Colors.RESET} 20251215_213158 (Compact)")
    print(f"{Colors.CYAN}2.{Colors.RESET} 2025-12-15_21-31-58 (Readable)")
    print(f"{Colors.CYAN}3.{Colors.RESET} 2025-12-15 (Date only)")
    print(f"{Colors.CYAN}4.{Colors.RESET} 20251215 (Compact date only)")

    while True:
        choice = input(f"\n{Colors.BOLD}Your choice [1-4]:{Colors.RESET} ").strip()
        if choice in ['1', '2', '3', '4']:
            return choice
        else:
            print_color("❌ Invalid choice. Enter 1-4.", Colors.RED)

def format_filename_date(date_str, format_type='1'):
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
        if format_type == '1':
            return date_obj.strftime("%Y%m%d_%H%M%S")
        elif format_type == '2':
            return date_obj.strftime("%Y-%m-%d_%H-%M-%S")
        elif format_type == '3':
            return date_obj.strftime("%Y-%m-%d")
        elif format_type == '4':
            return date_obj.strftime("%Y%m%d")
    except:
        pass
    return "unknown"
