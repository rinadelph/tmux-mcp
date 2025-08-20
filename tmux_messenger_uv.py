#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import pyuv
import signal
import os
import time
import functools

class TmuxMessengerUV:
    def __init__(self, root):
        self.root = root
        self.root.title("Tmux Session Messenger (UV)")
        self.root.geometry("600x500")
        
        self.loop = pyuv.Loop.default_loop()
        
        self.timer_handle = None
        self.auto_cycle_handle = None
        self.first_launch = True
        
        self.setup_ui()
        self.refresh_sessions()
        
        # Setup UV loop integration with Tkinter
        self.setup_uv_integration()
    
    def setup_uv_integration(self):
        """Integrate UV event loop with Tkinter main loop"""
        def run_uv_loop():
            # Run UV loop in non-blocking mode
            self.loop.run(pyuv.UV_RUN_NOWAIT)
            # Schedule next UV loop iteration
            self.root.after(10, run_uv_loop)
        
        # Start UV loop integration
        self.root.after(10, run_uv_loop)
    
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
        """Get tmux sessions using UV process spawning"""
        sessions = []
        output_data = []
        
        def on_exit(proc, exit_status, term_signal):
            if exit_status == 0:
                output = ''.join(output_data)
                for line in output.strip().split('\n'):
                    if line:
                        session_name = line.split(':')[0]
                        sessions.append((session_name, line))
        
        def on_read(handle, data, error):
            if data:
                output_data.append(data.decode('utf-8'))
        
        # Create pipes for stdout
        stdout_pipe = pyuv.Pipe(self.loop)
        
        # Prepare stdio containers
        stdio = []
        stdio.append(pyuv.StdIO(flags=pyuv.UV_IGNORE))  # stdin
        stdio.append(pyuv.StdIO(stream=stdout_pipe, flags=pyuv.UV_CREATE_PIPE | pyuv.UV_WRITABLE_PIPE))  # stdout
        stdio.append(pyuv.StdIO(flags=pyuv.UV_IGNORE))  # stderr
        
        # Spawn process
        proc = pyuv.Process(self.loop)
        proc.spawn(
            file="tmux",
            args=["tmux", "list-sessions"],
            stdio=stdio,
            exit_callback=on_exit
        )
        
        # Start reading from stdout
        stdout_pipe.start_read(on_read)
        
        # Run the loop to complete the operation
        self.loop.run(pyuv.UV_RUN_DEFAULT)
        
        return sessions
    
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
    
    def send_message_to_session_uv(self, session_name, message, callback=None):
        """Send message to tmux session using UV process spawning"""
        def on_exit(proc, exit_status, term_signal):
            if callback:
                callback(exit_status == 0)
        
        # First send the message
        proc1 = pyuv.Process(self.loop)
        proc1.spawn(
            file="tmux",
            args=["tmux", "send-keys", "-t", session_name, message],
            exit_callback=lambda p, s, t: None
        )
        
        # Then send Enter key
        proc2 = pyuv.Process(self.loop)
        proc2.spawn(
            file="tmux",
            args=["tmux", "send-keys", "-t", session_name, "C-m"],
            exit_callback=on_exit
        )
    
    def send_once(self):
        session_name = self.get_selected_session()
        if not session_name:
            return
        
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message:
            messagebox.showwarning("Warning", "Please enter a message to send")
            return
        
        def on_sent(success):
            if success:
                self.status_label.config(text=f"Message sent to '{session_name}'")
            else:
                messagebox.showerror("Error", f"Failed to send message to session '{session_name}'")
        
        self.send_message_to_session_uv(session_name, message, on_sent)
    
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
        
        self.start_timer_btn.config(state="disabled")
        self.stop_timer_btn.config(state="normal")
        self.send_once_btn.config(state="disabled")
        
        def timer_callback(timer_handle):
            self.send_message_to_session_uv(session_name, message)
            self.status_label.config(
                text=f"Timer active - Last sent to '{session_name}' at {time.strftime('%H:%M:%S')}"
            )
        
        # Create and start UV timer
        self.timer_handle = pyuv.Timer(self.loop)
        self.timer_handle.start(timer_callback, interval, interval)
        
        self.status_label.config(text=f"Timer started - sending every {interval}s to '{session_name}'")
    
    def stop_timer(self):
        if self.timer_handle:
            self.timer_handle.stop()
            self.timer_handle = None
        
        self.start_timer_btn.config(state="normal")
        self.stop_timer_btn.config(state="disabled")
        self.send_once_btn.config(state="normal")
        self.status_label.config(text="Timer stopped")
    
    def send_exit_continue_sequence_uv(self, session_name, callback=None):
        """Send exit/continue sequence using UV"""
        sequence_step = [0]
        
        def next_step(timer_handle=None):
            step = sequence_step[0]
            
            if step < 5:
                # Send Ctrl+C
                proc = pyuv.Process(self.loop)
                proc.spawn(
                    file="tmux",
                    args=["tmux", "send-keys", "-t", session_name, "C-c"],
                    exit_callback=lambda p, s, t: None
                )
                sequence_step[0] += 1
                
                # Schedule next Ctrl+C after 200ms
                timer = pyuv.Timer(self.loop)
                timer.start(next_step, 0.2, 0)
                
            elif step == 5:
                # Wait 1 second then send mullvad reconnect
                sequence_step[0] += 1
                timer = pyuv.Timer(self.loop)
                timer.start(next_step, 1.0, 0)
                
            elif step == 6:
                # Send mullvad reconnect
                proc1 = pyuv.Process(self.loop)
                proc1.spawn(
                    file="tmux",
                    args=["tmux", "send-keys", "-t", session_name, "mullvad reconnect"],
                    exit_callback=lambda p, s, t: None
                )
                
                proc2 = pyuv.Process(self.loop)
                proc2.spawn(
                    file="tmux",
                    args=["tmux", "send-keys", "-t", session_name, "Enter"],
                    exit_callback=lambda p, s, t: None
                )
                
                sequence_step[0] += 1
                # Wait 3 seconds for mullvad to reconnect
                timer = pyuv.Timer(self.loop)
                timer.start(next_step, 3.0, 0)
                
            elif step == 7:
                # Send claudex -c
                proc1 = pyuv.Process(self.loop)
                proc1.spawn(
                    file="tmux",
                    args=["tmux", "send-keys", "-t", session_name, "claudex -c"],
                    exit_callback=lambda p, s, t: None
                )
                
                proc2 = pyuv.Process(self.loop)
                proc2.spawn(
                    file="tmux",
                    args=["tmux", "send-keys", "-t", session_name, "Enter"],
                    exit_callback=lambda p, s, t: None
                )
                
                if callback:
                    callback(True)
        
        # Start the sequence
        next_step()
    
    def start_auto_cycle(self):
        session_name = self.get_selected_session()
        if not session_name:
            return
        
        self.start_auto_btn.config(state="disabled")
        self.stop_auto_btn.config(state="normal")
        self.start_timer_btn.config(state="disabled")
        self.send_once_btn.config(state="disabled")
        
        def auto_cycle_callback(timer_handle=None):
            self.send_exit_continue_sequence_uv(session_name)
            self.status_label.config(
                text=f"Auto cycle active - Last sequence sent to '{session_name}' at {time.strftime('%H:%M:%S')}"
            )
        
        # If first launch, start immediately
        if self.first_launch:
            self.first_launch = False
            auto_cycle_callback()
        
        # Create and start UV timer for 4-minute intervals
        self.auto_cycle_handle = pyuv.Timer(self.loop)
        self.auto_cycle_handle.start(auto_cycle_callback, 240.0, 240.0)  # 240 seconds = 4 minutes
        
        self.status_label.config(text=f"Auto cycle started - Ctrl+C spam + mullvad reconnect + claudex -c every 4 minutes to '{session_name}'")
    
    def stop_auto_cycle(self):
        if self.auto_cycle_handle:
            self.auto_cycle_handle.stop()
            self.auto_cycle_handle = None
        
        self.start_auto_btn.config(state="normal")
        self.stop_auto_btn.config(state="disabled")
        self.start_timer_btn.config(state="normal")
        self.send_once_btn.config(state="normal")
        self.status_label.config(text="Auto cycle stopped")

def main():
    root = tk.Tk()
    app = TmuxMessengerUV(root)
    
    def on_closing():
        if app.timer_handle:
            app.stop_timer()
        if app.auto_cycle_handle:
            app.stop_auto_cycle()
        # Stop UV loop
        app.loop.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_closing()

if __name__ == "__main__":
    main()