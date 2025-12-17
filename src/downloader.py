import os
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm
from .utils import print_color, Colors, format_size, format_filename_date
from .config import TIMEOUT, MAX_RETRIES, RETRY_DELAY

class Downloader:
    def __init__(self, output_dir, max_workers, organization_mode='by_date', filename_format='1'):
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.organization_mode = organization_mode
        self.filename_format = filename_format
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def download_single(self, memory):
        try:
            url = memory.url
            date_str = memory.date

            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                if self.organization_mode == 'by_date':
                    date_folder = date_obj.strftime("%Y/%m")
                else:
                    date_folder = ""
            except:
                date_folder = "unknown_date" if self.organization_mode == 'by_date' else ""
                date_obj = None

            target_dir = os.path.join(self.output_dir, date_folder) if date_folder else self.output_dir
            date_formatted = format_filename_date(date_str, self.filename_format)

            if os.path.exists(target_dir):
                existing_files = [f for f in os.listdir(target_dir) if f.startswith(date_formatted)]
                if existing_files:
                    existing_file = existing_files[0]
                    file_size = os.path.getsize(os.path.join(target_dir, existing_file))
                    if file_size > 0:
                        return {'status': 'skipped', 'filename': existing_file, 'size': file_size}

            last_error = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = self.session.get(url, timeout=TIMEOUT)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get('Content-Type', '')
                    break
                except requests.exceptions.RequestException as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (2 ** attempt))
                    else:
                        raise

            if 'image/jpeg' in content_type:
                extension = 'jpg'
            elif 'image/png' in content_type:
                extension = 'png'
            elif 'image/gif' in content_type:
                extension = 'gif'
            elif 'video/mp4' in content_type or 'video/quicktime' in content_type:
                extension = 'mp4'
            elif 'application/zip' in content_type:
                extension = 'zip'
            else:
                if content[:4] == b'\xff\xd8\xff\xe0' or content[:4] == b'\xff\xd8\xff\xe1':
                    extension = 'jpg'
                elif content[:8] == b'\x89PNG\r\n\x1a\n':
                    extension = 'png'
                elif content[:4] == b'GIF8':
                    extension = 'gif'
                elif b'ftyp' in content[:20]:
                    extension = 'mp4'
                else:
                    extension = 'dat'

            Path(target_dir).mkdir(parents=True, exist_ok=True)
            filename = f"{date_formatted}.{extension}"
            filepath = os.path.join(target_dir, filename)

            counter = 1
            while os.path.exists(filepath):
                filename = f"{date_formatted}_{counter}.{extension}"
                filepath = os.path.join(target_dir, filename)
                counter += 1

            with open(filepath, 'wb') as f:
                f.write(content)

            if date_obj:
                timestamp_seconds = date_obj.timestamp()
                os.utime(filepath, (timestamp_seconds, timestamp_seconds))

            return {'status': 'success', 'filename': filename, 'size': len(content)}

        except requests.exceptions.RequestException as e:
            return {'status': 'failed', 'url': url, 'error': str(e)}
        except Exception as e:
            return {'status': 'error', 'url': url, 'error': str(e)}

    def download_all(self, memories):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        total = len(memories)
        success_count = 0
        skipped_count = 0
        failed_count = 0
        total_size = 0
        failed_items = []

        print_color(f"\n🚀 Starting download of {total} memories with {self.max_workers} threads...\n", Colors.BOLD)

        start_time = time.time()

        with tqdm(total=total, desc="📥 Download", unit="memory",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                  colour="green") as pbar:

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_memory = {
                    executor.submit(self.download_single, memory): memory
                    for memory in memories
                }

                for future in as_completed(future_to_memory):
                    memory = future_to_memory[future]
                    result = future.result()

                    if result['status'] == 'success':
                        success_count += 1
                        total_size += result['size']
                        pbar.set_postfix_str(f"✓ {success_count} | ⊘ {skipped_count} | ✗ {failed_count}")
                    elif result['status'] == 'skipped':
                        skipped_count += 1
                        pbar.set_postfix_str(f"✓ {success_count} | ⊘ {skipped_count} | ✗ {failed_count}")
                    else:
                        failed_count += 1
                        failed_items.append({
                            'url': memory.url,
                            'date': memory.date,
                            'error': result.get('error', 'Unknown error')
                        })
                        pbar.set_postfix_str(f"✓ {success_count} | ⊘ {skipped_count} | ✗ {failed_count}")

                    pbar.update(1)

        self.session.close()
        elapsed_time = time.time() - start_time

        print_color("\n" + "="*80, Colors.BLUE)
        print_color("📊 DOWNLOAD SUMMARY", Colors.BOLD)
        print_color("="*80, Colors.BLUE)
        print_color(f"✓ Successfully downloaded: {success_count}", Colors.GREEN)
        print_color(f"⊘ Already existing (skipped): {skipped_count}", Colors.YELLOW)
        print_color(f"✗ Failed: {failed_count}", Colors.RED)
        print_color(f"📁 Total size downloaded: {format_size(total_size)}", Colors.CYAN)
        print_color(f"⏱️  Elapsed time: {elapsed_time:.2f} seconds", Colors.CYAN)

        if elapsed_time > 0:
            speed = success_count / elapsed_time
            print_color(f"🚀 Average speed: {speed:.2f} memories/second", Colors.CYAN)

        print_color(f"📂 Output folder: {os.path.abspath(self.output_dir)}", Colors.BLUE)
        print_color("="*80 + "\n", Colors.BLUE)

        if failed_items and len(failed_items) <= 10:
            print_color("⚠️  Failed memories:", Colors.YELLOW)
            for item in failed_items:
                print(f"  • {item['date']} - {item['url'][:60]}...")
                print(f"    Error: {item['error']}")

        if success_count > 0:
            print_color("🎉 Download completed successfully!", Colors.GREEN)
        elif skipped_count == total:
            print_color("ℹ️  All memories were already downloaded", Colors.YELLOW)
        else:
            print_color("⚠️  Download completed with errors", Colors.YELLOW)
