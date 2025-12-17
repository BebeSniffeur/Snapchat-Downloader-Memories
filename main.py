#!/usr/bin/env python3

import sys
from src.config import HTML_FILE, OUTPUT_DIR, MAX_WORKERS
from src.parser import HTMLParser
from src.downloader import Downloader
from src.zip_processor import ZipProcessor
from src.utils import print_color, Colors, ask_organization_mode, \
    ask_filename_format


def main():
    print_color("\n" + "=" * 80, Colors.BLUE)
    print_color("📸 SNAPCHAT MEMORIES DOWNLOADER", Colors.BOLD)
    print_color("=" * 80 + "\n", Colors.BLUE)

    organization_mode = ask_organization_mode()
    filename_format = ask_filename_format()
    zip_mode = ZipProcessor.ask_processing_mode()

    parser = HTMLParser(HTML_FILE)
    memories = parser.parse()

    if not memories:
        print_color("❌ No memories found in HTML file", Colors.RED)
        sys.exit(1)

    downloader = Downloader(OUTPUT_DIR, MAX_WORKERS, organization_mode,
                            filename_format)
    downloader.download_all(memories)

    processor = ZipProcessor(OUTPUT_DIR, zip_mode, filename_format)
    processor.process_all()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n\n⚠️  Download interrupted by user. Exiting...",
                    Colors.YELLOW)
        sys.exit(0)
    except Exception as e:
        print_color(f"\n❌ Unexpected Error : {str(e)}", Colors.RED)
        sys.exit(1)
