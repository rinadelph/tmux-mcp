#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import os

class TmuxMessenger:
    def __init__(self, root):
        self.root = root
        self.root.title("Tmux Session Messenger")
        self.root.geometry("600x500")
        
        self.timer_active = False
        self.timer_thread = None
        self.auto_cycle_active = False
        self.auto_cycle_thread = None
        self.first_launch = True
        
        self.setup_ui()
        self.refresh_sessions()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Sessions list
        ttk.Label(main_frame, text="Tmux Sessions:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Sessions listbox with scrollbar
        sessions_frame = ttk.Frame(main_frame)
        sessions_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.sessions_listbox = tk.Listbox(sessions_frame, height=8)
        self.sessions_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        sessions_scrollbar = ttk.Scrollbar(sessions_frame, orient="vertical", command=self.sessions_listbox.yview)
        sessions_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sessions_listbox.configure(yscrollcommand=sessions_scrollbar.set)
        
        # Refresh button
        ttk.Button(main_frame, text="Refresh Sessions", command=self.refresh_sessions).grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        # Message input
        ttk.Label(main_frame, text="Message to send:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.message_entry = tk.Text(main_frame, height=4, width=50)
        self.message_entry.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Timer settings
        timer_frame = ttk.Frame(main_frame)
        timer_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(timer_frame, text="Send every:").grid(row=0, column=0, sticky=tk.W)
        self.timer_entry = ttk.Entry(timer_frame, width=10)
        self.timer_entry.grid(row=0, column=1, padx=(5, 5))
        self.timer_entry.insert(0, "5")
        ttk.Label(timer_frame, text="seconds").grid(row=0, column=2, sticky=tk.W)
        
        # Auto cycle controls
        auto_frame = ttk.LabelFrame(main_frame, text="Auto Exit/Continue Cycle", padding="5")
        auto_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_auto_btn = ttk.Button(auto_frame, text="Start Auto Cycle", command=self.start_auto_cycle)
        self.start_auto_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_auto_btn = ttk.Button(auto_frame, text="Stop Auto Cycle", command=self.stop_auto_cycle, state="disabled")
        self.stop_auto_btn.grid(row=0, column=1)
        
        # Control buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.send_once_btn = ttk.Button(buttons_frame, text="Send Once", command=self.send_once)
        self.send_once_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.start_timer_btn = ttk.Button(buttons_frame, text="Start Timer", command=self.start_timer)
        self.start_timer_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.stop_timer_btn = ttk.Button(buttons_frame, text="Stop Timer", command=self.stop_timer, state="disabled")
        self.stop_timer_btn.grid(row=0, column=2)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        sessions_frame.columnconfigure(0, weight=1)
        sessions_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def get_tmux_sessions(self):
        try:
            result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True, check=True)
            sessions = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    session_name = line.split(':')[0]
                    sessions.append((session_name, line))
            return sessions
        except subprocess.CalledProcessError:
            return []
        except FileNotFoundError:
            messagebox.showerror("Error", "tmux not found. Please install tmux.")
            return []
    
    def refresh_sessions(self):
        self.sessions_listbox.delete(0, tk.END)
        sessions = self.get_tmux_sessions()
        
        if not sessions:
            self.sessions_listbox.insert(tk.END, "No tmux sessions found")
            self.status_label.config(text="No sessions available")
        else:
            for session_name, session_info in sessions:
                self.sessions_listbox.insert(tk.END, session_info)
            self.status_label.config(text=f"Found {len(sessions)} sessions")
    
    def get_selected_session(self):
        selection = self.sessions_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a tmux session")
            return None
        
        session_line = self.sessions_listbox.get(selection[0])
        if session_line == "No tmux sessions found":
            messagebox.showwarning("Warning", "No valid session selected")
            return None
        
        return session_line.split(':')[0]
    
    def send_message_to_session(self, session_name, message):
        try:
            # Send the message using tmux send-keys
            subprocess.run(['tmux', 'send-keys', '-t', session_name, message], check=True)
            # Send Enter key using C-m (carriage return)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'C-m'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to send message to session '{session_name}': {e}")
            return False
        except FileNotFoundError:
            messagebox.showerror("Error", "tmux not found")
            return False
    
    def send_once(self):
        session_name = self.get_selected_session()
        if not session_name:
            return
        
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message:
            messagebox.showwarning("Warning", "Please enter a message to send")
            return
        
        if self.send_message_to_session(session_name, message):
            self.status_label.config(text=f"Message sent to '{session_name}'")
    
    def start_timer(self):
        session_name = self.get_selected_session()
        if not session_name:
            return
        
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message:
            messagebox.showwarning("Warning", "Please enter a message to send")
            return
        
        try:
            interval = float(self.timer_entry.get())
            if interval <= 0:
                raise ValueError("Timer must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive number for timer interval")
            return
        
        self.timer_active = True
        self.start_timer_btn.config(state="disabled")
        self.stop_timer_btn.config(state="normal")
        self.send_once_btn.config(state="disabled")
        
        def timer_loop():
            while self.timer_active:
                if self.send_message_to_session(session_name, message):
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"Timer active - Last sent to '{session_name}' at {time.strftime('%H:%M:%S')}"
                    ))
                
                # Wait for the specified interval, but check every 0.1 seconds if we should stop
                elapsed = 0
                while elapsed < interval and self.timer_active:
                    time.sleep(0.1)
                    elapsed += 0.1
        
        self.timer_thread = threading.Thread(target=timer_loop, daemon=True)
        self.timer_thread.start()
        
        self.status_label.config(text=f"Timer started - sending every {interval}s to '{session_name}'")
    
    def stop_timer(self):
        self.timer_active = False
        if self.timer_thread:
            self.timer_thread.join(timeout=1)
        
        self.start_timer_btn.config(state="normal")
        self.stop_timer_btn.config(state="disabled")
        self.send_once_btn.config(state="normal")
        self.status_label.config(text="Timer stopped")
    
    def send_exit_continue_sequence(self, session_name):
        try:
            # Send Ctrl+C 5 times for robust termination
            for i in range(5):
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'C-c'], check=True)
                time.sleep(0.2)
            
            # Wait 1 second
            time.sleep(1)
            
            # Send mullvad reconnect
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'mullvad reconnect'], check=True)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'Enter'], check=True)
            
            # Wait 3 seconds for mullvad to reconnect
            time.sleep(3)
            
            # Send claudex -c
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'claudex -c'], check=True)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'Enter'], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send exit/continue sequence to session '{session_name}': {e}"))
            return False
        except FileNotFoundError:
            self.root.after(0, lambda: messagebox.showerror("Error", "tmux not found"))
            return False
    
    def start_auto_cycle(self):
        session_name = self.get_selected_session()
        if not session_name:
            return
        
        self.auto_cycle_active = True
        self.start_auto_btn.config(state="disabled")
        self.stop_auto_btn.config(state="normal")
        self.start_timer_btn.config(state="disabled")
        self.send_once_btn.config(state="disabled")
        
        def auto_cycle_loop():
            # If this is the first launch, start immediately
            if self.first_launch:
                self.first_launch = False
                if self.send_exit_continue_sequence(session_name):
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"Auto cycle active - First sequence sent to '{session_name}' at {time.strftime('%H:%M:%S')}"
                    ))
            
            # Then continue with 4-minute intervals
            while self.auto_cycle_active:
                # Wait for 4 minutes (240 seconds), checking every 0.5 seconds if we should stop
                elapsed = 0
                while elapsed < 240 and self.auto_cycle_active:
                    time.sleep(0.5)
                    elapsed += 0.5
                
                if self.auto_cycle_active:
                    if self.send_exit_continue_sequence(session_name):
                        self.root.after(0, lambda: self.status_label.config(
                            text=f"Auto cycle active - Last sequence sent to '{session_name}' at {time.strftime('%H:%M:%S')}"
                        ))
        
        self.auto_cycle_thread = threading.Thread(target=auto_cycle_loop, daemon=True)
        self.auto_cycle_thread.start()
        
        self.status_label.config(text=f"Auto cycle started - Ctrl+C spam + mullvad reconnect + claudex -c every 4 minutes to '{session_name}'")
    
    def stop_auto_cycle(self):
        self.auto_cycle_active = False
        if self.auto_cycle_thread:
            self.auto_cycle_thread.join(timeout=1)
        
        self.start_auto_btn.config(state="normal")
        self.stop_auto_btn.config(state="disabled")
        self.start_timer_btn.config(state="normal")
        self.send_once_btn.config(state="normal")
        self.status_label.config(text="Auto cycle stopped")

def main():
    root = tk.Tk()
    app = TmuxMessenger(root)
    
    def on_closing():
        if app.timer_active:
            app.stop_timer()
        if app.auto_cycle_active:
            app.stop_auto_cycle()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()