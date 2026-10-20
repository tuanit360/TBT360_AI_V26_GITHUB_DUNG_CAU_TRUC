"""Minimal Windows-native UI for verified stage-1 deep-learning workflow."""
import csv
import json
import queue
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .engine import run_training, predict_image


class App:
    def __init__(self, root):
        self.root = root
        root.title('TBT360 AI V26 · Deep Learning')
        root.geometry('1030x720')
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.dataset = tk.StringVar()
        self.output = tk.StringVar(value=str(Path.home() / 'TBT360_AI_Models'))
        self.epochs = tk.IntVar(value=3)
        self.gpu = tk.BooleanVar(value=False)
        self.losses = []
        self.accuracies = []
        top = ttk.Frame(root, padding=15)
        top.pack(fill='x')
        ttk.Label(top, text='TBT360 AI V26 · Huấn luyện ảnh bằng MobileNetV3', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(top, text='Giai đoạn 1: Phân loại ảnh có nhãn · Giai đoạn 2/3: chưa triển khai AI đọc 2D/BIM 3D').pack(anchor='w')
        for title, var, command in [('Thư mục dữ liệu', self.dataset, self.pick_dataset), ('Nơi lưu mô hình', self.output, self.pick_output)]:
            line = ttk.Frame(top)
            line.pack(fill='x', pady=4)
            ttk.Label(line, text=title, width=20).pack(side='left')
            ttk.Entry(line, textvariable=var).pack(side='left', fill='x', expand=True)
            ttk.Button(line, text='Chọn', command=command).pack(side='left', padx=6)
        controls = ttk.Frame(top)
        controls.pack(fill='x', pady=8)
        ttk.Label(controls, text='Epoch').pack(side='left')
        ttk.Spinbox(controls, from_=1, to=200, width=6, textvariable=self.epochs).pack(side='left', padx=8)
        ttk.Checkbutton(controls, text='Sử dụng CUDA nếu có', variable=self.gpu).pack(side='left')
        self.start_button = ttk.Button(controls, text='BẮT ĐẦU HỌC SÂU', command=self.train)
        self.start_button.pack(side='left', padx=12)
        ttk.Button(controls, text='Dừng sau batch hiện tại', command=self.stop.set).pack(side='left')
        ttk.Button(controls, text='Kiểm tra ảnh mới', command=self.test_image).pack(side='left', padx=6)
        self.progress = tk.StringVar(value='Sẵn sàng · Chưa huấn luyện')
        ttk.Label(top, textvariable=self.progress).pack(anchor='w')
        self.chart = tk.Canvas(root, bg='#101a2c', height=240, highlightthickness=0)
        self.chart.pack(fill='x', padx=15, pady=8)
        self.console = tk.Text(root, height=15, bg='#101a2c', fg='#bfe6ed', font=('Consolas', 10))
        self.console.pack(fill='both', expand=True, padx=15, pady=10)
        self.write('Hướng dẫn: dataset/truong_hoc/anh01.jpg và dataset/van_phong/anh01.jpg (mỗi lớp ít nhất 3 ảnh).')
        self.draw()
        self.root.after(100, self.poll)

    def pick_dataset(self):
        p = filedialog.askdirectory(title='Chọn thư mục chứa các thư mục lớp ảnh')
        if p:
            self.dataset.set(p)

    def pick_output(self):
        p = filedialog.askdirectory(title='Chọn nơi lưu model/log')
        if p:
            self.output.set(p)

    def write(self, msg):
        self.console.insert('end', msg + '\n')
        self.console.see('end')

    def train(self):
        if not self.dataset.get():
            messagebox.showwarning('Thiếu dữ liệu', 'Hãy chọn thư mục ảnh đã phân loại trước.')
            return
        self.losses.clear()
        self.accuracies.clear()
        self.stop.clear()
        self.start_button.configure(state='disabled')
        dataset, output, epochs, gpu = self.dataset.get(), self.output.get(), self.epochs.get(), self.gpu.get()
        self.write(f'Bắt đầu: {dataset}; {epochs} epochs; CUDA yêu cầu: {gpu}')

        def job():
            try:
                result = run_training(dataset, output, epochs=epochs, use_gpu=gpu, on_event=lambda event: self.events.put(('epoch', event)), stop=self.stop)
                self.events.put(('done', result))
            except Exception:
                self.events.put(('error', traceback.format_exc()))
        threading.Thread(target=job, daemon=True).start()

    def test_image(self):
        ck = Path(self.output.get()) / 'best.pt'
        if not ck.is_file():
            messagebox.showwarning('Chưa có model', 'Hãy huấn luyện hoặc chọn thư mục chứa best.pt')
            return
        image_path = filedialog.askopenfilename(filetypes=[('Ảnh', '*.jpg *.jpeg *.png *.webp *.bmp')])
        if image_path:
            try:
                result = predict_image(ck, image_path)
                self.write('Dự đoán: ' + json.dumps(result, ensure_ascii=False))
                messagebox.showinfo('Kết quả', '\n'.join(f"{x['label']}: {x['probability']:.1%}" for x in result))
            except Exception as e:
                messagebox.showerror('Không đọc được ảnh', str(e))

    def poll(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'epoch':
                self.losses.append(float(payload['loss']))
                self.accuracies.append(float(payload['accuracy']))
                self.progress.set(f"Epoch {payload['epoch']} · Loss {payload['loss']} · Accuracy {payload['accuracy']:.1%} · {payload['samples_per_second']} ảnh/s · {payload['device']}")
                self.write(json.dumps(payload, ensure_ascii=False))
                self.draw()
            elif kind == 'done':
                self.start_button.configure(state='normal')
                self.write('Đã kết thúc. File kết quả tại: ' + self.output.get())
                self.write(json.dumps(payload, ensure_ascii=False))
            else:
                self.start_button.configure(state='normal')
                self.progress.set('Có lỗi - xem log bên dưới')
                self.write(payload)
        self.root.after(100, self.poll)

    def draw(self):
        c = self.chart
        c.delete('all')
        width = max(c.winfo_width(), 950)
        height = 240
        c.create_text(15, 16, text='Loss (cam) / Validation Accuracy (xanh) · Theo epoch', fill='white', anchor='w')
        for i in range(5):
            y = 40 + i * 42
            c.create_line(30, y, width-30, y, fill='#294057')
        for values, color in [(self.losses, '#f5ab56'), (self.accuracies, '#68d4ed')]:
            if not values:
                continue
            m = max(1, max(values))
            pts = []
            for i, value in enumerate(values):
                x = 40 + i * (width-80) / max(1, len(values)-1)
                y = 220 - value/m * 175
                pts.extend((x, y))
                c.create_oval(x-3, y-3, x+3, y+3, fill=color, outline=color)
            if len(pts) > 2:
                c.create_line(*pts, fill=color, width=2)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
