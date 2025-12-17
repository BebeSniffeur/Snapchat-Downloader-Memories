import re
import os
import sys
from .models import Memory
from .utils import print_color, Colors

class HTMLParser:
    def __init__(self, html_file):
        self.html_file = html_file

    def parse(self):
        print_color("📄 Reading HTML file...", Colors.BLUE)

        if not os.path.exists(self.html_file):
            print_color(f"❌ Error: File {self.html_file} does not exist", Colors.RED)
            sys.exit(1)

        with open(self.html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'<tr><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>.*?onclick="downloadMemories\(\'([^\']+)\''
        matches = re.findall(pattern, content)

        memories = []
        seen_urls = set()

        for match in matches:
            date_str, media_type, location_str, url = match

            if url in seen_urls:
                continue
            seen_urls.add(url)

            lat, lon = None, None
            if 'Latitude, Longitude:' in location_str:
                coords_match = re.search(r'Latitude, Longitude:\s*([-\d.]+),\s*([-\d.]+)', location_str)
                if coords_match:
                    lat = float(coords_match.group(1))
                    lon = float(coords_match.group(2))

            memories.append(Memory(
                url=url,
                date=date_str.strip(),
                type=media_type.strip(),
                latitude=lat,
                longitude=lon
            ))

        print_color(f"✓ {len(memories)} unique memories found", Colors.GREEN)
        return memories
