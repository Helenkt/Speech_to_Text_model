import json
import os
import time
from typing import List, Literal
from pydantic import BaseModel, Field
from openai import OpenAI

# ==========================================
# 1. CẤU HÌNH KẾT NỐI LOCAL LLM
# ==========================================
# Nếu dùng Ollama: base_url="http://localhost:11434/v1", model="qwen2.5:7b-instruct"
# Nếu dùng vLLM: base_url="http://localhost:8000/v1", model="meta-llama/Llama-3.1-8B-Instruct"

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Key tượng trưng cho local endpoint
)
MODEL_NAME = "qwen2.5:7b-instruct"
OUTPUT_FILE = "question_bank.json"

# ==========================================
# 2. SCHEMA ĐỊNH DẠNG PYDANTIC
# ==========================================
class QuestionItem(BaseModel):
    id: str = Field(description="Unique ID của câu hỏi, ví dụ: Q_DB_VI_E001")
    language: Literal["vi", "en"]
    subject: str
    topic: str
    competency: str = Field(description="Năng lực đo lường cụ thể của câu hỏi")
    difficulty: Literal["Easy", "Medium", "Hard"]
    question: str = Field(description="Nội dung câu hỏi phỏng vấn technical")
    reference_answer: str = Field(description="Câu trả lời chuẩn mực, đầy đủ kiến thức")
    key_points: List[str] = Field(description="Danh sách 3-4 ý chính bắt buộc phải có để chấm điểm")

class QuestionBatchResponse(BaseModel):
    questions: List[QuestionItem]

# ==========================================
# 3. DANH MỤC CHỦ ĐỀ VÀ PHÂN RÃ NỘI DUNG
# ==========================================
CURRICULUM = [
    {
        "subject_code": "DB1",
        "subject_name": "1_Các hệ cơ sở dữ liệu",
        "language": "vi",
        "subtopics": [
            "Mô hình dữ liệu quan hệ, quan hệ và bộ dữ liệu",
            "Đại số quan hệ: Phép chọn, chiếu, kết nối, tích đề-các",
            "Toàn vẹn dữ liệu: Khóa chính, khóa ngoại, ràng buộc miền giá trị",
            "Ngôn ngữ SQL: DDL, DML, Aggregation, Subqueries",
            "Các dạng chuẩn 1NF, 2NF, 3NF và phụ thuộc hàm cơ bản"
        ]
    },
    {
        "subject_code": "OOP1",
        "subject_name": "1_Lập trình hướng đối tượng",
        "language": "vi",
        "subtopics": [
            "Lớp (Class), Đối tượng (Object), Khởi tạo và Hủy",
            "Tính đóng gói (Encapsulation) và Access Modifiers",
            "Tính kế thừa (Inheritance): Đơn kế thừa, đa kế thừa, vấn đề Diamond",
            "Tính đa hình (Polymorphism): Overloading vs Overriding",
            "Tính trừu tượng (Abstraction): Abstract Class vs Interface"
        ]
    },
    {
        "subject_code": "DSA",
        "subject_name": "Cấu trúc cơ sở dữ liệu và giải thuật",
        "language": "vi",
        "subtopics": [
            "Độ phức tạp thuật toán: Big-O, Time vs Space Complexity",
            "Mảng động, Danh sách liên kết đơn/đôi (Linked Lists)",
            "Ngăn xếp (Stack), Hàng đợi (Queue), Hàng đợi ưu tiên (Priority Queue)",
            "Thuật toán sắp xếp & tìm kiếm: QuickSort, MergeSort, Binary Search",
            "Cây nhị phân tìm kiếm (BST), Cây cân bằng (AVL, Red-Black Tree)",
            "Đồ thị: Biểu diễn đồ thị, Duyệt BFS và DFS, Dijkstra"
        ]
    }
]

DIFFICULTIES = ["Easy", "Medium", "Hard"]
TARGET_PER_LEVEL = 50
BATCH_SIZE = 10  # Mỗi lượt prompt sinh 10 câu để đảm bảo tốc độ và tránh timeout

# ==========================================
# 4. HÀM GỌI API & SINH DỮ LIỆU
# ==========================================
def fetch_batch_from_llm(subject: dict, difficulty: str, current_count: int, num_needed: int) -> List[dict]:
    """Gọi LLM với Structured Output để sinh 1 batch câu hỏi."""
    subtopics_str = ", ".join(subject["subtopics"])
    
    system_prompt = (
        "Bạn là một chuyên gia khảo thí ngành Công nghệ Thông tin tại trường đại học. "
        "Nhiệm vụ của bạn là tạo ngân hàng câu hỏi vấn đáp chuyên môn chuẩn xác cao. "
        "Bắt buộc trả về đúng định dạng JSON Schema được yêu cầu."
    )
    
    user_prompt = f"""Hãy sinh đúng {num_needed} câu hỏi phỏng vấn technical với tiêu chuẩn:
- Môn học: {subject['subject_name']}
- Ngôn ngữ: {subject['language']}
- Cấp độ: {difficulty}
- Các chủ đề con cần phân bổ đều: {subtopics_str}
- Đảm bảo các câu hỏi mang tính phân loại cao, không trùng lặp ý tưởng với nhau.
- Reference answer phải mang tính học thuật chính xác.
- Key points phải bóc tách 3-4 ý cốt lõi ngắn gọn để Small LLM sau này dùng làm rubric chấm điểm.
- ID bắt đầu tính từ STT: {current_count + 1}
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Sử dụng parse để tự động validate schema qua Pydantic
            completion = client.beta.chat.completions.parse(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=QuestionBatchResponse,
                temperature=0.7,
            )
            
            parsed: QuestionBatchResponse = completion.choices[0].message.parsed
            results = []
            for idx, q in enumerate(parsed.questions):
                # Chuẩn hóa lại ID chính xác theo format
                q_dict = q.model_dump()
                q_dict["id"] = f"Q_{subject['subject_code']}_{difficulty[0]}_{current_count + idx + 1:03d}"
                q_dict["difficulty"] = difficulty
                q_dict["subject"] = subject["subject_name"]
                q_dict["language"] = subject["language"]
                results.append(q_dict)
            return results

        except Exception as e:
            print(f"  [Lỗi lần {attempt+1}/{max_retries}]: {e}. Thử lại sau 3 giây...")
            time.sleep(3)
            
    return []

# ==========================================
# 5. VÒNG LẶP ĐIỀU PHỐI (ORCHESTRATOR)
# ==========================================
def main():
    # Đọc dữ liệu cũ nếu có để hỗ trợ chạy tiếp tục (checkpoint)
    all_questions = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            try:
                all_questions = json.load(f)
                print(f"Tìm thấy {len(all_questions)} câu hỏi đã lưu từ trước.")
            except json.JSONDecodeError:
                all_questions = []

    for subject in CURRICULUM:
        print(f"\n==================================================")
        print(f"BẮT ĐẦU MÔN: {subject['subject_name']} ({subject['language'].upper()})")
        print(f"==================================================")
        
        for diff in DIFFICULTIES:
            # Đếm số câu hiện có của môn và cấp độ này
            existing = [
                q for q in all_questions 
                if q["subject"] == subject["subject_name"] and q["difficulty"] == diff
            ]
            current_count = len(existing)
            print(f"\n--> Cấp độ: {diff} (Đã có: {current_count}/{TARGET_PER_LEVEL})")

            while current_count < TARGET_PER_LEVEL:
                needed = min(BATCH_SIZE, TARGET_PER_LEVEL - current_count)
                print(f"    Đang sinh {needed} câu tiếp theo...")
                
                batch = fetch_batch_from_llm(subject, diff, current_count, needed)
                if not batch:
                    print("    Bỏ qua batch do gặp lỗi liên tục.")
                    break
                
                all_questions.extend(batch)
                current_count += len(batch)

                # Lưu ngay sau mỗi batch để tránh mất dữ liệu nếu ngắt giữa chừng
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_questions, f, ensure_ascii=False, indent=2)

                print(f"    -> Đã cập nhật tổng số: {current_count}/{TARGET_PER_LEVEL}")
                time.sleep(0.5)

    print(f"\n[Hoàn tất!] Toàn bộ ngân hàng câu hỏi đã được lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()