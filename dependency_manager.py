# flake8: noqa: E501
"""
Dependency manager for TransMatch.

Handles ML library detection and path setup for packaged libraries.
ML libraries are packaged with the application and should not be downloaded at runtime.
"""

import importlib
import os
import sys
from typing import Optional

import logger

# Optional tkinter import (only needed for dialogs)
try:
    import tkinter as tk
    from tkinter import messagebox
    _has_tkinter = True
except ImportError:
    _has_tkinter = False

# Track user choice for manual input
_user_chose_manual_input = False
_ml_choice_dialog_shown = False

# ML libraries path (set once on first check)
_ml_libraries_path = None


def reset_ml_choice_flags():
    """Reset ML choice flags when a new file is selected."""
    global _user_chose_manual_input, _ml_choice_dialog_shown
    _user_chose_manual_input = False
    _ml_choice_dialog_shown = False


def get_log_file_path() -> str:
    """Get the path to the current log file."""
    from datetime import datetime
    
    # Detect PyInstaller bundle or dev mode
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_dir = os.path.join(base_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"TransMatch_log_{datetime.now().strftime('%Y%m%d')}.txt"
    return os.path.join(log_dir, log_filename)


def get_ml_model_storage_path() -> str:
    """Get the path where sentence-transformers models are stored."""
    # First check if models are packaged with the application
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, "_internal")
        
        # Check _internal first (where we copy ml_libraries), then next to exe
        model_paths = [
            os.path.join(internal_dir, "ml_libraries", "models"),  # _internal/ml_libraries/models
            os.path.join(exe_dir, "ml_libraries", "models"),       # exe_dir/ml_libraries/models
        ]
        
        for packaged_models_path in model_paths:
            if os.path.exists(packaged_models_path):
                return packaged_models_path
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        packaged_models_path = os.path.join(base_dir, "ml_libraries", "models")
        if os.path.exists(packaged_models_path):
            return packaged_models_path
    
    # Fallback to default Hugging Face cache location
    home = os.path.expanduser("~")
    cache_path = os.path.join(home, ".cache", "huggingface", "hub")
    return cache_path


def _setup_ml_libraries_path():
    """
    Setup the path to packaged ML libraries.
    This adds the ml_libraries folder to sys.path so packages can be imported.
    """
    global _ml_libraries_path
    
    if _ml_libraries_path is not None:
        return _ml_libraries_path
    
    # Detect PyInstaller bundle or dev mode
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, "_internal")
        
        # Check _internal first (where we copy ml_libraries), then next to exe
        ml_lib_paths = [
            os.path.join(internal_dir, "ml_libraries"),  # _internal/ml_libraries
            os.path.join(exe_dir, "ml_libraries"),        # exe_dir/ml_libraries
        ]
        
        ml_lib_dir = None
        for path in ml_lib_paths:
            if os.path.exists(path):
                ml_lib_dir = path
                break
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ml_lib_dir = os.path.join(base_dir, "ml_libraries")
    
    if ml_lib_dir and os.path.exists(ml_lib_dir):
        # Add to sys.path if not already there
        if ml_lib_dir not in sys.path:
            sys.path.insert(0, ml_lib_dir)
            logger.logger.info(f"[dependency_manager] : Added ML libraries path: {ml_lib_dir}")
        _ml_libraries_path = ml_lib_dir
        return ml_lib_dir
    
    _ml_libraries_path = None
    return None


def _has_sentence_transformers() -> bool:
    """
    Return True if sentence-transformers can be imported.
    Checks packaged location first, then system installation.
    """
    # Setup packaged libraries path first
    ml_lib_path = _setup_ml_libraries_path()
    
    # Log the path for debugging
    if ml_lib_path:
        logger.logger.info(f"[dependency_manager] : Checking for sentence_transformers in: {ml_lib_path}")
        # Check if sentence_transformers folder exists
        st_path = os.path.join(ml_lib_path, "sentence_transformers")
        if os.path.exists(st_path):
            logger.logger.info(f"[dependency_manager] : sentence_transformers folder found at: {st_path}")
        else:
            logger.logger.warning(f"[dependency_manager] : sentence_transformers folder NOT found at: {st_path}")
            # List what's actually in ml_libraries
            if os.path.exists(ml_lib_path):
                try:
                    contents = os.listdir(ml_lib_path)
                    logger.logger.info(f"[dependency_manager] : Contents of ml_libraries: {contents[:10]}")  # First 10 items
                except Exception as e:
                    logger.logger.warning(f"[dependency_manager] : Could not list ml_libraries contents: {e}")
    
    # Try to import
    try:
        # First ensure the path is in sys.path (double-check)
        if ml_lib_path and ml_lib_path not in sys.path:
            sys.path.insert(0, ml_lib_path)
            logger.logger.info(f"[dependency_manager] : Re-added ml_libraries to sys.path: {ml_lib_path}")
        
        importlib.import_module("sentence_transformers")
        logger.logger.info(f"[dependency_manager] : Successfully imported sentence_transformers")
        return True
    except ImportError as e:
        logger.logger.warning(f"[dependency_manager] : Failed to import sentence_transformers: {e}")
        logger.logger.info(f"[dependency_manager] : Current sys.path entries with ml_libraries: {[p for p in sys.path if 'ml_libraries' in p]}")
        # Try to get more details about the import error
        import traceback
        logger.logger.debug(f"[dependency_manager] : Import error traceback: {traceback.format_exc()}")
        return False
    except Exception as e:
        logger.logger.error(f"[dependency_manager] : Unexpected error importing sentence_transformers: {e}")
        import traceback
        logger.logger.exception(f"[dependency_manager] : Full traceback:")
        return False


