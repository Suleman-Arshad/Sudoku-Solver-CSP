import tkinter as tk
from tkinter import ttk, messagebox
import time
import copy
import os

class SudokuCSP:
    def __init__(self, grid: list[list[int]]):
        self.variables: list[tuple[int, int]] = [
            (r, c) for r in range(9) for c in range(9)
        ]
        # domains[var] = mutable set of currently legal values
        self.domains: dict[tuple[int, int], set[int]] = {}
        for r in range(9):
            for c in range(9):
                if grid[r][c] != 0:
                    self.domains[(r, c)] = {grid[r][c]}
                else:
                    self.domains[(r, c)] = set(range(1, 10))
        # Build neighbour map once (used by both AC-3 and backtracking)
        self.neighbors: dict[tuple[int, int], set[tuple[int, int]]] = {
            v: set() for v in self.variables
        }
        self._build_neighbors()

    # Neighbour construction
    def _build_neighbors(self) -> None:
        for r in range(9):
            for c in range(9):
                cell = (r, c)
                peers: set[tuple[int, int]] = set()
                # Same row
                for cc in range(9):
                    if cc != c:
                        peers.add((r, cc))
                # Same column
                for rr in range(9):
                    if rr != r:
                        peers.add((rr, c))
                # Same 3×3 box
                box_r, box_c = (r // 3) * 3, (c // 3) * 3
                for rr in range(box_r, box_r + 3):
                    for cc in range(box_c, box_c + 3):
                        if (rr, cc) != cell:
                            peers.add((rr, cc))
                self.neighbors[cell] = peers

    # Constraint check
    @staticmethod
    def constraint_satisfied(val_i: int, val_j: int) -> bool:
        return val_i != val_j

# AC-3 ALGORITHM 
def revise(csp: SudokuCSP, xi: tuple[int, int], xj: tuple[int, int]) -> bool:
    revised = False
    for x in set(csp.domains[xi]):          # iterate over a snapshot
        # Is there at least one y in Dj consistent with x?
        if not any(
            SudokuCSP.constraint_satisfied(x, y)
            for y in csp.domains[xj]
        ):
            csp.domains[xi].discard(x)
            revised = True
    return revised

def ac3(csp: SudokuCSP) -> bool:
    # Initialise queue with ALL directed arcs (Xi, Xj) for every constraint
    queue: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for xi in csp.variables:
        for xj in csp.neighbors[xi]:
            queue.append((xi, xj))

    while queue:
        xi, xj = queue.pop(0)               # POP from front (FIFO)

        if revise(csp, xi, xj):
            if len(csp.domains[xi]) == 0:   # domain wipe-out → failure
                return False
            # Re-examine all arcs into Xi (except from Xj)
            for xk in csp.neighbors[xi] - {xj}:
                queue.append((xk, xi))

    return True

# BACKTRACKING SEARCH  
def select_unassigned_variable(
    assignment: dict[tuple[int, int], int],
    csp: SudokuCSP
) -> tuple[int, int] | None:
    for var in csp.variables:
        if var not in assignment:
            return var
    return None

def order_domain_values(
    var: tuple[int, int],
    assignment: dict[tuple[int, int], int],
    csp: SudokuCSP
) -> list[int]:
    return sorted(csp.domains[var])

def is_consistent(
    var: tuple[int, int],
    value: int,
    assignment: dict[tuple[int, int], int],
    csp: SudokuCSP
) -> bool:
    for neighbor in csp.neighbors[var]:
        if neighbor in assignment:
            if not SudokuCSP.constraint_satisfied(value, assignment[neighbor]):
                return False
    return True

def inference(
    csp: SudokuCSP,
    var: tuple[int, int],
    value: int
) -> dict[tuple[int, int], int] | None:
    return {}   # empty inferences — always succeeds

def backtrack(
    assignment: dict[tuple[int, int], int],
    csp: SudokuCSP
) -> dict[tuple[int, int], int] | None:
    # Base case: all 81 variables assigned
    if len(assignment) == len(csp.variables):
        return assignment
    var = select_unassigned_variable(assignment, csp)
    for value in order_domain_values(var, assignment, csp):
        if is_consistent(var, value, assignment, csp):
            assignment[var] = value
            inferences = inference(csp, var, value)
            if inferences is not None:          # always true here
                assignment.update(inferences)
                result = backtrack(assignment, csp)
                if result is not None:
                    return result
            # Remove var = value AND inferences from assignment
            del assignment[var]
            for inf_var in inferences:
                if inf_var in assignment:
                    del assignment[inf_var]
    return None     # failure

def backtracking_search(
    csp: SudokuCSP
) -> dict[tuple[int, int], int] | None:
    return backtrack({}, csp)

# SOLVER FACADE 
def solve(grid: list[list[int]], algorithm: str) -> tuple[list[list[int]] | None, float]:
    csp = SudokuCSP(copy.deepcopy(grid))
    start = time.perf_counter()
    if algorithm == "AC-3":
        success = ac3(csp)
        elapsed = time.perf_counter() - start
        if not success:
            return None, elapsed
        # After AC-3, check if each domain is a singleton (fully solved)
        solved = [[0] * 9 for _ in range(9)]
        for (r, c), domain in csp.domains.items():
            if len(domain) == 1:
                solved[r][c] = next(iter(domain))
            else:
                # AC-3 alone could not fully determine the value —
                # fall through to backtracking on the reduced domains.
                assignment: dict[tuple[int, int], int] = {}
                for v2, d2 in csp.domains.items():
                    if len(d2) == 1:
                        assignment[v2] = next(iter(d2))
                result = backtrack(assignment, csp)
                elapsed = time.perf_counter() - start
                if result is None:
                    return None, elapsed
                out = [[0] * 9 for _ in range(9)]
                for (rr, cc), val in result.items():
                    out[rr][cc] = val
                return out, elapsed
        return solved, elapsed
    else:  # Backtracking
        # Seed assignment with given (pre-filled) cells
        assignment: dict[tuple[int, int], int] = {}
        for r in range(9):
            for c in range(9):
                if grid[r][c] != 0:
                    assignment[(r, c)] = grid[r][c]
        result = backtrack(assignment, csp)
        elapsed = time.perf_counter() - start
        if result is None:
            return None, elapsed
        out = [[0] * 9 for _ in range(9)]
        for (r, c), val in result.items():
            out[r][c] = val
        return out, elapsed

# PUZZLE FILE PARSER  
def parse_puzzle_file(filepath: str) -> list[list[list[int]]]:
    puzzles: list[list[list[int]]] = []
    current: list[list[int]] = []
    with open(filepath, "r") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if line == "":
                if len(current) == 9:
                    puzzles.append(current)
                current = []
            else:
                if len(line) == 9 and line.isdigit():
                    current.append([int(ch) for ch in line])
    # Don't forget the last puzzle (no trailing blank line required)
    if len(current) == 9:
        puzzles.append(current)
    return puzzles

def load_puzzle(difficulty: str, puzzle_number: int) -> list[list[int]]:
    filename_map = {"Easy": "easy.txt", "Medium": "medium.txt", "Hard": "hard.txt"}
    filepath = filename_map[difficulty]
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Puzzle file '{filepath}' not found.\n"
            f"Please place easy.txt, medium.txt, and hard.txt "
            f"in the same directory as this script."
        )
    puzzles = parse_puzzle_file(filepath)
    if puzzle_number < 1 or puzzle_number > len(puzzles):
        raise ValueError(
            f"Puzzle {puzzle_number} does not exist in '{filepath}'. "
            f"Only {len(puzzles)} puzzle(s) found."
        )
    return puzzles[puzzle_number - 1]

