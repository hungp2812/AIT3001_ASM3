import os
import json
import glob
from tqdm import tqdm
from pyvi import ViTokenizer
import re

# --- CẤU HÌNH (SỬA Ở ĐÂY CHO MỖI LẦN CHẠY) ---

# 1. Đường dẫn đến folder kết quả của lần chạy hiện tại
# Ví dụ: "result_vnexpress", "result_dantri"...
DATA_ROOT = "result_vnexpress"
# DATA_ROOT = "result_vietnamnet"  

# 2. Tên nguồn báo (để lưu vào meta data phân biệt)
# Ví dụ: "vnexpress", "dantri", "tuoitre"
SOURCE_NAME = "vnexpress" 
# SOURCE_NAME = "vietnamnet"

# 3. File đầu ra chung (Không sửa tên này để nó nối đuôi vào 1 file duy nhất)
OUTPUT_FILE = "combined_phobert_data.jsonl" 

# 4. Độ dài tối thiểu
MIN_LENGTH = 50       

# -----------------------------------------------

def clean_and_segment(text):
    """Làm sạch và tách từ cho PhoBERT"""
    if not text: return None
    text = re.sub(r'\s+', ' ', text).strip()
    # return ViTokenizer.tokenize(text)
    return text # Không tách từ lúc này để process sau khi thu thập xong

def load_url_map(category):
    """Đọc file map URL nếu có"""
    url_file_path = os.path.join(DATA_ROOT, "urls", f"{category}.txt")
    urls = []
    if os.path.exists(url_file_path):
        with open(url_file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f.readlines()]
    return urls

def process_append():
    # Kiểm tra xem folder dữ liệu có tồn tại không
    if not os.path.exists(DATA_ROOT):
        print(f"[LỖI] Không tìm thấy thư mục: {DATA_ROOT}")
        return

    print(f"\n>>> BẮT ĐẦU XỬ LÝ NGUỒN: {SOURCE_NAME}")
    print(f">>> Đọc từ folder: {DATA_ROOT}")
    print(f">>> Ghi nối vào file: {OUTPUT_FILE}")

    # CHẾ ĐỘ 'a' (APPEND) LÀ CHÌA KHÓA Ở ĐÂY
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
        
        categories = [
            d for d in os.listdir(DATA_ROOT) 
            if os.path.isdir(os.path.join(DATA_ROOT, d)) and d != 'urls'
        ]
        
        total_added = 0

        for category in categories:
            # Load map URL
            url_list = load_url_map(category)
            
            # Lấy list file
            files = glob.glob(os.path.join(DATA_ROOT, category, "url_*.txt"))
            
            # Dùng tqdm để hiện thanh tiến trình cho từng category
            desc_text = f"Xử lý {category}"
            for file_path in tqdm(files, desc=desc_text, leave=False):
                try:
                    # Lấy file index để map URL
                    filename = os.path.basename(file_path)
                    try:
                        file_index = int(filename.split('_')[1].split('.')[0])
                    except:
                        file_index = -1

                    # Lấy URL gốc
                    original_url = "unknown"
                    if file_index >= 0 and file_index < len(url_list):
                        original_url = url_list[file_index]

                    # Đọc content
                    with open(file_path, 'r', encoding='utf-8') as f_in:
                        content = f_in.read()

                    if len(content.split()) < MIN_LENGTH:
                        continue

                    # Tách từ
                    segmented_text = clean_and_segment(content)
                    
                    if segmented_text:
                        entry = {
                            "text": segmented_text,
                            "label": 0, # Human Text
                            "meta": {
                                "source": SOURCE_NAME, # Lưu nguồn (vnexpress/dantri...)
                                "category": category,
                                "original_url": original_url,
                                "file_id": filename,
                                "type": "original"
                            }
                        }
                        
                        f_out.write(json.dumps(entry, ensure_ascii=False) + '\n')
                        total_added += 1
                        
                except Exception as e:
                    continue

    print(f"\n>>> [XONG] Đã thêm {total_added} bài từ {SOURCE_NAME} vào file tổng.")

if __name__ == "__main__":
    process_append()