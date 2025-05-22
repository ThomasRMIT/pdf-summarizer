import fitz
from reportlab.pdfgen import canvas
from ollama import chat
from ollama import ChatResponse
import time

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
import re
import requests

CURRENT_VERSION = "1.0.6"
GITHUB_REPO = "ThomasRMIT/pdf-summarizer"

def check_for_update():
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(api_url)
        response.raise_for_status()

        latest_version = response.json()["tag_name"].lstrip("v")

        if latest_version > CURRENT_VERSION:
            return True, latest_version, response.json()["html_url"]
        return False, latest_version, ""
    except Exception as e:
        print(f"[ERROR] Failed to check for updates: {e}")
        return False, "", ""

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ''
    for page in doc:
        text += page.get_text()
    return text

def summarize_text(text, model, num_ctx=8192, temperature=0.0):
    response: ChatResponse = chat(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': f'''
                
                Please read through the following witness statement and generate only the following two sections of a Circumstances Report:

                1. Description of Events (Chronological)
                List the events in the order they occurred, grouped by date when possible. Use subheadings for specific dates (e.g., “25 March 2025”) and describe what happened factually on that day. Only include events directly related to the incident and its immediate aftermath.

                2. Post-Incident Condition
                Summarize the individual's condition following the incident, including medication taken, time off work, return-to-work status, and any ongoing issues, based only on the statement provided.

                Do not include opinions, assumptions, or inferred information. Only include information explicitly stated in the witness statement.

                :\n\n{text}''',
            },
        ],
        options={
            'num_ctx': num_ctx,
            'temperature': temperature
        }
    )
    return response.message.content

def clean_summary_text(text):
    # Remove leading meta comments like "Here's a summary..."
    text = re.sub(r"(?i)^here(?:'s| is) a summary.*?:\s*", "", text, count=1)

    # Remove trailing Q&A prompts like "Do you want me to..." or "Let me know if..."
    text = re.split(r"\n+(do you want me to.*|let me know if.*)", text, flags=re.IGNORECASE)[0]

    # Strip trailing whitespace
    return text.strip()

def write_summary_to_pdf(summary_text, output_path):
    doc = SimpleDocTemplate(output_path)
    styles = getSampleStyleSheet()
    
    paragraph_style = styles["BodyText"]
    bullet_style = ParagraphStyle(
        name="Bullet",
        parent=styles["Normal"],
        leftIndent=20,
        bulletIndent=10,
        spaceBefore=4,
    )
    heading_style = ParagraphStyle(
        name="Heading",
        parent=styles["Heading2"],
        spaceAfter=6,
    )

    elements = []

    def format_markdown(text):
        # Handle **bold** first to avoid nesting issues
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        return text

    lines = summary_text.strip().split('\n')
    buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                combined = format_markdown(' '.join(buffer))
                elements.append(Paragraph(combined, paragraph_style))
                elements.append(Spacer(1, 0.15 * inch))
                buffer = []
            continue

        # Bullet point detection
        if stripped.startswith("•"):
            bullet_content = stripped[1:].strip()
            bullet_formatted = format_markdown(bullet_content)
            elements.append(ListFlowable(
                [ListItem(Paragraph(bullet_formatted, bullet_style))],
                bulletType='bullet'
            ))
            continue

        # Headings (e.g., "**Summary Report**:")
        if stripped.startswith("**") and stripped.endswith("**"):
            heading = stripped.strip("*")
            elements.append(Paragraph(f"<b>{heading}</b>", heading_style))
            continue

        buffer.append(stripped)

    # Final buffer flush
    if buffer:
        combined = format_markdown(' '.join(buffer))
        elements.append(Paragraph(combined, paragraph_style))

    doc.build(elements)

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import os

def extract_title_from_summary(text):
    # Match first bold title: e.g., **Summary Report – John Doe Statement**
    match = re.search(r'\*\*(.+?)\*\*', text)
    if match:
        title = match.group(1)
        # Sanitize filename: remove slashes, colons, etc.
        title = re.sub(r'[\\/:"*?<>|]+', '', title).strip()
        return title
    return "summary_report"

def process_pdf(pdf_path):
    try:
        pdf_text = extract_text_from_pdf(pdf_path)
        selected_model = model_var.get()
        
        start_time = time.time()
        temperature = 0.0
        summary = summarize_text(pdf_text, model=selected_model, num_ctx=num_ctx, temperature=temperature)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"[INFO] Model '{selected_model}' took {elapsed_time:.2f} seconds with temperature {temperature:.1f}.")
        
        cleaned_summary = clean_summary_text(summary)
        title = extract_title_from_summary(cleaned_summary)
        output_dir = os.path.dirname(pdf_path)
        output_file = os.path.join(output_dir, f"{title}.pdf")
        
        write_summary_to_pdf(cleaned_summary, output_file)
        messagebox.showinfo("Success", f"Summary saved to:\n{output_file}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        process_pdf(file_path)

def on_drop(event):
    pdf_path = event.data.strip('{}')  # Remove curly braces from Windows path
    if pdf_path.lower().endswith('.pdf'):
        process_pdf(pdf_path)
    else:
        messagebox.showwarning("Invalid File", "Please drop a .pdf file.")

# GUI Setup
num_ctx = 8192

app = TkinterDnD.Tk()
app.title("PDF Summarizer")
app.geometry("500x300")

label = tk.Label(app, text="Drag and drop a PDF here,\nor click the button to select one.", font=("Helvetica", 14))
label.pack(pady=50)

# Drag-and-Drop Area
drop_area = tk.Label(app, text="⬇ Drop PDF File Here ⬇", relief="groove", height=5, width=50)
drop_area.pack(pady=10)
drop_area.drop_target_register(DND_FILES)
drop_area.dnd_bind('<<Drop>>', on_drop)

# File Picker Button
browse_button = tk.Button(app, text="Select PDF File", command=select_file)
browse_button.pack(pady=20)

# Model selector
model_var = tk.StringVar(value="gemma3:4b")  # Default model

model_label = tk.Label(app, text="Model:", font=("Helvetica", 10))
model_label.place(relx=0.75, rely=0.05)


model_menu = tk.OptionMenu(app, model_var, "gemma3:1b", "gemma3:4b", "gemma3:12b")
model_menu.place(relx=0.82, rely=0.04)

# Status label
status_label = tk.Label(app, text="", font=("Helvetica", 10), fg="gray")
status_label.pack(pady=5)

is_update, latest_version, release_url = check_for_update()
if is_update:
    if messagebox.askyesno("Update Available", f"A new version (v{latest_version}) is available. Do you want to download it?"):
        import webbrowser
        webbrowser.open(release_url)

app.mainloop()