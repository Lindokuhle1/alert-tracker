"""
UI module for Battery Alert Manager
Tkinter-based desktop interface with tabbed views and alert management
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import logging
from datetime import datetime
from typing import Optional, Callable, List, Dict
import threading
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

logger = logging.getLogger(__name__)


class AlertManagerUI:
    """
    Main UI class for Battery Alert Manager.
    Manages tabbed interface, treeviews, and user interactions.
    """
    
    # Color scheme
    COLOR_ACTIVE = "#ffcccc"  # Light red
    COLOR_CLEARED = "#ccffcc"  # Light green
    COLOR_CRITICAL = "#cc0000"  # Dark red
    
    def __init__(
        self, 
        root: tk.Tk,
        add_alert_callback: Callable,
        import_csv_callback: Callable,
        update_notes_callback: Callable,   # now expects (alert_id, notes, priority)
        update_status_callback: Callable,
        archive_callback: Callable,
        unarchive_callback: Callable,
        refresh_callback: Callable,
        export_callback: Callable,
        telegram_config_callback: Callable,
        mark_critical_callback: Callable,
        unmark_critical_callback: Callable
    ):
        """
        Initialize UI.
        
        Args:
            root: Tkinter root window
            add_alert_callback: Function to add new alert
            update_notes_callback: Function to update alert notes
            archive_callback: Function to archive alert
            unarchive_callback: Function to unarchive alert
            refresh_callback: Function to refresh data
            export_callback: Function to export data
            telegram_config_callback: Function to configure Telegram
            mark_critical_callback: Function to mark alert as critical
            unmark_critical_callback: Function to unmark alert as critical
        """
        self.root = root
        self.add_alert_callback = add_alert_callback
        self.import_csv_callback = import_csv_callback
        self.update_notes_callback = update_notes_callback
        self.update_status_callback = update_status_callback
        self.archive_callback = archive_callback
        self.unarchive_callback = unarchive_callback
        self.refresh_callback = refresh_callback
        self.export_callback = export_callback
        self.telegram_config_callback = telegram_config_callback
        self.mark_critical_callback = mark_critical_callback
        self.unmark_critical_callback = unmark_critical_callback
        
        self.setup_ui()
        logger.info("UI initialized")
    
    def setup_ui(self):
        """Set up main UI components."""
        self.root.title("Battery Alert Manager - Professional Edition")
        self.root.geometry("1400x800")
        
        # Configure root grid
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create top toolbar
        self._create_toolbar()
        
        # Create notebook with tabs
        self._create_notebook()
        
        # Create status bar
        self._create_status_bar()
        
        # Style configuration
        self._configure_styles()
    
    def _configure_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure treeview
        style.configure(
            "Treeview",
            background="white",
            foreground="black",
            rowheight=25,
            fieldbackground="white"
        )
        style.map('Treeview', background=[('selected', '#0078d7')])
        
        # Configure treeview heading
        style.configure(
            "Treeview.Heading",
            font=('Arial', 10, 'bold'),
            background="#f0f0f0",
            foreground="black"
        )
    
    def _create_toolbar(self):
        """Create top toolbar with buttons."""
        toolbar = ttk.Frame(self.root, padding="5")
        toolbar.grid(row=0, column=0, sticky="ew")
        
        # Manual alert entry button
        ttk.Button(
            toolbar,
            text="➕ Add Alert",
            command=self._show_add_alert_dialog
        ).pack(side=tk.LEFT, padx=2)
        
        # Edit priority button
        ttk.Button(
            toolbar,
            text="🔧 Edit Priority",
            command=self._edit_priority
        ).pack(side=tk.LEFT, padx=2)
        
        # Edit notes button
        ttk.Button(
            toolbar,
            text="📝 Edit Notes",
            command=self._edit_notes
        ).pack(side=tk.LEFT, padx=2)

        # Change status button
        ttk.Button(
            toolbar,
            text="🔁 Change Status",
            command=self._change_status
        ).pack(side=tk.LEFT, padx=2)
        
        # Archive button
        ttk.Button(
            toolbar,
            text="📦 Archive",
            command=self._archive_selected
        ).pack(side=tk.LEFT, padx=2)
        
        # Unarchive button
        ttk.Button(
            toolbar,
            text="↩️ Unarchive",
            command=self._unarchive_selected
        ).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=5
        )
        
        # Mark as Critical button
        ttk.Button(
            toolbar,
            text="⚠️ Mark Critical",
            command=self._mark_critical
        ).pack(side=tk.LEFT, padx=2)
        
        # Unmark as Critical button
        ttk.Button(
            toolbar,
            text="✓ Unmark Critical",
            command=self._unmark_critical
        ).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=5
        )
        
        # Refresh button
        ttk.Button(
            toolbar,
            text="🔄 Refresh",
            command=self.refresh_callback
        ).pack(side=tk.LEFT, padx=2)
        
        # Export button
        ttk.Button(
            toolbar,
            text="📊 Export to Excel",
            command=self._export_alerts
        ).pack(side=tk.LEFT, padx=2)
        
        # Import CSV button
        ttk.Button(
            toolbar,
            text="📁 Import CSV",
            command=self._show_import_csv_dialog
        ).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=5
        )
        
        # Telegram config button
        ttk.Button(
            toolbar,
            text="⚙️ Telegram Settings",
            command=self._show_telegram_config
        ).pack(side=tk.LEFT, padx=2)
    
    def _create_notebook(self):
        """Create tabbed notebook interface."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Tab 1: Main Dashboard
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="📊 Main Dashboard")
        self._create_main_dashboard(self.main_tab)
        
        # Tab 2: Critical Alerts
        self.critical_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.critical_tab, text="🔴 Critical Alerts")
        self._create_critical_alerts(self.critical_tab)
        
        # Tab 3: Archived Alerts
        self.archived_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.archived_tab, text="📦 Archived Alerts")
        self._create_archived_alerts(self.archived_tab)
    
    def _create_treeview(self, parent, columns: Dict[str, int]) -> ttk.Treeview:
        """
        Create a treeview with scrollbars.
        
        Args:
            parent: Parent widget
            columns: Dictionary of column names and widths
            
        Returns:
            Treeview widget
        """
        # Frame for treeview and scrollbars
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        
        # Treeview
        tree = ttk.Treeview(
            frame,
            columns=list(columns.keys()),
            show='tree headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Configure columns
        tree.column("#0", width=0, stretch=tk.NO)  # Hide tree column
        
        for col_name, width in columns.items():
            tree.column(col_name, width=width, anchor=tk.W)
            tree.heading(col_name, text=col_name, anchor=tk.W)
        
        return tree
    
    def _create_main_dashboard(self, parent):
        """Create main dashboard tab."""
        columns = {
            "Alert ID": 80,
            "Serial Number": 150,
            "Fault Type": 200,
            "Priority": 80,
            "Status": 100,
            "Occurred At": 180,
            "Count": 80,
            "Notes": 300
        }
        
        self.main_tree = self._create_treeview(parent, columns)
        
        # Bind double-click to edit notes
        self.main_tree.bind("<Double-1>", lambda e: self._edit_notes())
    
    def _create_critical_alerts(self, parent):
        """Create critical alerts tab."""
        # Warning label
        warning = ttk.Label(
            parent,
            text="⚠️ CRITICAL ALERTS - Status: ACTIVE & Re-occurrence Count ≥ 5",
            font=('Arial', 12, 'bold'),
            foreground="red"
        )
        warning.pack(pady=10)
        
        columns = {
            "Alert ID": 80,
            "Serial Number": 150,
            "Fault Type": 200,
            "Priority": 80,
            "Status": 100,
            "Occurred At": 180,
            "Count": 80,
            "Notes": 300
        }
        
        self.critical_tree = self._create_treeview(parent, columns)
        self.critical_tree.bind("<Double-1>", lambda e: self._edit_notes())
    
    def _create_archived_alerts(self, parent):
        """Create archived alerts tab."""
        columns = {
            "Alert ID": 80,
            "Serial Number": 150,
            "Fault Type": 200,
            "Priority": 80,
            "Status": 100,
            "Archived At": 180,
            "Count": 80,
            "Resolution": 300
        }
        
        self.archived_tree = self._create_treeview(parent, columns)
        self.archived_tree.bind("<Double-1>", lambda e: self._show_archived_details())
    
    def _create_status_bar(self):
        """Create bottom status bar."""
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding="2")
        status_frame.grid(row=2, column=0, sticky="ew")
        
        # Status label
        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Telegram status
        self.telegram_status_label = ttk.Label(
            status_frame,
            text="Telegram: Not connected",
            anchor=tk.E
        )
        self.telegram_status_label.pack(side=tk.RIGHT, padx=10)
        
        # Alert count
        self.count_label = ttk.Label(
            status_frame,
            text="Alerts: 0",
            anchor=tk.E
        )
        self.count_label.pack(side=tk.RIGHT, padx=10)
    
    def update_status(self, message: str):
        """Update status bar message."""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def update_telegram_status(self, status: str):
        """Update Telegram connection status."""
        self.telegram_status_label.config(text=f"Telegram: {status}")
        self.root.update_idletasks()
    
    def populate_main_dashboard(self, alerts: List[Dict]):
        """
        Populate main dashboard with alerts.
        
        Args:
            alerts: List of alert dictionaries
        """
        self._populate_tree(self.main_tree, alerts, show_resolution=False)
        self.count_label.config(text=f"Alerts: {len(alerts)}")
    
    def populate_critical_alerts(self, alerts: List[Dict]):
        """
        Populate critical alerts tab.
        
        Args:
            alerts: List of critical alert dictionaries
        """
        self._populate_tree(self.critical_tree, alerts, show_resolution=False)
    
    def populate_archived_alerts(self, alerts: List[Dict]):
        """
        Populate archived alerts tab.
        
        Args:
            alerts: List of archived alert dictionaries
        """
        self._populate_tree(self.archived_tree, alerts, show_resolution=True)
    
    def _populate_tree(
        self, 
        tree: ttk.Treeview, 
        alerts: List[Dict], 
        show_resolution: bool = False
    ):
        """
        Populate a treeview with alert data.
        
        Args:
            tree: Treeview widget
            alerts: List of alert dictionaries
            show_resolution: Whether to show resolution column
        """
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Insert alerts
        for alert in alerts:
            alert_id = alert['AlertId']
            is_critical = (
                alert['Status'] == 'ACTIVE' and 
                alert.get('ReOccurrenceCount', 0) >= 5
            )
            
            if show_resolution:
                # Archived view
                values = (
                    alert_id,
                    alert['SerialNumber'],
                    alert['FaultName'],
                    alert.get('Priority','Mid'),
                    alert['Status'],
                    self._format_datetime(alert.get('ArchivedAt', '')),
                    alert.get('ReOccurrenceCount', 1),
                    alert.get('Resolution', '')[:50]
                )
            else:
                # Main/Critical view
                values = (
                    alert_id,
                    alert['SerialNumber'],
                    alert['FaultName'],
                    alert.get('Priority','Mid'),
                    alert['Status'],
                    self._format_datetime(alert.get('OccurredAt', '')),
                    alert.get('ReOccurrenceCount', 1),
                    (alert.get('Notes', '') or '')[:50]
                )
            item = tree.insert("", tk.END, values=values, tags=(alert_id,))
            
            # Apply color coding
            if is_critical:
                tree.item(item, tags=(alert_id, 'critical'))
            elif alert['Status'] == 'ACTIVE':
                tree.item(item, tags=(alert_id, 'active'))
            elif alert['Status'] == 'CLEARED':
                tree.item(item, tags=(alert_id, 'cleared'))
        
        # Configure tags for colors
        tree.tag_configure('active', background=self.COLOR_ACTIVE)
        tree.tag_configure('cleared', background=self.COLOR_CLEARED)
        tree.tag_configure(
            'critical', 
            background=self.COLOR_CRITICAL, 
            foreground='white',
            font=('Arial', 10, 'bold')
        )
    
    def _format_datetime(self, dt_string: str) -> str:
        """Format datetime string for display."""
        if not dt_string:
            return ""
        
        try:
            dt = datetime.fromisoformat(dt_string.replace(' ', 'T'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(dt_string)
    
    def _show_add_alert_dialog(self):
        """Show dialog to manually add an alert."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Manual Alert")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Serial Number
        ttk.Label(dialog, text="Serial Number:").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5
        )
        serial_entry = ttk.Entry(dialog, width=40)
        serial_entry.grid(row=0, column=1, padx=10, pady=5)
        serial_entry.focus()
        
        # Fault Type
        ttk.Label(dialog, text="Fault Type:").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5
        )
        fault_entry = ttk.Entry(dialog, width=40)
        fault_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Status
        ttk.Label(dialog, text="Status:").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5
        )
        status_var = tk.StringVar(value="ACTIVE")
        status_combo = ttk.Combobox(
            dialog,
            textvariable=status_var,
            values=["ACTIVE", "CLEARED"],
            state="readonly",
            width=37
        )
        status_combo.grid(row=2, column=1, padx=10, pady=5)
        
        # Priority
        ttk.Label(dialog, text="Priority:").grid(
            row=3, column=0, sticky=tk.W, padx=10, pady=5
        )
        priority_var = tk.StringVar(value="Mid")
        priority_combo = ttk.Combobox(
            dialog,
            textvariable=priority_var,
            values=["High", "Mid", "Low"],
            state="readonly",
            width=37
        )
        priority_combo.grid(row=3, column=1, padx=10, pady=5)
        
        # Notes
        ttk.Label(dialog, text="Notes:").grid(
            row=4, column=0, sticky=tk.NW, padx=10, pady=5
        )
        notes_text = tk.Text(dialog, width=40, height=6)
        notes_text.grid(row=4, column=1, padx=10, pady=5)
        
        def submit():
            serial = serial_entry.get().strip()
            fault = fault_entry.get().strip()
            status = status_var.get()
            priority = priority_var.get()
            notes = notes_text.get("1.0", tk.END).strip()
            
            if not serial or not fault:
                messagebox.showerror(
                    "Validation Error",
                    "Serial Number and Fault Type are required!"
                )
                return
            
            self.add_alert_callback(serial, fault, status, notes, priority)
            dialog.destroy()
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Add Alert", command=submit).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )

    
    def _get_selected_alert_id(self) -> Optional[int]:
        """Get selected alert ID from current tab."""
        current_tab = self.notebook.select()
        
        if current_tab == str(self.main_tab):
            tree = self.main_tree
        elif current_tab == str(self.critical_tab):
            tree = self.critical_tree
        elif current_tab == str(self.archived_tab):
            tree = self.archived_tree
        else:
            return None
        
        selection = tree.selection()
        if not selection:
            return None
        
        item = selection[0]
        values = tree.item(item, 'values')
        return int(values[0]) if values else None
    
    def _edit_notes(self):
        """Edit notes + priority for selected alert."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        
        # fetch current data from the tree
        current = None
        for tree in (self.main_tree, self.critical_tree, self.archived_tree):
            try:
                item = tree.selection()[0]
                vals = tree.item(item, 'values')
                if int(vals[0]) == alert_id:
                    current = vals
                    break
            except Exception:
                continue
        current_notes = ''
        current_priority = 'Mid'
        if current:
            # notes in 7th column for main/critical
            current_notes = current[7] if len(current) > 7 else ''
            current_priority = current[3] if len(current) > 3 else 'Mid'

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Alert {alert_id}")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Priority:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        prio_var = tk.StringVar(value=current_priority)
        prio_combo = ttk.Combobox(dialog, textvariable=prio_var, values=["High","Mid","Low"], state="readonly", width=37)
        prio_combo.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Notes:").grid(row=1, column=0, sticky=tk.NW, padx=10, pady=5)
        notes_text = tk.Text(dialog, width=40, height=10)
        notes_text.grid(row=1, column=1, padx=10, pady=5)
        notes_text.insert("1.0", current_notes)

        def submit():
            notes = notes_text.get("1.0", tk.END).strip()
            priority = prio_var.get()
            self.update_notes_callback(alert_id, notes, priority)
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _archive_selected(self):
        """Archive selected alert."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        
        resolution = simpledialog.askstring(
            "Archive Alert",
            f"Enter resolution for Alert ID {alert_id}:",
            parent=self.root
        )
        
        if resolution:
            self.archive_callback(alert_id, resolution)

    def _change_status(self):
        """Change status of the selected alert."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        
        # Ask for new status
        status = simpledialog.askstring(
            "Change Status",
            f"Enter new status for Alert ID {alert_id} (ACTIVE/CLEARED):",
            parent=self.root
        )
        
        if status:
            status = status.strip().upper()
            if status not in ("ACTIVE", "CLEARED"):
                messagebox.showerror("Invalid Status", "Status must be ACTIVE or CLEARED.")
                return
            self.update_status_callback(alert_id, status)
    
    def _unarchive_selected(self):
        """Unarchive selected alert."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        
        if messagebox.askyesno(
            "Unarchive Alert",
            f"Unarchive Alert ID {alert_id}?"
        ):
            self.unarchive_callback(alert_id)
    
    def _mark_critical(self):
        """Mark selected alert as critical."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        
        if messagebox.askyesno(
            "Mark as Critical",
            f"Mark Alert ID {alert_id} as critical?\n\n"
            "This will move the alert to the Critical Alerts tab."
        ):
            self.mark_critical_callback(alert_id)
    
    def _unmark_critical(self):
        """Remove critical marking from selected alert."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        
        if messagebox.askyesno(
            "Unmark Critical",
            f"Remove critical marking from Alert ID {alert_id}?\n\n"
            "The alert will move back to the Main Dashboard."
        ):
            self.unmark_critical_callback(alert_id)
    
    def _show_archived_details(self):
        """Show details of archived alert."""
        alert_id = self._get_selected_alert_id()
        
        if not alert_id:
            return
        
        # This would fetch and display full alert details
        # For now, just show a message
        messagebox.showinfo(
            "Alert Details",
            f"Viewing details for Alert ID {alert_id}"
        )
    
    def _export_alerts(self):
        """Export current view to Excel."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"battery_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if file_path:
            self.export_callback(file_path)
    
    def _show_import_csv_dialog(self):
        """Open file dialog and call import callback."""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")]
        )
        if file_path:
            try:
                self.import_csv_callback(file_path)
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import CSV: {e}")

    def _edit_priority(self):
        """Prompt user to change selected alert's priority only."""
        alert_id = self._get_selected_alert_id()
        if not alert_id:
            messagebox.showwarning("No Selection", "Please select an alert first.")
            return
        # ask for new priority
        priority = simpledialog.askstring("Edit Priority",
                                          "Enter new priority (High/Mid/Low):",
                                          parent=self.root)
        if priority:
            priority = priority.strip().capitalize()
            if priority not in ("High","Mid","Low"):
                messagebox.showerror("Invalid", "Priority must be High, Mid or Low")
                return
            self.update_notes_callback(alert_id, '', priority)

    def _show_telegram_config(self):
        """Show Telegram configuration dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Telegram Configuration")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # API ID
        ttk.Label(dialog, text="API ID:").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5
        )
        api_id_entry = ttk.Entry(dialog, width=40)
        api_id_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # API Hash
        ttk.Label(dialog, text="API Hash:").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5
        )
        api_hash_entry = ttk.Entry(dialog, width=40)
        api_hash_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Phone
        ttk.Label(dialog, text="Phone Number:").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5
        )
        phone_entry = ttk.Entry(dialog, width=40)
        phone_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Channel
        ttk.Label(dialog, text="Channel Username:").grid(
            row=3, column=0, sticky=tk.W, padx=10, pady=5
        )
        channel_entry = ttk.Entry(dialog, width=40)
        channel_entry.grid(row=3, column=1, padx=10, pady=5)
        
        # Help text
        help_text = ttk.Label(
            dialog,
            text=("Enter the exact channel username (e.g. @MyChannel) or ID. "
                  "Spaces are not allowed. You can also paste a link."),
            font=('Arial', 8),
            foreground="gray",
            wraplength=400,
            justify=tk.LEFT
        )
        help_text.grid(row=4, column=0, columnspan=2, pady=5)
        
        def save_config():
            config = {
                'api_id': api_id_entry.get().strip(),
                'api_hash': api_hash_entry.get().strip(),
                'phone': phone_entry.get().strip(),
                'channel': channel_entry.get().strip()
            }
            
            if not all(config.values()):
                messagebox.showerror(
                    "Validation Error",
                    "All fields are required!"
                )
                return
            
            try:
                config['api_id'] = int(config['api_id'])
            except ValueError:
                messagebox.showerror(
                    "Validation Error",
                    "API ID must be a number!"
                )
                return
            
            self.telegram_config_callback(config)
            dialog.destroy()
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Save & Connect", command=save_config).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )
