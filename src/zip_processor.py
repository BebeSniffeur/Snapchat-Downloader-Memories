import os
import re
import zipfile
import subprocess
import time
from io import BytesIO
from datetime import datetime
from tqdm import tqdm
from .utils import print_color, Colors
from .config import MAX_RETRIES, RETRY_DELAY
from PIL import Image


class ZipProcessor:
    def __init__(self, output_dir, mode, filename_format='1'):
        self.output_dir = output_dir
        self.mode = mode
        self.filename_format = filename_format

    @staticmethod
    def parse_date_from_filename(date_formatted):
        formats = [
            ("%Y%m%d_%H%M%S", r'\d{8}_\d{6}'),
            ("%Y-%m-%d_%H-%M-%S", r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'),
            ("%Y-%m-%d", r'\d{4}-\d{2}-\d{2}'),
            ("%Y%m%d", r'\d{8}'),
        ]

        for fmt, pattern in formats:
            if re.match(pattern, date_formatted):
                try:
                    return datetime.strptime(date_formatted, fmt)
                except:
                    pass
        return None

    @staticmethod
    def set_file_date(filepath, date_obj):
        if date_obj and os.path.exists(filepath):
            timestamp = date_obj.timestamp()
            os.utime(filepath, (timestamp, timestamp))

    @staticmethod
    def check_already_processed(self, target_dir, date_formatted):
        """Check if ZIP has already been processed by looking for output files"""
        if not os.path.exists(target_dir):
            return False

        existing_files = [f for f in os.listdir(target_dir)
                          if f.startswith(date_formatted) and not f.endswith(
                '.zip')]

        if existing_files:
            for f in existing_files:
                filepath = os.path.join(target_dir, f)
                if os.path.getsize(filepath) > 0:
                    return True
        return False

    @staticmethod
    def ask_processing_mode():
        print_color("\n" + "=" * 80, Colors.BLUE)
        print_color("🗜️  ZIP FILE PROCESSING", Colors.BOLD)
        print_color("=" * 80, Colors.BLUE)
        print(
            "\nZIP files contain the original media + a PNG overlay (text/drawings).")
        print("\nAvailable options:")
        print(
            f"{Colors.CYAN}1.{Colors.RESET} Original + composed (without separate PNG) (Recommended)")
        print(
            f"{Colors.CYAN}2.{Colors.RESET} Composed only (with overlay applied)")
        print(
            f"{Colors.CYAN}3.{Colors.RESET} Original only (without overlay)")
        print(
            f"{Colors.CYAN}4.{Colors.RESET} Keep everything: original + overlay + composed")

        while True:
            choice = input(
                f"\n{Colors.BOLD}Your choice [1-4]:{Colors.RESET} ").strip()
            if choice == '1':
                return 'both'
            elif choice == '2':
                return 'composed'
            elif choice == '3':
                return 'original'
            elif choice == '4':
                return 'all'
            else:
                print_color("❌ Invalid choice. Enter a number between 1 and 4.",
                            Colors.RED)

    @staticmethod
    def compose_image(media_data, overlay_data, output_path):
        if not Image:
            return False

        try:
            base_img = Image.open(BytesIO(media_data))
            overlay_img = Image.open(BytesIO(overlay_data))

            if base_img.mode != 'RGBA':
                base_img = base_img.convert('RGBA')
            if overlay_img.mode != 'RGBA':
                overlay_img = overlay_img.convert('RGBA')

            if overlay_img.size != base_img.size:
                overlay_img = overlay_img.resize(base_img.size,
                                                 Image.Resampling.LANCZOS)

            composed = Image.alpha_composite(base_img, overlay_img)

            if output_path.lower().endswith('.jpg'):
                composed = composed.convert('RGB')

            composed.save(output_path, quality=95)
            return True
        except Exception:
            return False

    @staticmethod
    def compose_video(video_path, overlay_path, output_path):
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', overlay_path,
                '-filter_complex', '[0:v][1:v]overlay',
                '-codec:a', 'copy',
                '-y',
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception:
            return False

    def process_single_zip(self, zip_path, target_dir, date_formatted):
        if self.check_already_processed(target_dir, date_formatted):
            return 'skipped'

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return self._process_single_zip_impl(zip_path, target_dir,
                                                     date_formatted)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(
                        RETRY_DELAY * (2 ** attempt))
                else:
                    return False

    def _process_single_zip_impl(self, zip_path, target_dir, date_formatted):
        try:
            date_obj = self.parse_date_from_filename(date_formatted)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

                media_file = None
                overlay_file = None

                for filename in file_list:
                    if filename.lower().endswith(
                            '.png') and 'overlay' in filename.lower():
                        overlay_file = filename
                    elif filename.lower().endswith(
                            ('.jpg', '.jpeg', '.mp4', '.mov')):
                        media_file = filename

                if not media_file or not overlay_file:
                    for filename in file_list:
                        if filename.lower().endswith('.png'):
                            overlay_file = filename
                        elif filename.lower().endswith(
                                ('.jpg', '.jpeg', '.mp4', '.mov')):
                            media_file = filename

                if not media_file:
                    return False

                media_data = zip_ref.read(media_file)
                overlay_data = zip_ref.read(
                    overlay_file) if overlay_file else None

                media_ext = os.path.splitext(media_file)[1].lower().replace('.',
                                                                            '')
                if media_ext == 'jpeg':
                    media_ext = 'jpg'
                elif media_ext == 'mov':
                    media_ext = 'mp4'

                is_video = media_ext in ['mp4']
                is_image = media_ext in ['jpg', 'png']

                if self.mode == 'all':
                    original_path = os.path.join(target_dir,
                                                 f"{date_formatted}_original.{media_ext}")
                    with open(original_path, 'wb') as f:
                        f.write(media_data)
                    self.set_file_date(original_path, date_obj)

                    if overlay_data:
                        overlay_path = os.path.join(target_dir,
                                                    f"{date_formatted}_overlay.png")
                        with open(overlay_path, 'wb') as f:
                            f.write(overlay_data)
                        self.set_file_date(overlay_path, date_obj)

                        if is_image and Image:
                            try:
                                composed_path = os.path.join(target_dir,
                                                             f"{date_formatted}_composed.{media_ext}")
                                self.compose_image(media_data, overlay_data,
                                                   composed_path)
                                self.set_file_date(composed_path, date_obj)
                            except:
                                pass
                        elif is_video:
                            try:
                                composed_path = os.path.join(target_dir,
                                                             f"{date_formatted}_composed.{media_ext}")
                                self.compose_video(original_path, overlay_path,
                                                   composed_path)
                                self.set_file_date(composed_path, date_obj)
                            except:
                                pass

                elif self.mode == 'composed':
                    if overlay_data:
                        if is_image and Image:
                            composed_path = os.path.join(target_dir,
                                                         f"{date_formatted}.{media_ext}")
                            self.compose_image(media_data, overlay_data,
                                               composed_path)
                            self.set_file_date(composed_path, date_obj)
                        elif is_video:
                            temp_video = os.path.join(target_dir,
                                                      f"{date_formatted}_temp.{media_ext}")
                            temp_overlay = os.path.join(target_dir,
                                                        f"{date_formatted}_temp_overlay.png")
                            composed_path = os.path.join(target_dir,
                                                         f"{date_formatted}.{media_ext}")

                            with open(temp_video, 'wb') as f:
                                f.write(media_data)
                            with open(temp_overlay, 'wb') as f:
                                f.write(overlay_data)

                            if self.compose_video(temp_video, temp_overlay,
                                                  composed_path):
                                os.remove(temp_video)
                                os.remove(temp_overlay)
                                self.set_file_date(composed_path, date_obj)
                            else:
                                os.rename(temp_video, composed_path)
                                self.set_file_date(composed_path, date_obj)
                                if os.path.exists(temp_overlay):
                                    os.remove(temp_overlay)
                        else:
                            original_path = os.path.join(target_dir,
                                                         f"{date_formatted}.{media_ext}")
                            with open(original_path, 'wb') as f:
                                f.write(media_data)
                            self.set_file_date(original_path, date_obj)
                    else:
                        original_path = os.path.join(target_dir,
                                                     f"{date_formatted}.{media_ext}")
                        with open(original_path, 'wb') as f:
                            f.write(media_data)
                        self.set_file_date(original_path, date_obj)

                elif self.mode == 'original':
                    original_path = os.path.join(target_dir,
                                                 f"{date_formatted}.{media_ext}")
                    with open(original_path, 'wb') as f:
                        f.write(media_data)
                    self.set_file_date(original_path, date_obj)

                elif self.mode == 'both':
                    original_path = os.path.join(target_dir,
                                                 f"{date_formatted}_original.{media_ext}")
                    with open(original_path, 'wb') as f:
                        f.write(media_data)
                    self.set_file_date(original_path, date_obj)

                    if overlay_data:
                        if is_image and Image:
                            try:
                                composed_path = os.path.join(target_dir,
                                                             f"{date_formatted}_composed.{media_ext}")
                                self.compose_image(media_data, overlay_data,
                                                   composed_path)
                                self.set_file_date(composed_path, date_obj)
                            except:
                                pass
                        elif is_video:
                            try:
                                temp_overlay = os.path.join(target_dir,
                                                            f"{date_formatted}_temp_overlay.png")
                                with open(temp_overlay, 'wb') as f:
                                    f.write(overlay_data)

                                composed_path = os.path.join(target_dir,
                                                             f"{date_formatted}_composed.{media_ext}")
                                if self.compose_video(original_path,
                                                      temp_overlay,
                                                      composed_path):
                                    os.remove(temp_overlay)
                                    self.set_file_date(composed_path, date_obj)
                                else:
                                    if os.path.exists(temp_overlay):
                                        os.remove(temp_overlay)
                            except:
                                pass

                return True

        except Exception:
            return False

    def process_all(self):
        print_color("\n🗜️  Processing ZIP files...", Colors.BLUE)

        zip_files = []
        for root, dirs, files in os.walk(self.output_dir):
            for filename in files:
                if filename.endswith('.zip'):
                    zip_path = os.path.join(root, filename)
                    zip_files.append((zip_path, root, filename))

        total = len(zip_files)

        if total == 0:
            print_color("ℹ️  No ZIP files found", Colors.YELLOW)
            return

        processed_count = 0
        failed_count = 0
        images_count = 0
        videos_count = 0

        with tqdm(total=total, desc="🗜️  Processing ZIPs", unit="zip",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                  colour="cyan") as pbar:

            for zip_path, root, filename in zip_files:
                date_match = (
                        re.search(r'(\d{8}_\d{6})', filename) or
                        re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})',
                                  filename) or
                        re.search(r'(\d{4}-\d{2}-\d{2})', filename) or
                        re.search(r'(\d{8})', filename)
                )

                if date_match:
                    date_formatted = date_match.group(1)

                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            file_list = zip_ref.namelist()
                            is_video = any(
                                f.lower().endswith(('.mp4', '.mov')) for f in
                                file_list)
                            if is_video:
                                videos_count += 1
                            else:
                                images_count += 1

                        if self.process_single_zip(zip_path, root,
                                                   date_formatted):
                            processed_count += 1
                            os.remove(zip_path)
                            pbar.set_postfix_str(
                                f"✓ {processed_count} | ✗ {failed_count} | 🖼️  {images_count} | 🎬 {videos_count}")
                        else:
                            failed_count += 1
                            pbar.set_postfix_str(
                                f"✓ {processed_count} | ✗ {failed_count} | 🖼️  {images_count} | 🎬 {videos_count}")
                    except Exception:
                        failed_count += 1
                        pbar.set_postfix_str(
                            f"✓ {processed_count} | ✗ {failed_count} | 🖼️  {images_count} | 🎬 {videos_count}")
                else:
                    failed_count += 1
                    pbar.set_postfix_str(
                        f"✓ {processed_count} | ✗ {failed_count} | 🖼️  {images_count} | 🎬 {videos_count}")

                pbar.update(1)

        print_color("\n" + "=" * 80, Colors.BLUE)
        print_color("📊 ZIP PROCESSING SUMMARY", Colors.BOLD)
        print_color("=" * 80, Colors.BLUE)
        print_color(f"✓ Successfully processed: {processed_count}/{total}",
                    Colors.GREEN)
        if failed_count > 0:
            print_color(f"✗ Failed: {failed_count}", Colors.RED)
        print_color(f"🖼️  Images: {images_count}", Colors.CYAN)
        print_color(f"🎬 Videos: {videos_count}", Colors.CYAN)
        print_color("=" * 80 + "\n", Colors.BLUE)
