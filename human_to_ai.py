import os
import time
import json
import random
import google.generativeai as genai
from dotenv import load_dotenv

# --- CẤU HÌNH ---
INPUT_FILE = "human-write-data.jsonl"  # File dữ liệu gốc của bạn
OUTPUT_FILE = "ai-generate-data.jsonl" # File kết quả sẽ lưu vào
API_KEY_ENV = "GEMINI_API_KEY"

MODEL_LIST = [
    "models/gemini-2.0-flash-lite",         # Ưu tiên 1: Bản Lite cực nhanh
    "models/gemini-2.0-flash",              # Ưu tiên 2: Bản 2.0 chuẩn
    "models/gemini-flash-latest",           # Ưu tiên 3: Alias chung
    "models/gemini-2.5-flash-lite",         # Ưu tiên 4: Bản Lite đời mới
    "models/gemini-2.0-flash-exp",          # Ưu tiên 5: Bản thử nghiệm
    "models/gemini-flash-lite-latest",      # Ưu tiên 6
    "models/gemini-2.0-pro-exp-02-05",      # Dự phòng cuối cùng (Pro chạy chậm hơn)
]

load_dotenv()
genai.configure(api_key=os.getenv(API_KEY_ENV))

# Biến toàn cục theo dõi vị trí model đang dùng
current_model_index = 0

def get_current_model_name():
    return MODEL_LIST[current_model_index]

def switch_model():
    """Chuyển sang model kế tiếp trong danh sách"""
    global current_model_index
    old_model = MODEL_LIST[current_model_index]
    current_model_index = (current_model_index + 1) % len(MODEL_LIST)
    new_model = MODEL_LIST[current_model_index]
    print(f"\n⚠️ Chuyển Model: {old_model} -> {new_model}")
    print(f"   (Lý do: Model cũ bị lỗi hoặc hết Quota)\n")

PROMPT_STYLES = [
    "Viết lại đoạn văn này theo phong cách báo chí khách quan, dùng từ vựng khác nhưng giữ nguyên sự kiện.",
    "Paraphrase lại nội dung này, thay đổi cấu trúc câu (chủ động/bị động) và sử dụng từ đồng nghĩa.",
    "Tóm lược và viết lại nội dung sao cho gãy gọn, súc tích hơn, loại bỏ các từ dư thừa.",
    "Thay đổi giọng văn để tạo sự tươi mới nhưng tuyệt đối giữ nguyên các số liệu và tên riêng."
]

def generate_rewritten_text_smart(original_text):
    global current_model_index
    
    # Thử tối đa 5 lần (với các model khác nhau) cho 1 dòng dữ liệu
    max_retries = 5 
    
    for attempt in range(max_retries):
        model_name = get_current_model_name()
        
        try:
            # Khởi tạo model
            # Lưu ý: Các model Gemini 2.0/2.5 đều hỗ trợ tốt JSON mode
            model = genai.GenerativeModel(
                model_name,
                generation_config={"response_mime_type": "application/json"}
            )
            
            style = random.choice(PROMPT_STYLES)
            
            prompt = f"""
            Bạn là một trợ lý AI xử lý dữ liệu.
            Nhiệm vụ: {style}
            
            Yêu cầu NGHIÊM NGẶT:
            1. Output phải là JSON hợp lệ: {{ "rewritten_text": "nội dung..." }}
            2. KHÔNG thêm bất kỳ lời dẫn, lời chào, hay giải thích.
            3. Nếu văn bản quá ngắn hoặc vô nghĩa, trả về chuỗi rỗng.

            Văn bản gốc:
            "{original_text}"
            """
            
            response = model.generate_content(prompt)
            result = json.loads(response.text)
            return result.get("rewritten_text", None)

        except Exception as e:
            error_msg = str(e)
            
            # Xử lý các loại lỗi để đổi model
            if "429" in error_msg or "Quota exceeded" in error_msg:
                print(f"❌ {model_name} hết Quota (429).")
                switch_model()
                time.sleep(2) # Nghỉ xíu để chuyển đổi
                continue
            
            elif "404" in error_msg or "not found" in error_msg:
                print(f"❌ {model_name} không tìm thấy/lỗi tên.")
                switch_model()
                continue
            
            elif "500" in error_msg or "503" in error_msg: # Lỗi Server Google
                print(f"⚠️ Google Server Error ({model_name}). Thử lại...")
                time.sleep(5)
                continue
                
            else:
                # Lỗi không phải do mạng/quota (ví dụ JSON lỗi) thì bỏ qua dòng này
                print(f"⚠️ Lỗi xử lý ({model_name}): {e}")
                return None
    
    return None

def main():
    # Tạo file output nếu chưa có
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE, 'w', encoding='utf-8').close()

    # Đếm số dòng đã làm để Resume
    processed_count = 0
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        processed_count = sum(1 for _ in f)

    # Đếm tổng số dòng input
    total_lines = 0
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file {INPUT_FILE}")
        return

    print(f"🚀 Bắt đầu! Đã có {processed_count} dòng. Tổng input: {total_lines}")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as fin, \
         open(OUTPUT_FILE, 'a', encoding='utf-8') as fout:
        
        for i, line in enumerate(fin):
            # Bỏ qua các dòng đã làm
            if i < processed_count:
                continue
            
            try:
                data = json.loads(line.strip())
            except:
                continue

            # In ra màn hình trạng thái
            current_model = get_current_model_name().replace("models/", "")
            print(f"⏳ {i+1}/{total_lines} | Model: {current_model}")
            
            original_text = data.get("text", "")
            
            # Bỏ qua text quá ngắn (rác)
            if len(original_text) < 30: 
                print("   -> Text quá ngắn, skip.")
                continue

            new_text = generate_rewritten_text_smart(original_text)
            
            if new_text:
                new_record = {
                    "text": new_text,
                    "label": 1, # Label 1 cho AI
                    "meta": data.get("meta", {})
                }
                # Cập nhật meta
                new_record["meta"]["type"] = "ai_generated_rewrite"
                new_record["meta"]["model_used"] = current_model
                
                fout.write(json.dumps(new_record, ensure_ascii=False) + "\n")
                fout.flush() # Lưu ngay
            else:
                print("   ⚠️ Failed.")

            # Sleep nhẹ (3s) để giữ nhịp, nếu dùng Lite có thể giảm xuống 2s
            time.sleep(3) 

    print("\n🎉 HOÀN THÀNH TOÀN BỘ DATASET!")

if __name__ == "__main__":
    main()