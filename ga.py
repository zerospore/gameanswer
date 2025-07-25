import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import json

# ====== Data Model ======
class Answer:
    def __init__(self, text, next_id=None):
        self.text = text
        self.next_id = next_id

    def to_dict(self):
        return {'text': self.text, 'next_id': self.next_id}

    @staticmethod
    def from_dict(data):
        return Answer(data['text'], data['next_id'])

class Scene:
    def __init__(self, scene_id, question):
        self.id = scene_id
        self.question = question
        self.answers = []

    def add_answer(self, text, next_id=None):
        self.answers.append(Answer(text, next_id))

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answers': [a.to_dict() for a in self.answers]
        }

    @staticmethod
    def from_dict(data):
        scene = Scene(data['id'], data['question'])
        scene.answers = [Answer.from_dict(a) for a in data['answers']]
        return scene

# ====== Dialog Editor ======
class DialogEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("GameAnswer — Dialog Editor")

        self.scenes = {}
        self.current_id = None

        # Scene list on the left
        self.scene_list = tk.Listbox(master, width=20)
        self.scene_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        self.scene_list.bind("<<ListboxSelect>>", self.select_scene)

        # Right pane
        right = tk.Frame(master)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(right, text="Scene Text (Question):").pack(anchor="w")
        self.question_entry = tk.Entry(right, width=60)
        self.question_entry.pack(fill=tk.X, padx=5)

        tk.Label(right, text="Answers:").pack(anchor="w", pady=(10, 0))
        self.answer_list = tk.Listbox(right)
        self.answer_list.pack(fill=tk.BOTH, expand=True, padx=5)

        btn_frame = tk.Frame(right)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Add Scene", command=self.add_scene).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Add Answer", command=self.add_answer).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Save", command=self.save).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Load", command=self.load).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="Run", command=self.run_game).grid(row=2, column=0, columnspan=2, pady=10)

    def add_scene(self):
        scene_id = simpledialog.askstring("Scene ID", "Enter a unique scene ID:")
        if not scene_id:
            return
        if scene_id in self.scenes:
            messagebox.showerror("Error", "Scene with this ID already exists!")
            return
        scene = Scene(scene_id, "New question")
        self.scenes[scene_id] = scene
        self.scene_list.insert(tk.END, scene_id)

    def select_scene(self, event):
        sel = self.scene_list.curselection()
        if not sel:
            return
        scene_id = self.scene_list.get(sel[0])
        self.current_id = scene_id
        scene = self.scenes[scene_id]
        self.question_entry.delete(0, tk.END)
        self.question_entry.insert(0, scene.question)
        self.refresh_answers()

    def refresh_answers(self):
        self.answer_list.delete(0, tk.END)
        if self.current_id:
            for a in self.scenes[self.current_id].answers:
                self.answer_list.insert(tk.END, f"{a.text} → {a.next_id}")

    def add_answer(self):
        if not self.current_id:
            messagebox.showerror("Error", "Please select a scene first!")
            return
        text = simpledialog.askstring("Answer Text", "Enter the answer text:")
        if text is None or text.strip() == "":
            return
        next_id = simpledialog.askstring("Next Scene ID", "Enter the scene ID this answer leads to (leave blank for ending):")
        if next_id == "":
            next_id = None
        self.scenes[self.current_id].add_answer(text, next_id)
        self.refresh_answers()

    def save(self):
        if self.current_id:
            self.scenes[self.current_id].question = self.question_entry.get()

        data = {sid: scene.to_dict() for sid, scene in self.scenes.items()}
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", "Dialogs saved successfully!")

    def load(self):
        file = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.scenes.clear()
            self.scene_list.delete(0, tk.END)
            for sid, sdata in data.items():
                scene = Scene.from_dict(sdata)
                self.scenes[sid] = scene
                self.scene_list.insert(tk.END, sid)
            messagebox.showinfo("Loaded", "Dialogs loaded successfully!")

    def run_game(self):
        if not self.scenes:
            messagebox.showerror("Error", "No scenes to run!")
            return
        start = simpledialog.askstring("Start Scene", "Enter the ID of the starting scene:")
        if start not in self.scenes:
            messagebox.showerror("Error", "No such scene!")
            return
        GamePlayer(self.master, self.scenes, start)

# ====== Dialog Player ======
class GamePlayer:
    def __init__(self, parent, scenes, start_id):
        self.win = tk.Toplevel(parent)
        self.win.title("GameAnswer — Dialog Player")
        self.win.geometry("500x300")

        self.label = tk.Label(self.win, text="", wraplength=480, font=("Arial", 14))
        self.label.pack(pady=20)

        self.btns_frame = tk.Frame(self.win)
        self.btns_frame.pack(fill=tk.BOTH, expand=True)

        self.scenes = scenes
        self.current = None
        self.load_scene(start_id)

    def load_scene(self, scene_id):
        self.current = self.scenes.get(scene_id)
        if not self.current:
            self.label.config(text="End of dialog.")
            for w in self.btns_frame.winfo_children():
                w.destroy()
            return
        self.label.config(text=self.current.question)
        for w in self.btns_frame.winfo_children():
            w.destroy()
        if not self.current.answers:
            end_label = tk.Label(self.btns_frame, text="(Dialog ended)", font=("Arial", 12, "italic"))
            end_label.pack()
            return
        for a in self.current.answers:
            btn = tk.Button(self.btns_frame, text=a.text, font=("Arial", 12),
                            command=lambda next_id=a.next_id: self.load_scene(next_id))
            btn.pack(fill=tk.X, pady=2, padx=10)

# ====== Run App ======
if __name__ == "__main__":
    root = tk.Tk()
    app = DialogEditor(root)
    root.geometry("700x400")
    try:
        root.iconbitmap("icon.ico")  # Optional
    except Exception:
        pass
    root.mainloop()
