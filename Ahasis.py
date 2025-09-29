import cv2
import numpy as np
from deepface import DeepFace
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from PIL import Image, ImageTk
import threading
import time
import json
from datetime import datetime
import logging
import os

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmotionConfig:
    COLORS = {
        'primary': '#1a1a2e',
        'secondary': '#16213e',
        'accent': '#0f3460',
        'highlight': '#e94560',
        'success': '#00d4aa',
        'warning': '#f39c12',
        'text_light': '#ecf0f1',
        'text_dark': '#2c3e50',
        'background': '#0e1621',
        'card': '#1e2a3a',
        'border': '#34495e'
    }
    EMOTIONS = {
        "happy": {"arabic": "سعيد", "emoji": "😊", "color": "#2ecc71"},
        "sad": {"arabic": "حزين", "emoji": "😢", "color": "#3498db"},
        "angry": {"arabic": "غاضب", "emoji": "😡", "color": "#e74c3c"},
        "fear": {"arabic": "خائف", "emoji": "😨", "color": "#9b59b6"},
        "surprise": {"arabic": "مندهش", "emoji": "😲", "color": "#f39c12"},
        "neutral": {"arabic": "محايد", "emoji": "😐", "color": "#95a5a6"},
        "disgust": {"arabic": "مشمئز", "emoji": "🤢", "color": "#8b4513"}
    }
    CAMERA_SETTINGS = {'width': 640, 'height': 480, 'fps': 30, 'analysis_interval': 0.5}
class CameraSettingsWindow:
    RESOLUTIONS = ["640x480", "720x480", "1280x720"]
    FPS_OPTIONS = [15, 20, 25, 30]
    def __init__(self, parent, camera):
        self.parent = parent
        self.camera = camera
        self.win = tk.Toplevel(parent)
        self.win.title("⚙️ إعدادات الكاميرا")
        self.win.geometry("300x250")

        # هنا نحدد الدقة
        tk.Label(self.win, text="الدقة (Resolution):").pack(pady=(10,0))
        self.res_var = tk.StringVar(value="640x480")
        self.res_combo = ttk.Combobox(self.win, values=self.RESOLUTIONS, state="readonly", textvariable=self.res_var)
        self.res_combo.pack()

        # هنا نحدد عدد الفريمات
        tk.Label(self.win, text="عدد الفريمات (FPS):").pack(pady=(10,0))
        self.fps_var = tk.IntVar(value=30)
        self.fps_combo = ttk.Combobox(self.win, values=self.FPS_OPTIONS, state="readonly", textvariable=self.fps_var)
        self.fps_combo.pack()

        # هنا نحدد تأخير التحليل
        tk.Label(self.win, text="تأخير التحليل (ثواني):").pack(pady=(10,0))
        self.interval_var = tk.DoubleVar(value=EmotionConfig.CAMERA_SETTINGS['analysis_interval'])
        self.interval_slider = ttk.Scale(self.win, from_=0.3, to=2.0, orient='horizontal', variable=self.interval_var)
        self.interval_slider.pack(pady=5, fill='x', padx=20)
        tk.Label(self.win, text="أسرع ←   → أبطأ").pack()
        ttk.Button(self.win, text="تطبيق", command=self.apply).pack(pady=15)
    def apply(self):
        try:
            res = self.res_var.get()
            width, height = map(int, res.split("x"))
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            fps = int(self.fps_var.get())
            self.camera.set(cv2.CAP_PROP_FPS, fps)
            EmotionConfig.CAMERA_SETTINGS['analysis_interval'] = self.interval_var.get()
            messagebox.showinfo("تم", f"تم تحديث إعدادات الكاميرا:\n{width}x{height} @ {fps} FPS\nتأخير التحليل: {self.interval_var.get():.2f} ثانية")
            self.win.destroy()
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تطبيق الإعدادات: {e}")

# هنا نقوم بتحليل المشاعر
class EmotionAnalyzer:
    def analyze_frame(self, frame):
        try:
            small_frame = cv2.resize(frame, (320, 240))
            result = DeepFace.analyze(
                small_frame,
                actions=['emotion'],
                enforce_detection=False,
                detector_backend='opencv',
                silent=True
            )
            if isinstance(result, list):
                result = result[0]
            # هنا نصحح بعض الأخطاء الشائعة في التعرف على المشاعر
            if result['dominant_emotion'] == 'angry' and result['emotion'].get('disgust',0) > 0.01:
                result['dominant_emotion'] = 'disgust'
            return {
                'dominant_emotion': result['dominant_emotion'],
                'emotions': result['emotion'],
                'timestamp': datetime.now(),
                'confidence': max(result['emotion'].values())
            }
        except Exception as e:
            logger.error(f"خطأ في تحليل المشاعر: {e}")
            return {
                'dominant_emotion': 'neutral',
                'emotions': {k: 0 for k in EmotionConfig.EMOTIONS.keys()},
                'timestamp': datetime.now(),
                'confidence': 0
            }
# هنا نقوم بحفظ وتحليل البيانات
class EmotionStatistics:
    def __init__(self):
        self.emotion_history = []
        self.session_start = datetime.now()

    def add_result(self, result):
        self.emotion_history.append(result)
        if len(self.emotion_history) > 1000:
            self.emotion_history = self.emotion_history[-1000:]
    def export_data(self, filename):
        data = {
            'session_start': self.session_start.isoformat(),
            'total_analyses': len(self.emotion_history),
            'history': [
                {'timestamp': r['timestamp'].isoformat(),
                 'dominant_emotion': r['dominant_emotion'],
                 'confidence': r['confidence'],
                 'emotions': r['emotions']}
                for r in self.emotion_history
            ]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# هنا شريط تقدم حديث لكل شعور
class ModernProgressBar:
    def __init__(self, parent, width=250, height=20, color="#2ecc71"):
        self.canvas = tk.Canvas(parent, width=width, height=height,
                                bg=EmotionConfig.COLORS['card'], highlightthickness=0)
        self.width, self.height, self.color = width, height, color
        self.value, self.max_value = 0, 100
        self.bg_rect = self.canvas.create_rectangle(2,2,width-2,height-2,
                                                    fill=EmotionConfig.COLORS['secondary'],
                                                    outline=EmotionConfig.COLORS['border'])
        self.progress_rect = self.canvas.create_rectangle(2,2,2,height-2, fill=color, outline="")
        self.text = self.canvas.create_text(width//2, height//2, text="0%", fill=EmotionConfig.COLORS['text_light'], font=("Arial", 10, "bold"))
    def set_value(self, value):
        self.value = max(0, min(value, self.max_value))
        progress_width = (self.value / self.max_value) * (self.width - 4)
        self.canvas.coords(self.progress_rect, 2,2,2+progress_width,self.height-2)
        self.canvas.itemconfig(self.text, text=f"{int(self.value)}%")
    def pack(self, **kwargs): self.canvas.pack(**kwargs)
    def grid(self, **kwargs): self.canvas.grid(**kwargs)

#هنا الواجهة الرئيسية
class EmotionDetectorPro:
    def __init__(self, root):
        self.root = root
        self.analyzer = EmotionAnalyzer()
        self.statistics = EmotionStatistics()
        self.camera_active = False
        self.recording = False
        self.video_writer = None
        self.current_frame = None
        self.imgtk = None
        self.create_interface()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    def create_interface(self):
        self.root.title("🎭Ahasis")
        self.root.geometry("1400x900")
        self.root.configure(bg=EmotionConfig.COLORS['background'])
        main_frame = tk.Frame(self.root, bg=EmotionConfig.COLORS['background'])
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)

        #هنا حق عرض الفيديو
        video_frame = tk.Frame(main_frame, bg=EmotionConfig.COLORS['card'], bd=2, relief='raised')
        video_frame.pack(side='left', fill='both', expand=True, padx=(0,10))
        tk.Label(video_frame, text="📹 الكاميرا المباشرة", bg=EmotionConfig.COLORS['card'], fg=EmotionConfig.COLORS['text_light'], font=('Arial',14,'bold')).pack(pady=10)
        self.video_label = tk.Label(video_frame, text="📷 اضغط تشغيل الكاميرا", bg=EmotionConfig.COLORS['secondary'], fg=EmotionConfig.COLORS['text_light'], font=('Arial',16))
        self.video_label.pack(expand=True, fill='both', pady=10)
        # وهنا حق عرض النتائج
        results_frame = tk.Frame(main_frame, bg=EmotionConfig.COLORS['card'], bd=2, relief='raised')
        results_frame.pack(side='right', fill='y', padx=(10,0))
        tk.Label(results_frame, text="📊 نتائج المشاعر", font=('Arial',14,'bold'), bg=EmotionConfig.COLORS['card'], fg=EmotionConfig.COLORS['text_light']).pack(pady=10)
        self.current_emotion_label = tk.Label(results_frame, text="😐 محايد", font=('Arial',24,'bold'), bg=EmotionConfig.COLORS['card'], fg=EmotionConfig.COLORS['success'])
        self.current_emotion_label.pack(pady=5)
        self.confidence_label = tk.Label(results_frame, text="الثقة: 0%", font=('Arial',12), bg=EmotionConfig.COLORS['card'], fg=EmotionConfig.COLORS['text_light'])
        self.confidence_label.pack(pady=5)
        self.emotion_bars = {}
        for k,v in EmotionConfig.EMOTIONS.items():
            bar_frame = tk.Frame(results_frame, bg=EmotionConfig.COLORS['card'])
            bar_frame.pack(fill='x', pady=2)
            lbl = tk.Label(bar_frame, text=f"{v['emoji']} {v['arabic']}", font=('Arial',11,'bold'), bg=EmotionConfig.COLORS['card'], fg=v['color'], width=12, anchor='w')
            lbl.pack(side='left')
            bar = ModernProgressBar(bar_frame, width=180, height=15, color=v['color'])
            bar.pack(side='left', padx=5)
            self.emotion_bars[k] = bar
        controls_frame = tk.Frame(results_frame, bg=EmotionConfig.COLORS['card'])
        controls_frame.pack(pady=20)
        ttk.Button(controls_frame, text="▶ تشغيل الكاميرا", command=self.start_camera).pack(pady=5)
        ttk.Button(controls_frame, text="⏹ إيقاف الكاميرا", command=self.stop_camera).pack(pady=5)
        ttk.Button(controls_frame, text="🎥 تسجيل الفيديو", command=self.toggle_recording).pack(pady=5)
        ttk.Button(controls_frame, text="💾 حفظ البيانات", command=self.export_data).pack(pady=5)
        ttk.Button(controls_frame, text="📝 شرح المشروع", command=self.show_project_explanation).pack(pady=5)
        ttk.Button(controls_frame, text="⚙️ إعدادات الكاميرا", command=self.open_camera_settings).pack(pady=5)

    # الكاميرا
    def start_camera(self):
        if not self.camera_active:
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # منع الغمز
            # self.camera = cv2.VideoCapture("http://192.168.1.3:8080/video")
            #self.camera = cv2.VideoCapture("D:/26ajd/infer5-test.avi")
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, EmotionConfig.CAMERA_SETTINGS['width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, EmotionConfig.CAMERA_SETTINGS['height'])
            self.camera_active = True
            self.video_loop()
            self.analysis_loop()
            logger.info("تم تشغيل الكاميرا وتحليل المشاعر")
    def stop_camera(self):
        self.camera_active = False
        if self.camera:
            self.camera.release()
            self.camera = None
        if self.recording:
            self.toggle_recording()
        self.video_label.config(image='', text='📷 اضغط تشغيل الكاميرا')
        logger.info("تم إيقاف الكاميرا")    
    def open_camera_settings(self):
        if not hasattr(self, "camera") or self.camera is None:
            messagebox.showwarning("تنبيه", "شغّل الكاميرا أولاً قبل تعديل الإعدادات.")
            return
        CameraSettingsWindow(self.root, self.camera)
#هنا الكلاس الخاص بعرض الفيديو وتحليل المشاعر
    def video_loop(self):
        if self.camera_active:
            ret, frame = self.camera.read()
            if ret:
                self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(self.current_frame)
                img = img.resize((640,480))
                self.imgtk = ImageTk.PhotoImage(img)
                self.video_label.imgtk = self.imgtk
                self.video_label.config(image=self.imgtk)
                # هنا حق تسجيل الفيديو و عرض النتائج عليه
                if self.recording and self.video_writer:
                    frame_bgr = cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR)
                    if hasattr(self, 'last_result') and self.last_result:
                        dominant = self.last_result['dominant_emotion']
                        emoji = EmotionConfig.EMOTIONS.get(dominant, {'emoji':'','arabic':'محايد'})['emoji']
                        text = f"{emoji} {dominant}"
                        cv2.putText(frame_bgr, text, (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                    self.video_writer.write(frame_bgr)
            self.root.after(int(1000/EmotionConfig.CAMERA_SETTINGS['fps']), self.video_loop)  
    def analysis_loop(self):
        if self.camera_active and self.current_frame is not None:
            result = self.analyzer.analyze_frame(self.current_frame)
            self.statistics.add_result(result)
            self.last_result = result  # هذا عشان في تحديث الفيديو
            self.update_ui(result)
            self.root.after(int(EmotionConfig.CAMERA_SETTINGS['analysis_interval']*1000), self.analysis_loop)

    def update_ui(self, result):
        dominant = result['dominant_emotion']
        if dominant not in EmotionConfig.EMOTIONS:
            dominant = 'neutral'
        emoji = EmotionConfig.EMOTIONS[dominant]['emoji']
        color = EmotionConfig.EMOTIONS[dominant]['color']
        confidence = int(result['confidence'])
        self.current_emotion_label.config(text=f"{emoji} {EmotionConfig.EMOTIONS[dominant]['arabic']}", fg=color)
        self.confidence_label.config(text=f"الثقة: {confidence}%")
        for k,v in result['emotions'].items():
            if k in self.emotion_bars:
                self.emotion_bars[k].set_value(v)

    def toggle_recording(self):
        if not self.recording and self.camera_active:
            filename = filedialog.asksaveasfilename(defaultextension=".avi", filetypes=[("AVI files","*.avi")])
            if filename:
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
                self.recording = True
                messagebox.showinfo("تسجيل الفيديو", f"بدأ التسجيل وحفظ الملف في {filename}")
        elif self.recording:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
            messagebox.showinfo("تسجيل الفيديو", "تم إيقاف التسجيل وحفظ الملف بنجاح")

    # حفظ البيانات
    def export_data(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
        if filename:
            self.statistics.export_data(filename)
            messagebox.showinfo("تم الحفظ", f"تم حفظ البيانات في {filename}")

    # شرح المشروع
    def show_project_explanation(self):
        # نافذة جديدة لعرض الكود وشرحه
        window = tk.Toplevel(self.root)
        window.title("📖 شرح المشروع الكامل")
        window.geometry("1000x700")

        # إنشاء Text widget مع Scrollbar
        text_frame = tk.Frame(window)
        text_frame.pack(expand=True, fill='both')
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        text = tk.Text(text_frame, wrap="none", font=("Courier New", 10), yscrollcommand=scrollbar.set)
        text.pack(expand=True, fill='both')
        scrollbar.config(command=text.yview)

        # قراءة الكود
        code_path = os.path.abspath(__file__)
        with open(code_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # شرح لكل سطر
        explanations = {
            "import cv2": "OpenCV: لالتقاط الفيديو ومعالجة الصور والفيديو.",
            "import numpy": "NumPy: للتعامل مع المصفوفات وتحويل الصور.",
            "from deepface": "DeepFace: لتحليل التعابير الوجهية واكتشاف المشاعر.",
            "import tkinter": "Tkinter: لإنشاء واجهة المستخدم الرسومية (GUI).",
            "from tkinter import messagebox": "لإظهار رسائل منبثقة للمستخدم.",
            "from tkinter import ttk": "عناصر واجهة حديثة مثل أزرار وشريط التقدم.",
            "from tkinter import filedialog": "لإظهار مربعات حوار اختيار الملفات.",
            "from PIL": "Pillow: لتحويل الصور بين OpenCV وTkinter.",
            "import threading": "لتشغيل عمليات الخلفية بدون تجميد الواجهة.",
            "import time": "للتعامل مع تأخيرات زمنية بين الإطارات.",
            "import json": "لحفظ البيانات في ملفات JSON.",
            "from datetime import datetime": "لإضافة وقت لكل تحليل مشاعر.",
            "import logging": "لتسجيل الأخطاء والمعلومات أثناء التشغيل.",
            "import os": "للتعامل مع ملفات النظام وقراءة ملف الكود نفسه.",
            "class EmotionConfig": "إعدادات المشروع: الألوان، المشاعر، إعدادات الكاميرا.",
            "class EmotionAnalyzer": "تحليل الإطار للكشف عن المشاعر وتصحيح الأخطاء.",
            "class EmotionStatistics": "تخزين نتائج التحليل وحفظها في JSON.",
            "class ModernProgressBar": "شريط تقدم مرئي لكل شعور.",
            "class EmotionDetectorPro": "الواجهة الرئيسية وتشغيل الكاميرا والتحليل وعرض النتائج.",
            "def start_camera": "تشغيل الكاميرا وبدء التحديث المستمر للفيديو والتحليل.",
            "def stop_camera": "إيقاف الكاميرا وتحرير الموارد وإيقاف التسجيل.",
            "def video_loop": "عرض الفيديو في Tkinter وتسجيل الفيديو إذا مفعل.",
            "def analysis_loop": "تحليل المشاعر لكل إطار وتحديث واجهة النتائج.",
            "def update_ui": "تحديث واجهة النتائج مع المشاعر والثقة وأشرطة التقدم.",
            "def toggle_recording": "بدء أو إيقاف تسجيل الفيديو وحفظه.",
            "def export_data": "حفظ بيانات التحليل في ملف JSON.",
            "def on_closing": "إيقاف الكاميرا والتسجيل عند إغلاق التطبيق."
        }
        for i, line in enumerate(lines, start=1):
            explanation = ""
            for key in explanations:
                if key in line:
                    explanation = explanations[key]
                    break
            text.insert("end", f"{i:03d}: {line.rstrip()}\n")
            if explanation:
                text.insert("end", f"     ➜ {explanation}\n", "explanation")

        text.config(state="disabled") 
    def on_closing(self):
        self.stop_camera()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = EmotionDetectorPro(root)
    root.mainloop()

