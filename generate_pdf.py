from fpdf import FPDF
import os
import re

# Path config
MD_FILE = r"c:\Users\chim01\.gemini\antigravity\brain\0ab3a74e-3974-4025-ad11-c44788f0de5f\system_workflows.md"
OUTPUT_FILE = r"c:\Users\chim01\Desktop\meta\projects\SMART-WAITER\Smart_Waiter_System_Workflows.pdf"

print(f"DEBUG: Starting PDF generation...")
if not os.path.exists(MD_FILE):
    print(f"ERROR: MD File not found at {MD_FILE}")
else:
    print(f"DEBUG: Found MD File.")


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Smart Waiter System Workflows", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, label):
        self.set_font("Helvetica", "B", 16)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, label, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(4)

    def chapter_subtitle(self, label):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, label, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def chapter_body(self, text):
        self.set_font("Helvetica", "", 12)
        try:
            self.multi_cell(self.epw, 6, text)
            self.ln()
        except Exception as e:
            print(f"Skipping body text: {e}")

    def code_block(self, text):
        self.set_font("Courier", "", 10)
        self.set_fill_color(240, 240, 240)
        try:
            self.multi_cell(self.epw, 5, text, fill=True, border=1)
            self.ln()
        except:
            pass
        
    def list_item(self, text, indent=False):
        self.set_font("Helvetica", "", 12)
        prefix = "  - " if indent else "- " 
        msg = f"{prefix}{text}"
        try:
            self.multi_cell(self.epw, 6, msg)
        except Exception as e:
            print(f"Warning: Could not render line: {msg[:20]}... Error: {e}")
            self.ln()


def parse_markdown_to_pdf(input_path, output_path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    in_code_block = False
    code_buffer = ""
    
    for line in lines:
        stripped = line.rstrip()
        
        # Code Block Handling
        if stripped.strip().startswith("```"):
            if in_code_block:
                # End of block
                pdf.code_block(code_buffer)
                code_buffer = ""
                in_code_block = False
            else:
                # Start of block
                in_code_block = True
            continue
            
        if in_code_block:
            code_buffer += stripped + "\n"
            continue
            
        # Headers
        if stripped.startswith("# "):
            pdf.chapter_title(stripped[2:])
        elif stripped.startswith("## "):
            pdf.chapter_subtitle(stripped[3:])
        elif stripped.startswith("### "):
            self_font_bak = pdf.font_size_pt
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, stripped[4:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 12)
        elif stripped.strip().startswith("- ") or stripped.strip().startswith("* "):
            # Bullet point
            content = stripped.strip()[2:]
            pdf.list_item(content)
        elif re.match(r'^\d+\.', stripped.strip()):
            # Numbered list
            pdf.list_item(stripped.strip())
        else:
            # Normal Text
            if stripped:
                pdf.chapter_body(stripped)
                
    pdf.output(output_path)
    print(f"PDF generated successfully: {output_path}")

if __name__ == "__main__":
    if not os.path.exists(MD_FILE):
        print(f"Error: input file {MD_FILE} not found.")
    else:
        parse_markdown_to_pdf(MD_FILE, OUTPUT_FILE)
