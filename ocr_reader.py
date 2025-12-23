import tkinter as tk
from tkinter import ttk
import pytesseract
from PIL import ImageGrab, Image
import pyperclip
from pynput import mouse, keyboard
import time
import sys
import os
import logging


# Global variables
TEXT_FILE_PATH = "mb.txt"
popup_window = None
last_extracted_text = ""
current_index = 0
root = None
is_running = True
MAX_RESULTS = 4
selection_overlay = None


# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logging.info("=" * 50)
logging.info("Starting OCR Reader application")
logging.info("=" * 50)


# Exception hook
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


def capture_screen_region(x1, y1, x2, y2):
    """Capture a region of the screen and return PIL Image"""
    logging.info(f"Capturing screen region: ({x1}, {y1}) to ({x2}, {y2})")
    try:
        # Ensure coordinates are in correct order
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        logging.debug(f"Adjusted coordinates: ({left}, {top}) to ({right}, {bottom})")
        # Capture the screen region
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        logging.info(f"Screen captured successfully. Size: {screenshot.size}")
        return screenshot
    except Exception as e:
        logging.error(f"Error capturing screen: {str(e)}")
        return None


def extract_text_from_image(image):
    """Extract text from image using Pytesseract OCR"""
    logging.info("Starting OCR text extraction...")
    try:
        # Use pytesseract to extract text
        text = pytesseract.image_to_string(image, lang='eng')
        text = text.strip()
        logging.info(f"OCR completed. Extracted {len(text)} characters")
        logging.debug(f"Extracted text: {text[:100]}..." if len(text) > 100 else f"Extracted text: {text}")
        return text
    except Exception as e:
        logging.error(f"Error extracting text: {str(e)}")
        return f"Error: {str(e)}"


def search_in_file(keyword, context_lines=4):
    """Search for keyword in text file and return matching results"""
    results = []

    try:
        if not os.path.exists(TEXT_FILE_PATH):
            logging.error(f"File not found: {TEXT_FILE_PATH}")
            return [f"Error: File {TEXT_FILE_PATH} not found"]

        with open(TEXT_FILE_PATH, "r", encoding="utf-8") as file:
            lines = file.readlines()
            
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                snippet = line.strip()
                # Add context lines after the match
                for j in range(1, context_lines + 1):
                    if i + j < len(lines):
                        snippet += f"\n{lines[i + j].strip()}"
                results.append(snippet)
                if len(results) >= MAX_RESULTS:
                    break

    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        results.append(f"[Error reading file: {e}]")

    return results if results else [f"No match found for: '{keyword}'"]


