import tkinter as tk
import pyperclip
from pynput import mouse, keyboard
import time
import sys
import os
import subprocess
import logging


# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Global variables
TEXT_FILE_PATH = "mb.txt"
popup_window = None
last_text = ""
current_index = 0
root = None
is_running = True
MAX_RESULTS = 4  # Limit maximum number of results

logging.info("=" * 50)
logging.info("Starting main.py application")
logging.info("=" * 50)

# Add exception hook to catch unhandled exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


def check_accessibility_permissions():
    logging.info("Checking accessibility permissions...")
    if sys.platform != "darwin":  # Only check on macOS
        return True

    try:
        # Try to create a mouse listener to test permissions
        with mouse.Listener(on_click=lambda *args: None) as listener:
            logging.info("Accessibility permissions granted")
            return True
    except Exception as e:
        logging.error(f"Permission error: {str(e)}")
        if "Accessibility" in str(e):
            root = tk.Tk()
            root.withdraw()  # Hide the main window

            msg = tk.Toplevel(root)
            msg.title("Accessibility Permissions Required")

            label = tk.Label(
                msg,
                text="This app requires accessibility permissions to work.\n\n"
                "1. Open System Preferences > Security & Privacy > Privacy > Accessibility\n"
                "2. Click the lock icon to make changes\n"
                "3. Add and enable Terminal or Python in the list\n"
                "4. Restart the application",
                padx=20,
                pady=20,
                wraplength=400,
            )
            label.pack()

            def open_preferences():
                subprocess.run(
                    [
                        "open",
                        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                    ]
                )

            def quit_app():
                root.quit()
                sys.exit(0)

            tk.Button(
                msg, text="Open System Preferences", command=open_preferences
            ).pack(pady=5)
            tk.Button(msg, text="Quit", command=quit_app).pack(pady=5)

            # Center the window
            msg.update_idletasks()
            width = msg.winfo_width()
            height = msg.winfo_height()
            x = (msg.winfo_screenwidth() // 2) - (width // 2)
            y = (msg.winfo_screenheight() // 2) - (height // 2)
            msg.geometry(f"{width}x{height}+{x}+{y}")

            msg.mainloop()
            return False

        return False


def search_in_file(keyword, context_lines=4):  # Reduced context lines tcp
    logging.info(f"Searching for keyword: '{keyword}'")
    results = []

    try:
        if not os.path.exists(TEXT_FILE_PATH):
            logging.error(f"File not found: {TEXT_FILE_PATH}")
            print(f"Error: File {TEXT_FILE_PATH} not found")
            global is_running, root
            is_running = False
            if root and root.winfo_exists():
                root.quit()
                root.destroy()
            return [f"Error: File {TEXT_FILE_PATH} not found"]

        with open(TEXT_FILE_PATH, "r", encoding="utf-8") as file:
            line_num = 0

            for line in file:
                if keyword.lower() in line.lower():
                    snippet = line.strip()
                    # Add additional lines after the match
                    for _ in range(context_lines):
                        next_line = next(file, None)
                        if next_line:
                            snippet += f"\n{next_line.strip()}"
                    results.append(snippet)
                    if len(results) >= MAX_RESULTS:  # Limit number of results
                        break
                line_num += 1

                if line_num % 1000 == 0:  # Periodic garbage collection
                    import gc

                    gc.collect()

    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        results.append(f"[Error reading file: {e}]")

    if results:
        logging.info(f"Found {len(results)} match(es) for '{keyword}'")
    else:
        logging.info(f"No match found for '{keyword}'")
    return results if results else [f"No match found for: '{keyword}'"]


def create_popup(text_list):
    logging.info(f"Creating popup with {len(text_list)} result(s)")
    global popup_window, current_index, root

    if not root:
        logging.warning("Root window not available for popup")
        return

    if not root.winfo_exists():
        logging.warning("Root window does not exist")
        return

    current_index = 0

    try:
        if popup_window and popup_window.winfo_exists():
            logging.debug("Destroying existing popup window")
            popup_window.destroy()
            del popup_window  # Explicitly delete old window

        popup_window = tk.Toplevel(root)
        popup_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: (
                popup_window.destroy(),
                setattr(sys.modules[__name__], "popup_window", None),
            ),
        )
        popup_window.overrideredirect(True)
        popup_window.attributes("-topmost", True)
        popup_window.attributes("-alpha", 0.9)  # Slight transparency

        def update_display():
            for widget in popup_window.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(
                        text=f"[{current_index+1}/{len(text_list)}]\n{text_list[current_index]}"
                    )

        def on_key(event):
            global current_index
            if event.keysym in ("Right", "x") and current_index < len(text_list) - 1:
                current_index += 1
                update_display()
            elif event.keysym in ("Left", "z") and current_index > 0:
                current_index -= 1
                update_display()
            elif event.keysym == "Escape":
                popup_window.destroy()

        def on_move(x, y):
            if popup_window and popup_window.winfo_exists():
                popup_window.destroy()
                setattr(sys.modules[__name__], "popup_window", None)
            return True

        popup_window.bind("<Key>", on_key)
        popup_window.focus_force()
        popup_window.config(bg="white")
        popup_window.attributes("-transparentcolor", "white")

        label = tk.Label(
            popup_window,
            text=f"[{current_index+1}/{len(text_list)}]\n{text_list[0]}",
            font=("Courier", 9),
            bg="white",
            fg="black",
            justify="left",
            anchor="nw",
            padx=3,
            pady=3,
            wraplength=300,
        )
        label.pack(fill=tk.BOTH, expand=True)

        popup_window.update_idletasks()
        sw = popup_window.winfo_screenwidth()
        sh = popup_window.winfo_screenheight()
        w = 300
        h = 200
        x = (sw // 2) - (w // 2)
        y = sh - h  # Position at the very bottom of the screen
        popup_window.geometry(f"{w}x{h}+{x}+{y}")

        mouse_listener = mouse.Listener(on_scroll=on_move)
        mouse_listener.daemon = True
        mouse_listener.start()

    except Exception as e:
        pass


def show_popup(text_list):
    if root:
        root.after(0, lambda: create_popup(text_list))
    else:
        logging.error("Root window not available")


def on_mouse_release(x, y, button, pressed):
    if not pressed and is_running:
        logging.debug(f"Mouse released at ({x}, {y})")
        try:
            kb = keyboard.Controller()
            with kb.pressed(keyboard.Key.ctrl):
                kb.press("c")
                kb.release("c")

            time.sleep(0.1)
            selected = pyperclip.paste().strip()

            if not selected:
                logging.debug("No text selected")
                return

            logging.info(f"Text selected: '{selected[:50]}...'" if len(selected) > 50 else f"Text selected: '{selected}'")
            global last_text
            if selected and selected != last_text:
                last_text = selected
                matches = search_in_file(selected)
                show_popup(matches)
            else:
                logging.debug("Same text as before, skipping")
        except Exception as e:
            logging.error(f"Error in mouse release handler: {str(e)}")


if __name__ == "__main__":
    try:
        logging.info("Checking accessibility permissions...")
        if not check_accessibility_permissions():
            logging.error("Accessibility permissions not granted")
            sys.exit(1)

        logging.info("Creating root window...")
        root = tk.Tk()
        root.protocol(
            "WM_DELETE_WINDOW",
            lambda: (
                setattr(sys.modules[__name__], "is_running", False),
                root.destroy(),
            ),
        )
        root.withdraw()
        logging.info("Root window created and hidden")

        logging.info("Starting mouse listener...")
        mouse_listener = mouse.Listener(on_click=on_mouse_release)
        mouse_listener.daemon = True
        mouse_listener.start()
        logging.info("Mouse listener started successfully")

        def check_running():
            if is_running and root.winfo_exists():
                root.after(1000, check_running)
            else:
                logging.info("Application shutting down...")
                root.quit()

        logging.info("Application is now running. Select text with mouse to search.")
        logging.info("Press Ctrl+C in terminal to quit.")
        root.after(1000, check_running)
        root.mainloop()

    except Exception as e:
        logging.error(f"Fatal error in main: {str(e)}")
        sys.exit(1)
    finally:
        logging.info("Application terminated")