# GUI — COLOUR PALETTE & CONSTANTS  
# Colour scheme 
BG_DARK         = "#0f0f1a"       # app background
BG_PANEL        = "#1a1a2e"       # sidebar panel
BG_CELL         = "#16213e"       # normal cell background
BG_CELL_GIVEN   = "#0d0d1a"       # given (pre-filled) cell
BG_CELL_HINT    = "#1a2e1a"       # hint reveal cell
BG_CELL_SOLVED  = "#0e2030"       # AI-solved cell
ACCENT          = "#e94560"       # primary accent (crimson)
ACCENT2         = "#0f3460"       # secondary accent (deep blue)
ACCENT3         = "#533483"       # tertiary accent (purple)
TEXT_PRIMARY    = "#000000"       # main text
FRONT_TEXT      = "#ffffff"       # front-facing text (e.g. on buttons)
TEXT_SECONDARY  = "#8888aa"       # muted text
TEXT_GIVEN      = "#ffffff"       # given digit colour
TEXT_SOLVED     = "#4fc3f7"       # AI-solved digit colour
TEXT_HINT       = "#81c784"       # hint digit colour
TEXT_USER       = "#ffcc80"       # user-typed digit colour
BORDER_THIN     = "#2a2a4a"       # thin inter-cell border
HINT_BUTTON_BG  = "#ffcc80"       # hint button background
BORDER_THICK    = "#e94560"       # thick sub-grid border
BG_CELL_ERROR   = "#3a0a0a"       # invalid user entry — red tint background
TEXT_ERROR      = "#ff4444"       # invalid user entry — bright red digit