def create_popup(text_list, title="OCR Results"):
    """Create popup window to display results"""
    global popup_window, current_index, root

    if not root or not root.winfo_exists():
        return

    current_index = 0

    try:
        if popup_window and popup_window.winfo_exists():
            popup_window.destroy()

        popup_window = tk.Toplevel(root)
        popup_window.title(title)
        popup_window.attributes("-topmost", True)
        popup_window.attributes("-alpha", 0.95)

        def update_display():
            text_widget.delete('1.0', tk.END)
            text_widget.insert('1.0', text_list[current_index])
            counter_label.config(text=f"Result {current_index + 1} of {len(text_list)}")

        def on_key(event):
            global current_index
            if event.keysym in ("Right", "x", "n") and current_index < len(text_list) - 1:
                current_index += 1
                update_display()
            elif event.keysym in ("Left", "z", "p") and current_index > 0:
                current_index -= 1
                update_display()
            elif event.keysym == "Escape":
                popup_window.destroy()
            elif event.keysym == "c" and event.state & 0x0004:  # Ctrl+C
                pyperclip.copy(text_widget.get('1.0', tk.END))

        def copy_to_clipboard():
            pyperclip.copy(text_widget.get('1.0', tk.END).strip())
            copy_btn.config(text="✓ Copied!")
            popup_window.after(1000, lambda: copy_btn.config(text="Copy"))

        popup_window.bind("<Key>", on_key)
        popup_window.focus_force()

        # Frame for controls
        control_frame = tk.Frame(popup_window, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Counter label
        counter_label = tk.Label(
            control_frame,
            text=f"Result {current_index + 1} of {len(text_list)}",
            font=("Arial", 10),
            bg="#f0f0f0"
        )
        counter_label.pack(side=tk.LEFT, padx=5)

        # Navigation buttons
        btn_frame = tk.Frame(control_frame, bg="#f0f0f0")
        btn_frame.pack(side=tk.RIGHT)

        prev_btn = tk.Button(btn_frame, text="← Prev (Z)", command=lambda: on_key(type('obj', (), {'keysym': 'Left'})))
        prev_btn.pack(side=tk.LEFT, padx=2)

        next_btn = tk.Button(btn_frame, text="Next (X) →", command=lambda: on_key(type('obj', (), {'keysym': 'Right'})))
        next_btn.pack(side=tk.LEFT, padx=2)

        copy_btn = tk.Button(btn_frame, text="Copy", command=copy_to_clipboard)
        copy_btn.pack(side=tk.LEFT, padx=2)

        # Text widget with scrollbar
        text_frame = tk.Frame(popup_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            text_frame,
            font=("Courier", 10),
            bg="white",
            fg="black",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=5,
            pady=5
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # Insert initial text
        text_widget.insert('1.0', text_list[0])

        # Position window
        popup_window.update_idletasks()
        w = 500
        h = 400
        sw = popup_window.winfo_screenwidth()
        sh = popup_window.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        popup_window.geometry(f"{w}x{h}+{x}+{y}")

    except Exception as e:
        logging.error(f"Error creating popup: {str(e)}")


def show_selection_overlay():
    """Create transparent overlay for screen region selection"""
    global selection_overlay

    selection_overlay = tk.Toplevel(root)
    selection_overlay.attributes("-fullscreen", True)
    selection_overlay.attributes("-alpha", 0.3)
    selection_overlay.attributes("-topmost", True)
    selection_overlay.config(bg="gray")

    canvas = tk.Canvas(selection_overlay, bg="gray", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    selection_data = {
        'rect': None,
        'start_pos': None,
        'end_pos': None
    }

    instruction_text = canvas.create_text(
        selection_overlay.winfo_screenwidth() // 2,
        50,
        text="Click and drag to select screen region for OCR\nPress ESC to cancel",
        font=("Arial", 16, "bold"),
        fill="white"
    )

    def on_mouse_down(event):
        selection_data['start_pos'] = (event.x, event.y)
        if selection_data['rect']:
            canvas.delete(selection_data['rect'])

    def on_mouse_drag(event):
        if selection_data['start_pos']:
            if selection_data['rect']:
                canvas.delete(selection_data['rect'])
            selection_data['rect'] = canvas.create_rectangle(
                selection_data['start_pos'][0], selection_data['start_pos'][1],
                event.x, event.y,
                outline="red",
                width=3
            )

    def on_mouse_up(event):
        selection_data['end_pos'] = (event.x, event.y)
        selection_overlay.destroy()
        process_selection(selection_data['start_pos'], selection_data['end_pos'])

    def on_escape(event):
        selection_overlay.destroy()

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    selection_overlay.bind("<Escape>", on_escape)


def process_selection(start_pos, end_pos):
    """Process the selected screen region"""
    global last_extracted_text

    if not start_pos or not end_pos:
        return

    # Small delay to ensure overlay is fully closed
    time.sleep(0.2)

    # Capture screen region
    image = capture_screen_region(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
    
    if image:
        # Extract text using OCR
        extracted_text = extract_text_from_image(image)
        
        if extracted_text and extracted_text != last_extracted_text:
            last_extracted_text = extracted_text
            
            # Show extracted text
            root.after(0, lambda: create_popup([f"Extracted Text:\n\n{extracted_text}"], "OCR - Extracted Text"))
            
            # Also search in file if text was extracted
            if len(extracted_text) > 2:  # Only search if meaningful text
                # Search for the first few words
                search_terms = extracted_text.split()[:3]  # First 3 words
                if search_terms:
                    matches = search_in_file(' '.join(search_terms))
                    if matches and "No match found" not in matches[0]:
                        root.after(100, lambda: create_popup(matches, "Search Results"))


def on_hotkey():
    """Triggered when hotkey is pressed - shows selection overlay"""
    logging.info("Hotkey pressed! Showing selection overlay...")
    if is_running and root and root.winfo_exists():
        root.after(0, show_selection_overlay)
    else:
        logging.warning("Cannot show overlay - app not ready")


def setup_hotkey_listener():
    """Setup global hotkey listener for Cmd+Shift+S (or Ctrl+Shift+S on other platforms)"""
    current_keys = set()

    def on_press(key):
        try:
            current_keys.add(key)
            # Check for Cmd+Shift+S on macOS or Ctrl+Shift+S on other platforms
            if sys.platform == "darwin":
                # macOS: Cmd+Shift+S
                if (keyboard.Key.cmd in current_keys and 
                    keyboard.Key.shift in current_keys and 
                    hasattr(key, 'char') and key.char == 's'):
                    on_hotkey()
            else:
                # Other platforms: Ctrl+Shift+S
                if (keyboard.Key.ctrl in current_keys and 
                    keyboard.Key.shift in current_keys and 
                    hasattr(key, 'char') and key.char == 's'):
                    on_hotkey()
        except AttributeError:
            pass

    def on_release(key):
        try:
            if key in current_keys:
                current_keys.remove(key)
        except KeyError:
            pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()


def create_control_window():
    """Create a small control window with instructions"""
    global root
    
    control = tk.Toplevel(root)
    control.title("OCR Screen Reader Control")
    control.attributes("-topmost", True)
    
    instructions = tk.Label(
        control,
        text="📖 OCR Screen Reader\n\n"
             "Hotkey: Cmd+Shift+S (Mac) / Ctrl+Shift+S (Others)\n\n"
             "1. Press hotkey to select screen region\n"
             "2. Click and drag to select area\n"
             "3. Text will be extracted via OCR\n"
             "4. Results will be searched in database\n\n"
             "Press 'Start' to begin monitoring",
        padx=20,
        pady=20,
        justify=tk.LEFT,
        font=("Arial", 11)
    )
    instructions.pack()
    
    def start_monitoring():
        global is_running
        is_running = True
        setup_hotkey_listener()
        start_btn.config(state=tk.DISABLED, text="✓ Monitoring Active")
        status_label.config(text="Status: Active - Press Cmd+Shift+S", fg="green")
    
    def stop_monitoring():
        global is_running
        is_running = False
        start_btn.config(state=tk.NORMAL, text="Start Monitoring")
        status_label.config(text="Status: Stopped", fg="red")
    
    button_frame = tk.Frame(control)
    button_frame.pack(pady=10)
    
    start_btn = tk.Button(button_frame, text="Start Monitoring", command=start_monitoring, width=15)
    start_btn.pack(side=tk.LEFT, padx=5)
    
    stop_btn = tk.Button(button_frame, text="Stop", command=stop_monitoring, width=15)
    stop_btn.pack(side=tk.LEFT, padx=5)
    
    status_label = tk.Label(control, text="Status: Ready", fg="orange", font=("Arial", 10, "bold"))
    status_label.pack(pady=5)
    
    # Position window
    control.update_idletasks()
    w = control.winfo_width()
    h = control.winfo_height()
    x = (control.winfo_screenwidth() // 2) - (w // 2)
    y = 50
    control.geometry(f"+{x}+{y}")
    
    return control


if __name__ == "__main__":
    try:
        # Check if pytesseract is available
        logging.info("Checking Tesseract installation...")
        try:
            version = pytesseract.get_tesseract_version()
            logging.info(f"Tesseract version: {version}")
        except Exception as e:
            logging.error(f"Tesseract not found: {str(e)}")
            print("Error: Pytesseract not found!")
            print("Please install Tesseract OCR:")
            print("  macOS: brew install tesseract")
            print("  Linux: sudo apt-get install tesseract-ocr")
            print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            sys.exit(1)

        logging.info("Creating main window...")
        root = tk.Tk()
        root.withdraw()  # Hide main window
        logging.info("Main window created")
        
        logging.info("Creating control window...")
        control_window = create_control_window()
        logging.info("Control window ready")
        
        def on_close():
            global is_running
            logging.info("Close button pressed")
            is_running = False
            root.quit()
            root.destroy()
        
        control_window.protocol("WM_DELETE_WINDOW", on_close)
        
        logging.info("Application ready. Waiting for user input...")
        root.mainloop()

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("Application terminated")
