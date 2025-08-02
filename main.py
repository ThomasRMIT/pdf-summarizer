
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from ollama import chat
from ollama import ChatResponse
import fitz  # PyMuPDF
from docx import Document
import os

class GPTChatUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GPT Interface")
        self.root.geometry("800x650")

        self.model_var = tk.StringVar(value="gemma3:4b")
        self.messages = []

        self.create_widgets()

    def create_widgets(self):
        # Chat history display
        self.chat_display = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state="disabled", font=("Consolas", 11))
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Input frame for both text and buttons
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        self.prompt_entry = tk.Text(input_frame, height=3, wrap=tk.WORD, font=("Consolas", 11))
        self.prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        send_button = tk.Button(input_frame, text="Send", command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=5)

        file_button = tk.Button(input_frame, text="📄 Add File", command=self.import_file)
        file_button.pack(side=tk.RIGHT, padx=5)

        # Model selection
        model_frame = tk.Frame(self.root)
        model_frame.pack(pady=5)
        tk.Label(model_frame, text="Model:").pack(side=tk.LEFT)
        tk.OptionMenu(model_frame, self.model_var, "gemma3:1b", "gemma3:4b", "gemma3:12b").pack(side=tk.LEFT)

    def send_message(self, content_override=None):
        user_input = content_override or self.prompt_entry.get("1.0", tk.END).strip()
        if not user_input:
            return

        self.append_chat("You", user_input)
        self.prompt_entry.delete("1.0", tk.END)

        self.messages.append({"role": "user", "content": user_input})
        try:
            response: ChatResponse = chat(
                model=self.model_var.get(),
                messages=self.messages
            )
            reply = response.message.content.strip()
            self.messages.append({"role": "assistant", "content": reply})
            self.append_chat("Bot", reply)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def append_chat(self, speaker, message):
        self.chat_display.configure(state="normal")
        self.chat_display.insert(tk.END, f"{speaker}: {message}\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)

    def import_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF and Word files", "*.pdf *.docx")])
        if not file_path:
            return

        try:
            if file_path.lower().endswith(".pdf"):
                text = self.extract_text_from_pdf(file_path)
            elif file_path.lower().endswith(".docx"):
                text = self.extract_text_from_docx(file_path)
            else:
                raise ValueError("Unsupported file type.")

            # Insert file content into the prompt box so user can edit before sending
            self.prompt_entry.insert(tk.END, text.strip() + "\n")

        except Exception as e:
            messagebox.showerror("File Error", str(e))

    def extract_text_from_pdf(self, file_path):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()

    def extract_text_from_docx(self, file_path):
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

if __name__ == "__main__":
    root = tk.Tk()
    app = GPTChatUI(root)
    root.mainloop()