# Fonts 
FONT_CELL_GIVEN  = ("Courier New", 18, "bold")
FONT_CELL_SOLVED = ("Courier New", 18, "bold")
FONT_CELL_USER   = ("Courier New", 16)
FONT_CELL_HINT   = ("Courier New", 18, "bold")
FONT_HEADER      = ("Courier New", 22, "bold")
FONT_LABEL       = ("Courier New", 11)
FONT_BUTTON      = ("Courier New", 12, "bold")
FONT_SPLASH_TITLE = ("Courier New", 32, "bold")
FONT_SPLASH_SUB   = ("Courier New", 14)

CELL_SIZE = 56   # pixels per cell

# SPLASH SCREEN 
class SplashScreen(tk.Frame):
    def __init__(self, master: tk.Tk, on_select):
        super().__init__(master, bg=BG_DARK)
        self.on_select = on_select
        self._build()
    def _build(self) -> None:
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Decorative horizontal bar
        tk.Frame(self, bg=ACCENT, height=4).pack(fill="x", pady=(0, 0))
        # Title
        tk.Label(
            self,
            text="SUDOKU  SOLVER",
            font=FONT_SPLASH_TITLE,
            bg=BG_DARK,
            fg=ACCENT,
        ).pack(pady=(60, 8))

        tk.Label(
            self,
            text="CSP  ·  AC-3  ·  Backtracking",
            font=FONT_SPLASH_SUB,
            bg=BG_DARK,
            fg=TEXT_SECONDARY,
        ).pack(pady=(0, 60))

        #  Separator 
        tk.Frame(self, bg=ACCENT2, height=1).pack(fill="x", padx=80, pady=(0, 50))

        tk.Label(
            self,
            text="Select a Mode to Begin",
            font=FONT_LABEL,
            bg=BG_DARK,
            fg=TEXT_SECONDARY,
        ).pack(pady=(0, 28))

        # Mode buttons
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack()

        self._mode_btn(btn_frame, "🤖  AI Mode", "AI",
                       "Let the algorithm solve the puzzle.").grid(
            row=0, column=0, padx=8, pady=10)

        self._mode_btn(btn_frame, "✏️  User Mode", "User",
                       "Solve it yourself — get hints when stuck.").grid(
            row=1, column=0, padx=8, pady=10)

        # Bottom bar
        tk.Frame(self, bg=ACCENT, height=4).pack(side="bottom", fill="x")

    def _mode_btn(
        self,
        parent: tk.Frame,
        label: str,
        mode: str,
        subtitle: str
    ) -> tk.Frame:
        outer = tk.Frame(parent, bg=ACCENT2, bd=0, relief="flat")
        inner = tk.Frame(outer, bg=BG_PANEL, padx=30, pady=20)
        inner.pack(padx=2, pady=2)

        tk.Label(
            inner, text=label,
            font=FONT_BUTTON,
            bg=BG_PANEL, fg=FRONT_TEXT,
            cursor="hand2",
        ).pack()

        tk.Label(
            inner, text=subtitle,
            font=("Courier New", 9),
            bg=BG_PANEL, fg=TEXT_SECONDARY,
            cursor="hand2",
        ).pack(pady=(4, 0))

        # Bind entire frame + children
        for widget in (outer, inner, *inner.winfo_children()):
            widget.bind("<Button-1>", lambda e, m=mode: self._select(m))
            widget.bind("<Enter>",    lambda e, f=inner: f.config(bg=ACCENT2))
            widget.bind("<Leave>",    lambda e, f=inner: f.config(bg=BG_PANEL))

        return outer

    def _select(self, mode: str) -> None:
        self.place_forget()
        self.on_select(mode)

