import json
from txt_input import load_txt
import queue
import threading
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import tkinter as tk
from tkinter import filedialog as fd, messagebox as msg, ttk
from rubric_generator_sdk import RubricGenerator

HOME = Path(__file__).resolve().parent
def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def calls(check):
    rows = []
    for c in check.get("calls", []):
        t = c.get("terminal") or {}
        def sec(k):
            return round(t[k]/1e9, 2) if isinstance(t.get(k), (int,float)) else None
        rows.append(dict(stage=c.get("stage"), status=c.get("status"), total_s=c.get("elapsed_seconds"),
                         load_s=sec("load_duration"), prompt_s=sec("prompt_eval_duration"),
                         generate_s=sec("eval_duration"), tokens=t.get("eval_count"), error=c.get("error")))
    return rows

def run(data, events):
    base = HOME / "runtime" / (datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8])
    report = dict(mode="SDK_V15_fresh", input=data, status="ERROR", stages=[])
    start = time.perf_counter()
    try:
        base.mkdir(parents=True)
        result = RubricGenerator(work_dir=base / "runtime").generate_input(data, progress=lambda s:events.put(("progress",s)))
        report.update(wall_s=round(time.perf_counter()-start,2),status=result["status"], sdk_result=result,
                      error=result.get("error"),rubric=result.get("rubric"))
        path = (result.get("artifacts") or {}).get("checkpoint")
        if path and Path(path).is_file():
            report["checkpoint"]=read(path)
            report["stages"]=calls(report["checkpoint"])
    except Exception as e:
        report["error"]=str(e)
        report.setdefault("wall_s",round(time.perf_counter()-start,2))
    try:
        write(base / "speed_report.json", report)
    except OSError as e:
        report["save_error"]=str(e)
    events.put(("done",report))

def main():
    root=tk.Tk()
    root.title("Rubric V15 | Đo tốc độ")
    root.geometry("890x475")
    box=ttk.Frame(root,padding=16);box.pack(fill="both",expand=True)
    value=tk.StringVar(value="Chưa chọn tệp.")
    status=tk.StringVar(value="Sẵn sàng.")
    progress=tk.StringVar(value="Mỗi lần đo dùng dữ liệu chạy mới. Model đang ở trong RAM có thể làm lượt sau nhanh hơn.")
    data=None; report=None; running=False; start=0; events=queue.Queue()
    ttk.Label(box,text="Tạo rubric từ câu hỏi và đáp án chuẩn",font=("Segoe UI",16,"bold")).pack(anchor="w")
    bar=ttk.Frame(box);bar.pack(fill="x",pady=10)
    def show(obj):
        nonlocal report
        report=obj; table.delete(*table.get_children())
        for r in obj["stages"]:
            table.insert("", "end",values=[r.get(k) if r.get(k) is not None else "–" for k in keys])
        elapsed=obj.get("wall_s")
        status.set(str(obj["status"])+(f"   |   Tổng: {elapsed} giây" if elapsed is not None else "   |   Log cũ: xem thời gian từng lượt"))
        err=obj.get("error")
        if isinstance(err,dict): err=err.get("message") or str(err)
        progress.set(str(obj.get("save_error") or err or "Hoàn tất. Bạn có thể lưu kết quả."))
        save.state(["!disabled"])
        rub.state(["!disabled"] if obj.get("rubric") else ["disabled"])
    def choose():
        nonlocal data,report
        path=fd.askopenfilename(initialdir=str(HOME),filetypes=[("Câu hỏi hoặc kết quả", "*.txt *.json"), ("Văn bản","*.txt"), ("JSON","*.json")])
        if not path:return
        try:
            obj=load_txt(path) if Path(path).suffix.lower()==".txt" else read(path)
            if isinstance(obj,dict) and isinstance(obj.get("calls"),list) and "status" in obj:
                show(dict(mode="imported_checkpoint",status=obj["status"],error=obj.get("error"),stages=calls(obj),checkpoint=obj,rubric=obj.get("rubric")))
                data=None; go.state(["disabled"])
            else:
                if not isinstance(obj,dict) or not all(isinstance(obj.get(k),str) and obj[k].strip() for k in ("question","reference_answer")):
                    raise ValueError("Chọn file câu hỏi có question và reference_answer, hoặc generation_result.json.")
                data=obj;report=None;table.delete(*table.get_children());go.state(["!disabled"]);save.state(["disabled"]);rub.state(["disabled"])
                status.set("Sẵn sàng đo."); progress.set(obj["question"][:250])
            value.set(path)
        except Exception as e:msg.showerror("Không mở được tệp",str(e))
    def begin():
        nonlocal running,start
        if running or data is None:return
        running=True;start=time.perf_counter();progress.set("Đang kết nối SDK và Ollama…")
        for b in (pick,go,save,rub):b.state(["disabled"])
        table.delete(*table.get_children())
        threading.Thread(target=run,args=(data,events),daemon=True).start()
    def export(only):
        p=fd.asksaveasfilename(defaultextension=".json",initialfile="rubric.json" if only else "speed_report.json",filetypes=[("JSON","*.json")])
        if p:
            try:write(p,report["rubric"] if only else report)
            except OSError as e:msg.showerror("Không lưu được",str(e))
    pick=ttk.Button(bar,text="1. Mở TXT / JSON",command=choose)
    go=ttk.Button(bar,text="2. Tạo rubric",command=begin)
    save=ttk.Button(bar,text="Lưu báo cáo JSON",command=lambda:export(False))
    rub=ttk.Button(bar,text="Lưu rubric JSON",command=lambda:export(True))
    for b in (pick,go,save,rub):b.pack(side="left",padx=3)
    for b in (go,save,rub):b.state(["disabled"])
    for var in (value,status,progress):ttk.Label(box,textvariable=var,wraplength=830).pack(anchor="w",pady=3)
    keys=("stage","status","total_s","load_s","prompt_s","generate_s","tokens")
    table=ttk.Treeview(box,columns=keys,show="headings",height=8)
    for k,title,w in zip(keys,("Bước","Trạng thái","Tổng (s)","Nạp (s)","Đọc (s)","Sinh (s)","Token ra"),(160,120,82,82,82,82,72)):
        table.heading(k,text=title);table.column(k,width=w)
    table.pack(fill="both",expand=True,pady=10)
    def poll():
        nonlocal running
        while not events.empty():
            typ,obj=events.get()
            if typ=="progress":progress.set(str(obj))
            else:
                running=False;pick.state(["!disabled"]);go.state(["!disabled"]);show(obj)
        if running:status.set(f"Đang chạy: {time.perf_counter()-start:.0f} giây")
        root.after(200,poll)
    root.protocol("WM_DELETE_WINDOW",lambda:msg.showinfo("Đang đo","Hãy chờ lượt đo kết thúc.") if running else root.destroy())
    poll();root.mainloop()
if __name__=="__main__":main()