def ensure_sentence_transformers(parent: Optional[tk.Misc] = None, show_failure_message: bool = True, 
                                  show_choice_dialog: bool = True) -> bool:
    """
    Ensure sentence-transformers is available.
    
    Returns:
        True if available, False if not available (user can proceed with manual input),
        None if user cancelled.
    """
    global _user_chose_manual_input, _ml_choice_dialog_shown
    
    if _has_sentence_transformers():
        return True
    
    # ML library not available
    if show_choice_dialog and not _ml_choice_dialog_shown and _has_tkinter:
        _ml_choice_dialog_shown = True
        
        try:
            
            # Create a custom dialog with two options
            choice_dialog = tk.Toplevel(parent if parent else None)
            choice_dialog.title("ML Library Not Available")
            choice_dialog.geometry("500x200")
            choice_dialog.configure(bg="#0b1120")
            choice_dialog.resizable(False, False)
            choice_dialog.attributes("-topmost", True)
            if parent:
                choice_dialog.transient(parent)
            
            # Center the dialog
            choice_dialog.update_idletasks()
            if parent:
                x = parent.winfo_x() + (parent.winfo_width() // 2) - (choice_dialog.winfo_width() // 2)
                y = parent.winfo_y() + (parent.winfo_height() // 2) - (choice_dialog.winfo_height() // 2)
            else:
                x = (choice_dialog.winfo_screenwidth() // 2) - (choice_dialog.winfo_width() // 2)
                y = (choice_dialog.winfo_screenheight() // 2) - (choice_dialog.winfo_height() // 2)
            choice_dialog.geometry(f"+{x}+{y}")
            
            # Message label
            msg_label = tk.Label(
                choice_dialog,
                text="ML library is not available.\n\nPlease choose an option:",
                font=("Segoe UI", 10),
                fg="white",
                bg="#0b1120",
                justify="center",
                wraplength=450
            )
            msg_label.pack(pady=(20, 15))
            
            # Result variable
            result = {"choice": None}
            
            def choose_manual():
                global _user_chose_manual_input
                result["choice"] = "manual"
                _user_chose_manual_input = True
                choice_dialog.destroy()
            
            def choose_cancel():
                result["choice"] = "cancel"
                choice_dialog.destroy()
            
            # Buttons frame
            button_frame = tk.Frame(choice_dialog, bg="#0b1120")
            button_frame.pack(pady=10)
            
            # Continue with manual input button
            manual_btn = tk.Button(
                button_frame,
                text="Continue with Manual Input",
                command=choose_manual,
                font=("Segoe UI", 9),
                bg="#1e3a8a",
                fg="white",
                activebackground="#1e40af",
                activeforeground="white",
                padx=15,
                pady=8,
                cursor="hand2"
            )
            manual_btn.pack(side=tk.LEFT, padx=10)
            
            # Cancel button
            cancel_btn = tk.Button(
                button_frame,
                text="Cancel & Select Another File",
                command=choose_cancel,
                font=("Segoe UI", 9),
                bg="#7f1d1d",
                fg="white",
                activebackground="#991b1b",
                activeforeground="white",
                padx=15,
                pady=8,
                cursor="hand2"
            )
            cancel_btn.pack(side=tk.LEFT, padx=10)
            
            # Wait for user choice
            choice_dialog.wait_window()
            
            if result["choice"] == "manual":
                _user_chose_manual_input = True
                return False  # Return False to indicate ML is not ready, but user chose manual input
            elif result["choice"] == "cancel":
                return None  # Return None to indicate user cancelled
            else:
                # Dialog closed without choice, treat as cancel
                return None
        except Exception as e:
            logger.logger.exception(f"[dependency_manager] : Error showing choice dialog: {e}")
            # Fall through to show failure message
    
    elif _user_chose_manual_input:
        # User already chose manual input, silently return False
        return False
    
    # Show failure message if requested
    if show_failure_message and _has_tkinter:
        try:
            messagebox.showwarning(
                "TransMatch",
                "ML library (sentence-transformers) is not available.\n"
                "Advanced name extraction features will be disabled.\n"
                "You can still use manual input."
            )
        except Exception:
            pass
    
    return False