# MAIN APPLICATION WINDOW  
class SudokuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sudoku Solver — CSP")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)

        self.mode: str | None = None              # "AI" or "User"
        self.current_grid: list[list[int]] = []   # original puzzle (0 = empty)
        self.given_cells: set[tuple[int, int]] = set()

        # Show splash first
        self.splash = SplashScreen(self, self._launch_main)
        # Size window to fit splash
        self.geometry("740x540")
        self._center()

    def _launch_main(self, mode: str) -> None:
        self.mode = mode
        # Resize for main layout
        self.geometry("960x620")
        self._center()
        self._build_main_ui()

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_main_ui(self) -> None:
        # Top bar
        top_bar = tk.Frame(self, bg=ACCENT, height=4)
        top_bar.pack(fill="x")

        header_frame = tk.Frame(self, bg=BG_DARK, pady=10)
        header_frame.pack(fill="x", padx=20)

        mode_tag = "[ AI MODE ]" if self.mode == "AI" else "[ USER MODE ]"
        tk.Label(
            header_frame,
            text=f"SUDOKU SOLVER   {mode_tag}",
            font=FONT_HEADER,
            bg=BG_DARK, fg=ACCENT,
        ).pack(side="left")

        # Back button
        tk.Button(
            header_frame,
            text="⟵ Back",
            font=("Courier New", 10),
            bg=ACCENT2, fg=FRONT_TEXT,
            activebackground=ACCENT, activeforeground=FRONT_TEXT,
            relief="flat", bd=0, padx=10, pady=4,
            cursor="hand2",
            command=self._go_back,
        ).pack(side="right")

        tk.Frame(self, bg=ACCENT2, height=1).pack(fill="x", padx=20)

        # Content area 
        content = tk.Frame(self, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=20, pady=14)
        # Grid panel (left)
        self.grid_frame = tk.Frame(content, bg=BG_DARK)
        self.grid_frame.pack(side="left", anchor="n")
        # Sidebar (right)
        self.sidebar = tk.Frame(content, bg=BG_PANEL, padx=18, pady=18, width=270)
        self.sidebar.pack(side="right", fill="y", padx=(18, 0), anchor="n")
        self.sidebar.pack_propagate(False)
        self._build_grid()
        self._build_sidebar()
        # Bottom bar
        tk.Frame(self, bg=ACCENT, height=4).pack(side="bottom", fill="x")

    def _go_back(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self.geometry("740x540")
        self._center()
        self.splash = SplashScreen(self, self._launch_main)

    def _build_grid(self) -> None:
        self.cell_widgets: list[list] = [[None] * 9 for _ in range(9)]
        self.cell_vars: list[list[tk.StringVar | None]] = [
            [None] * 9 for _ in range(9)
        ]
        THIN = 1
        THICK = 3
        canvas_size = CELL_SIZE * 9 + THICK * 4 + THIN * 6
        self.canvas = tk.Canvas(
            self.grid_frame,
            width=canvas_size,
            height=canvas_size,
            bg=BORDER_THICK,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0)

        # Place cells into the canvas using a Frame per cell
        for r in range(9):
            for c in range(9):
                # Compute pixel position including border offsets
                bx = _border_offset(c)
                by = _border_offset(r)
                x = bx + c * CELL_SIZE
                y = by + r * CELL_SIZE

                cell_frame = tk.Frame(
                    self.canvas,
                    width=CELL_SIZE,
                    height=CELL_SIZE,
                    bg=BG_CELL_GIVEN,
                )
                self.canvas.create_window(x, y, window=cell_frame, anchor="nw",
                                          width=CELL_SIZE, height=CELL_SIZE)

                if self.mode == "User":
                    var = tk.StringVar()
                    self.cell_vars[r][c] = var
                    entry = tk.Entry(
                        cell_frame,
                        textvariable=var,
                        font=FONT_CELL_USER,
                        bg=BG_CELL,
                        fg=TEXT_USER,
                        insertbackground=ACCENT,
                        relief="flat",
                        justify="center",
                        width=2,
                        bd=0,
                    )
                    entry.place(relx=0.5, rely=0.5, anchor="center",
                                width=CELL_SIZE - 4, height=CELL_SIZE - 4)
                    # Validate: only single digit 1-9
                    entry.bind("<KeyRelease>", lambda e, rr=r, cc=c: self._validate_entry(rr, cc))
                    self.cell_widgets[r][c] = entry
                else:
                    lbl = tk.Label(
                        cell_frame,
                        text="",
                        font=FONT_CELL_GIVEN,
                        bg=BG_CELL,
                        fg=TEXT_GIVEN,
                        anchor="center",
                    )
                    lbl.place(relx=0.5, rely=0.5, anchor="center",
                              width=CELL_SIZE - 4, height=CELL_SIZE - 4)
                    self.cell_widgets[r][c] = lbl

    def _validate_entry(self, r: int, c: int) -> None:
        var  = self.cell_vars[r][c]
        val  = var.get()
        # Sanitise: keep only the last valid digit
        if val == "":
            # Cell cleared → reset to normal and re-check peers
            self.cell_widgets[r][c].config(fg=TEXT_USER, bg=BG_CELL)
            self._recheck_peers(r, c)
            return

        last = val[-1]
        if last.isdigit() and last != "0":
            var.set(last)
        else:
            var.set(val[:-1])          # strip the invalid character
            # Re-run with the corrected value (or empty string)
            self._validate_entry(r, c)
            return

        # Conflict check against all peers
        digit = int(var.get())
        conflict = self._has_conflict(r, c, digit)

        entry = self.cell_widgets[r][c]
        if conflict:
            entry.config(fg=TEXT_ERROR, bg=BG_CELL_ERROR)
        else:
            entry.config(fg=TEXT_USER,  bg=BG_CELL)

        # Re-evaluate peers — their conflict status may have changed
        self._recheck_peers(r, c)

    def _has_conflict(self, r: int, c: int, digit: int) -> bool:
        for pr, pc in self._peer_coords(r, c):
            peer_val = self._get_board_value(pr, pc)
            if peer_val == digit:
                return True
        return False

    def _peer_coords(self, r: int, c: int):
        for cc in range(9):
            if cc != c:
                yield r, cc
        for rr in range(9):
            if rr != r:
                yield rr, c
        br, bc = (r // 3) * 3, (c // 3) * 3
        for rr in range(br, br + 3):
            for cc in range(bc, bc + 3):
                if (rr, cc) != (r, c):
                    yield rr, cc

    def _get_board_value(self, r: int, c: int) -> int:
        if (r, c) in self.given_cells:
            return self.current_grid[r][c]
        return self._get_user_value(r, c)

    def _recheck_peers(self, r: int, c: int) -> None:
        seen: set[tuple[int, int]] = set()
        for pr, pc in self._peer_coords(r, c):
            if (pr, pc) in self.given_cells or (pr, pc) in seen:
                continue
            seen.add((pr, pc))
            peer_digit = self._get_user_value(pr, pc)
            if peer_digit == 0:
                continue    # empty — no need to recheck
            conflict = self._has_conflict(pr, pc, peer_digit)
            entry = self.cell_widgets[pr][pc]
            # Only touch cells that are in normal user or error state
            current_bg = entry.cget("bg")
            if current_bg in (BG_CELL, BG_CELL_ERROR):
                if conflict:
                    entry.config(fg=TEXT_ERROR, bg=BG_CELL_ERROR)
                else:
                    entry.config(fg=TEXT_USER,  bg=BG_CELL)

    # SIDEBAR CONSTRUCTION 
    def _build_sidebar(self) -> None:
        sb_container = self.sidebar 
        self.sb_canvas = tk.Canvas(sb_container, bg=BG_PANEL, highlightthickness=0)
        self.sb_scrollbar = ttk.Scrollbar(sb_container, orient="vertical", command=self.sb_canvas.yview)
        self.sb_content = tk.Frame(self.sb_canvas, bg=BG_PANEL)
        
        # Canvas configuration
        self.sb_canvas.create_window((0, 0), window=self.sb_content, anchor="nw", width=210)
        self.sb_canvas.configure(yscrollcommand=self.sb_scrollbar.set)

        # Layout for scrollbar and canvas
        self.sb_scrollbar.pack(side="right", fill="y")
        self.sb_canvas.pack(side="left", fill="both", expand=True)
        self.sb_content.bind("<Configure>", lambda e: self.sb_canvas.configure(scrollregion=self.sb_canvas.bbox("all")))
        
        # Mouse wheel support
        self.sb_canvas.bind_all("<MouseWheel>", lambda e: self.sb_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        # Now build the actual sidebar content inside self.sb_content
        sb = self.sb_content

        def section_label(text: str) -> None:
            tk.Label(sb, text=text, font=("Courier New", 9), bg=BG_PANEL, fg=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(14, 2))

        def styled_combo(parent, values, default_idx=0) -> ttk.Combobox:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure("Dark.TCombobox", fieldbackground=ACCENT2, background=ACCENT2, foreground=TEXT_PRIMARY,
                            selectbackground=ACCENT, selectforeground=TEXT_PRIMARY, arrowcolor=TEXT_PRIMARY)
            cb = ttk.Combobox(parent, values=values, state="readonly", style="Dark.TCombobox", font=("Courier New", 11))
            cb.current(default_idx)
            cb.pack(fill="x", padx=5)
            return cb

        # Title
        tk.Label(sb, text="CONTROLS", font=("Courier New", 13, "bold"), bg=BG_PANEL, fg=ACCENT).pack(fill="x")
        tk.Frame(sb, bg=ACCENT, height=2).pack(fill="x", pady=(4, 0))

        # Difficulty
        section_label("DIFFICULTY")
        self.difficulty_cb = styled_combo(sb, ["Easy", "Medium", "Hard"])
        self.difficulty_cb.bind("<<ComboboxSelected>>", self._on_setting_change)

        # Puzzle
        section_label("PUZZLE")
        self.puzzle_cb = styled_combo(sb, ["Puzzle 1", "Puzzle 2", "Puzzle 3", "Puzzle 4"])
        self.puzzle_cb.bind("<<ComboboxSelected>>", self._on_setting_change)

        # Algorithm
        section_label("ALGORITHM")
        self.algo_cb = styled_combo(sb, ["AC-3", "Backtracking"])

        # Separator
        tk.Frame(sb, bg=ACCENT2, height=1).pack(fill="x", pady=18)

        # Buttons
        self._action_btn(sb, "⊞  Load Puzzle", self._load_puzzle_action, FRONT_TEXT).pack(fill="x", pady=(0, 8), padx=5)
        self._action_btn(sb, "↺  Reset / Clear", self._reset_action, FRONT_TEXT).pack(fill="x", padx=5)
        
        tk.Frame(sb, bg=ACCENT2, height=1).pack(fill="x", pady=18)

        # Mode-specific buttons
        if self.mode == "AI":
            self._action_btn(sb, "▶  Solve", self._solve_action, FRONT_TEXT).pack(fill="x", padx=5)
            self.time_label = tk.Label(sb, text="Time Complexity:\n— not run yet —", font=("Courier New", 9),
                                      bg=BG_PANEL, fg=TEXT_SECONDARY, justify="left", wraplength=180)
            self.time_label.pack(fill="x", pady=(14, 10))
        else:
            self._action_btn(sb, "💡  Hint", self._hint_action, HINT_BUTTON_BG).pack(fill="x", padx=5)
            self._action_btn(sb, "✅  Complete", self._complete_action, "#81c784").pack(fill="x", pady=(10, 0), padx=5)
            
            self.hint_label = tk.Label(sb, text="Press Hint to reveal a cell.", font=("Courier New", 9),
                                      bg=BG_PANEL, fg=TEXT_SECONDARY, justify="left", wraplength=180)
            self.hint_label.pack(fill="x", pady=(14, 10))

    def _action_btn(
        self,
        parent: tk.Frame,
        text: str,
        command,
        bg_color: str
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            font=FONT_BUTTON,
            bg=bg_color, fg=TEXT_PRIMARY,
            activebackground=ACCENT, activeforeground=TEXT_PRIMARY,
            relief="flat", bd=0,
            padx=10, pady=10,
            cursor="hand2",
            command=command,
        )

    # GRID DISPLAY HELPERS
    def _set_cell(
        self,
        r: int, c: int,
        value: int,
        style: str = "given"
    ) -> None:
        text = str(value) if value != 0 else ""
        if self.mode == "AI":
            lbl = self.cell_widgets[r][c]
            if style == "given":
                lbl.config(text=text, fg=TEXT_GIVEN,
                           bg=BG_CELL_GIVEN, font=FONT_CELL_GIVEN)
            elif style == "solved":
                lbl.config(text=text, fg=TEXT_SOLVED,
                           bg=BG_CELL_SOLVED, font=FONT_CELL_SOLVED)
            else:
                lbl.config(text="", fg=TEXT_GIVEN,
                           bg=BG_CELL, font=FONT_CELL_GIVEN)
        else:  # User mode
            entry = self.cell_widgets[r][c]
            var = self.cell_vars[r][c]
            if style == "given":
                var.set(text)
                entry.config(
                    fg=TEXT_GIVEN, bg=BG_CELL_GIVEN,
                    font=FONT_CELL_GIVEN, state="disabled",
                    disabledforeground=TEXT_GIVEN,
                    disabledbackground=BG_CELL_GIVEN,
                )
            elif style == "hint":
                var.set(text)
                entry.config(
                    fg=TEXT_HINT, bg=BG_CELL_HINT,
                    font=FONT_CELL_HINT, state="disabled",
                    disabledforeground=TEXT_HINT,
                    disabledbackground=BG_CELL_HINT,
                )
            elif style == "empty":
                var.set("")
                entry.config(
                    fg=TEXT_USER, bg=BG_CELL,
                    font=FONT_CELL_USER, state="normal",
                )
            elif style == "error":
                var.set(text)
                entry.config(
                    fg=TEXT_ERROR, bg=BG_CELL_ERROR,
                    font=FONT_CELL_USER, state="normal",
                )
            else:
                pass

    def _display_puzzle(self, grid: list[list[int]]) -> None:
        self.current_grid = [row[:] for row in grid]
        self.given_cells = set()

        for r in range(9):
            for c in range(9):
                v = grid[r][c]
                if v != 0:
                    self.given_cells.add((r, c))
                    self._set_cell(r, c, v, "given")
                else:
                    self._set_cell(r, c, 0, "empty")

    def _display_solution(self, solved: list[list[int]]) -> None:
        # Overlay the solved values onto the grid (AI mode).
        for r in range(9):
            for c in range(9):
                if (r, c) not in self.given_cells:
                    self._set_cell(r, c, solved[r][c], "solved")

    # ACTION HANDLERS 
    def _get_selections(self) -> tuple[str, int, str]:
        difficulty = self.difficulty_cb.get()
        puzzle_num = int(self.puzzle_cb.get().split()[-1])
        algorithm  = self.algo_cb.get()
        return difficulty, puzzle_num, algorithm

    def _on_setting_change(self, _event=None) -> None:
        self._load_puzzle_action()

    def _load_puzzle_action(self) -> None:
        difficulty, puzzle_num, _ = self._get_selections()
        try:
            grid = load_puzzle(difficulty, puzzle_num)
        except (FileNotFoundError, ValueError) as err:
            messagebox.showerror("Load Error", str(err))
            return

        self._display_puzzle(grid)

        if self.mode == "AI":
            self.time_label.config(
                text="Time Complexity (Elapsed Time):\n— not run yet —",
                fg=TEXT_SECONDARY,
            )
        else:
            self.hint_label.config(
                text="Press Hint to reveal a cell.",
                fg=TEXT_SECONDARY,
            )

    def _reset_action(self) -> None:
        #Restore the grid to the last loaded puzzle state.
        if not self.current_grid:
            return
        self._display_puzzle(self.current_grid)
        if self.mode == "AI":
            self.time_label.config(
                text="Time Complexity (Elapsed Time):\n— not run yet —",
                fg=TEXT_SECONDARY,
            )
        else:
            self.hint_label.config(
                text="Press Hint to reveal a cell.",
                fg=TEXT_SECONDARY,
            )

    def _solve_action(self) -> None:
        if not self.current_grid:
            messagebox.showinfo("No Puzzle", "Please load a puzzle first.")
            return

        _, _, algorithm = self._get_selections()
        self.time_label.config(text="Solving …", fg=TEXT_SECONDARY)
        self.update_idletasks()

        solved, elapsed = solve(self.current_grid, algorithm)

        if solved is None:
            self.time_label.config(
                text="No solution found.",
                fg=ACCENT,
            )
            messagebox.showwarning("No Solution", "This puzzle has no solution.")
            return

        self._display_solution(solved)
        self.time_label.config(
            text=(
                f"Time Complexity (Elapsed Time):\n"
                f"Algorithm : {algorithm}\n"
                f"Time      : {elapsed:.6f}s"
            ),
            fg=TEXT_SOLVED,
        )

    def _hint_action(self) -> None:
        if not self.current_grid:
            messagebox.showinfo("No Puzzle", "Please load a puzzle first.")
            return

        _, _, algorithm = self._get_selections()

        # Always solve from the original puzzle — user entries may be wrong
        solved, _ = solve(self.current_grid, algorithm)

        if solved is None:
            messagebox.showwarning(
                "Cannot Hint",
                "No solution exists for this puzzle.\n"
                "Try resetting and loading a fresh puzzle."
            )
            return

        wrong_cells: list[tuple[int, int]] = []
        empty_cells: list[tuple[int, int]] = []

        for r in range(9):
            for c in range(9):
                if (r, c) in self.given_cells:
                    continue
                user_val = self._get_user_value(r, c)
                if user_val == 0:
                    empty_cells.append((r, c))
                elif user_val != solved[r][c]:
                    wrong_cells.append((r, c))
                # correct non-empty cells are left untouched

        if wrong_cells:
            # Correct every wrong cell so the board is consistent
            for r, c in wrong_cells:
                self._set_cell(r, c, solved[r][c], "hint")
            # Re-check all peers of corrected cells so red highlights clear
            seen: set[tuple[int, int]] = set()
            for r, c in wrong_cells:
                for pr, pc in self._peer_coords(r, c):
                    if (pr, pc) in self.given_cells or (pr, pc) in seen:
                        continue
                    seen.add((pr, pc))
                    pv = self._get_user_value(pr, pc)
                    if pv == 0:
                        continue
                    conflict = self._has_conflict(pr, pc, pv)
                    entry = self.cell_widgets[pr][pc]
                    if entry.cget("bg") in (BG_CELL, BG_CELL_ERROR):
                        entry.config(
                            fg=TEXT_ERROR if conflict else TEXT_USER,
                            bg=BG_CELL_ERROR if conflict else BG_CELL,
                        )
            remaining = len(empty_cells)
            self.hint_label.config(
                text=f"Corrected {len(wrong_cells)} wrong cell(s).\n"
                     f"{remaining} empty cell(s) remaining.",
                fg=TEXT_HINT,
            )
            return

        if not empty_cells:
            messagebox.showinfo("Solved!", "The puzzle is already complete!")
            return

        # No wrong cells — reveal the first empty cell
        r, c = empty_cells[0]
        self._set_cell(r, c, solved[r][c], "hint")

        remaining = len(empty_cells) - 1
        self.hint_label.config(
            text=f"Hint revealed: ({r+1},{c+1}) = {solved[r][c]}\n"
                 f"{remaining} cell(s) remaining.",
            fg=TEXT_HINT,
        )
    
    # In User mode, check if the current board state is a complete and correct solution.
    def _complete_action(self) -> None:
        if not self.current_grid:
            messagebox.showinfo("No Puzzle", "Please load a puzzle first.")
            return
        # Pehle check karte hain ke koi cell khali to nahi
        empty_cells = 0
        for r in range(9):
            for c in range(9):
                if (r, c) not in self.given_cells:
                    if self._get_user_value(r, c) == 0:
                        empty_cells += 1
        if empty_cells > 0:
            messagebox.showwarning("Incomplete", f"Puzzle not complete yet!\nAbhi {empty_cells} dabbe khali hain.")
            return
        # Agar sab fill hain, to AI se actual solution nikal kar compare karte hain
        _, _, algorithm = self._get_selections()
        solved, _ = solve(self.current_grid, algorithm)
        if solved is None:
            messagebox.showerror("Error", "This puzzle has no solution.")
            return
        # User ke answers ko sahi solution se match karna
        wrong_cells = 0
        for r in range(9):
            for c in range(9):
                if (r, c) not in self.given_cells:
                    if self._get_user_value(r, c) != solved[r][c]:
                        wrong_cells += 1
        # Final Result Message Box
        if wrong_cells > 0:
            messagebox.showwarning("Incorrect", f"Puzzle not complete yet!\nAapne sab fill kar diya hai lekin {wrong_cells} dabbe galat hain.")
        else:
            messagebox.showinfo("Congratulations!", "🎉 Zabardast! Aapne Sudoku bilkul sahi solve kar liya hai!")

    def _read_user_board(self) -> list[list[int]]:
        board = [[0] * 9 for _ in range(9)]
        for r in range(9):
            for c in range(9):
                if (r, c) in self.given_cells:
                    board[r][c] = self.current_grid[r][c]
                else:
                    board[r][c] = self._get_user_value(r, c)
        return board

    def _get_user_value(self, r: int, c: int) -> int:
        if self.mode != "User":
            return 0
        val = self.cell_vars[r][c].get().strip()
        if val.isdigit() and val != "0":
            return int(val)
        return 0

# UTILITY 
def _border_offset(index: int) -> int:
    THICK = 3
    THIN  = 1
    block  = index // 3          # how many thick borders before this index
    within = index % 3           # position within the current block
    thin_count = index - block   # thin borders = index − thick-border count
    return block * THICK + thin_count * THIN + THICK  # +THICK for outer border

# ENTRY POINT 
if __name__ == "__main__":
    app = SudokuApp()
    app.mainloop()