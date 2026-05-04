import random
import tkinter as tk
from copy import deepcopy
from tkinter import messagebox, ttk

BOARD_SIZE = 20
EMPTY = 0
BLACK = 1
WHITE = 2
STONE_LABEL = {BLACK: "黑", WHITE: "白"}


class GoBoard:
    def __init__(self, size=BOARD_SIZE):
        self.size = size
        self.grid = [[EMPTY for _ in range(size)] for _ in range(size)]

    def in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def neighbors(self, x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def get_group_and_liberties(self, x, y):
        color = self.grid[y][x]
        if color == EMPTY:
            return set(), set()

        group = set()
        liberties = set()
        stack = [(x, y)]

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))

            for nx, ny in self.neighbors(cx, cy):
                v = self.grid[ny][nx]
                if v == EMPTY:
                    liberties.add((nx, ny))
                elif v == color and (nx, ny) not in group:
                    stack.append((nx, ny))

        return group, liberties

    def remove_group(self, group):
        for x, y in group:
            self.grid[y][x] = EMPTY

    def clone(self):
        b = GoBoard(self.size)
        b.grid = deepcopy(self.grid)
        return b

    def place_stone(self, x, y, color):
        if not self.in_bounds(x, y) or self.grid[y][x] != EMPTY:
            return False, 0

        self.grid[y][x] = color
        opponent = BLACK if color == WHITE else WHITE
        captured = 0

        checked = set()
        for nx, ny in self.neighbors(x, y):
            if self.grid[ny][nx] != opponent or (nx, ny) in checked:
                continue
            group, libs = self.get_group_and_liberties(nx, ny)
            checked |= group
            if len(libs) == 0:
                captured += len(group)
                self.remove_group(group)

        own_group, own_libs = self.get_group_and_liberties(x, y)
        if len(own_libs) == 0:
            self.remove_group(own_group)
            return False, 0

        return True, captured

    def legal_moves(self, color):
        moves = []
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[y][x] != EMPTY:
                    continue
                b = self.clone()
                ok, _ = b.place_stone(x, y, color)
                if ok:
                    moves.append((x, y))
        return moves


class GoAI:
    def __init__(self, difficulty):
        self.difficulty = difficulty

    def pick_move(self, board, color):
        legal = board.legal_moves(color)
        if not legal:
            return None

        if self.difficulty == "简单":
            return random.choice(legal)
        if self.difficulty == "中等":
            return self._best_capture_move(board, color, legal)
        return self._hard_move(board, color, legal)

    def _best_capture_move(self, board, color, legal):
        best_score = -1
        best = []
        for x, y in legal:
            b = board.clone()
            ok, captured = b.place_stone(x, y, color)
            if not ok:
                continue
            if captured > best_score:
                best_score = captured
                best = [(x, y)]
            elif captured == best_score:
                best.append((x, y))
        return random.choice(best) if best else random.choice(legal)

    def _hard_move(self, board, color, legal):
        opponent = BLACK if color == WHITE else WHITE
        best_value = -10**9
        best = []

        for x, y in legal:
            b = board.clone()
            ok, captured = b.place_stone(x, y, color)
            if not ok:
                continue

            my_value = self._evaluate_board(b, color) + captured * 8
            opp_best = 0
            for ox, oy in b.legal_moves(opponent)[:60]:
                b2 = b.clone()
                ok2, ocap = b2.place_stone(ox, oy, opponent)
                if ok2:
                    opp_best = max(opp_best, ocap * 7 + self._evaluate_board(b2, opponent) // 4)

            score = my_value - opp_best
            if score > best_value:
                best_value = score
                best = [(x, y)]
            elif score == best_value:
                best.append((x, y))

        return random.choice(best) if best else random.choice(legal)

    def _evaluate_board(self, board, color):
        opponent = BLACK if color == WHITE else WHITE
        my_stones = 0
        opp_stones = 0
        liberty_score = 0
        visited = set()

        for y in range(board.size):
            for x in range(board.size):
                v = board.grid[y][x]
                if v == color:
                    my_stones += 1
                elif v == opponent:
                    opp_stones += 1

                if v in (color, opponent) and (x, y) not in visited:
                    group, libs = board.get_group_and_liberties(x, y)
                    visited |= group
                    if v == color:
                        liberty_score += len(libs)
                    else:
                        liberty_score -= len(libs)

        return (my_stones - opp_stones) * 10 + liberty_score * 2


class GoGameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("20x20 围棋（人机/AI对战）")

        self.board = GoBoard(BOARD_SIZE)
        self.cell = 30
        self.margin = 30
        self.canvas_size = self.margin * 2 + self.cell * (BOARD_SIZE - 1)

        self.current_player = BLACK
        self.move_history = []
        self.game_mode = tk.StringVar(value="人机对战")
        self.difficulty = tk.StringVar(value="中等")

        # 防止 AI 模式回调重复调度
        self.ai_running = False
        self.ai_job_id = None

        self._build_ui()
        self.draw_board()

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT)

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))

        top_controls = ttk.Frame(left)
        top_controls.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top_controls, text="模式:").pack(side=tk.LEFT)
        mode_box = ttk.Combobox(
            top_controls,
            textvariable=self.game_mode,
            values=["人机对战", "AI对战"],
            state="readonly",
            width=10,
        )
        mode_box.pack(side=tk.LEFT, padx=(4, 10))
        mode_box.bind("<<ComboboxSelected>>", self.on_mode_or_difficulty_change)

        ttk.Label(top_controls, text="难度:").pack(side=tk.LEFT)
        diff_box = ttk.Combobox(
            top_controls,
            textvariable=self.difficulty,
            values=["简单", "中等", "困难"],
            state="readonly",
            width=8,
        )
        diff_box.pack(side=tk.LEFT, padx=(4, 10))
        diff_box.bind("<<ComboboxSelected>>", self.on_mode_or_difficulty_change)

        ttk.Button(top_controls, text="重新开始", command=self.reset_game).pack(side=tk.LEFT)

        self.status_label = ttk.Label(top_controls, text="当前：黑棋")
        self.status_label.pack(side=tk.LEFT, padx=(12, 0))

        self.canvas = tk.Canvas(left, width=self.canvas_size, height=self.canvas_size, bg="#DDB66D")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_board_click)

        ttk.Label(right, text="落子记录").pack(anchor="w")
        self.move_list = tk.Listbox(right, width=28, height=36)
        self.move_list.pack(fill=tk.Y, expand=True)

    def draw_board(self):
        self.canvas.delete("all")

        for i in range(BOARD_SIZE):
            p = self.margin + i * self.cell
            self.canvas.create_line(self.margin, p, self.canvas_size - self.margin, p)
            self.canvas.create_line(p, self.margin, p, self.canvas_size - self.margin)

        r = self.cell * 0.42
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                v = self.board.grid[y][x]
                if v == EMPTY:
                    continue
                cx = self.margin + x * self.cell
                cy = self.margin + y * self.cell
                fill = "black" if v == BLACK else "white"
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline="black")

    def board_xy_from_click(self, event):
        x = round((event.x - self.margin) / self.cell)
        y = round((event.y - self.margin) / self.cell)
        if self.board.in_bounds(x, y):
            return x, y
        return None

    def on_mode_or_difficulty_change(self, _event=None):
        # 切模式时，停止旧的 AI 调度，按当前模式继续
        self.stop_ai_loop()
        self.maybe_ai_turn()

    def on_board_click(self, event):
        if self.ai_running or self.game_mode.get() != "人机对战" or self.current_player != BLACK:
            return

        pos = self.board_xy_from_click(event)
        if pos is None:
            return

        self.play_move(*pos, trigger_next=True)

    def play_move(self, x, y, trigger_next=False):
        color = self.current_player
        ok, captured = self.board.place_stone(x, y, color)
        if not ok:
            return False

        self.move_history.append((color, x, y, captured))
        move_no = len(self.move_history)
        self.move_list.insert(tk.END, f"{move_no:03d}. {STONE_LABEL[color]} ({x + 1},{y + 1}) 吃子:{captured}")
        self.move_list.see(tk.END)

        self.current_player = WHITE if self.current_player == BLACK else BLACK
        self.draw_board()
        self.update_status()

        if trigger_next:
            self.root.after(80, self.maybe_ai_turn)

        return True

    def update_status(self):
        self.status_label.config(text=f"当前：{STONE_LABEL[self.current_player]}棋")

    def maybe_ai_turn(self):
        mode = self.game_mode.get()

        if mode == "人机对战":
            self.stop_ai_loop()
            if self.current_player == WHITE:
                self.ai_move_once()
            return

        # AI 对战
        if mode == "AI对战" and not self.ai_running:
            self.ai_running = True
            self.schedule_ai_loop(120)

    def ai_move_once(self):
        ai = GoAI(self.difficulty.get())
        move = ai.pick_move(self.board, self.current_player)
        if move is None:
            messagebox.showinfo("结束", "AI无合法落子，游戏结束。")
            return
        self.play_move(*move, trigger_next=False)

    def schedule_ai_loop(self, delay_ms=250):
        self.ai_job_id = self.root.after(delay_ms, self.ai_move_loop)

    def stop_ai_loop(self):
        self.ai_running = False
        if self.ai_job_id is not None:
            try:
                self.root.after_cancel(self.ai_job_id)
            except tk.TclError:
                pass
            self.ai_job_id = None

    def ai_move_loop(self):
        self.ai_job_id = None
        if not self.ai_running or self.game_mode.get() != "AI对战":
            self.stop_ai_loop()
            return

        ai = GoAI(self.difficulty.get())
        move = ai.pick_move(self.board, self.current_player)
        if move is None:
            loser = STONE_LABEL[self.current_player]
            winner = "白" if self.current_player == BLACK else "黑"
            self.stop_ai_loop()
            messagebox.showinfo("结束", f"{loser}棋无合法落子，{winner}棋获胜。")
            return

        self.play_move(*move, trigger_next=False)

        if self.ai_running and self.game_mode.get() == "AI对战":
            self.schedule_ai_loop(250)

    def reset_game(self):
        self.stop_ai_loop()
        self.board = GoBoard(BOARD_SIZE)
        self.current_player = BLACK
        self.move_history.clear()
        self.move_list.delete(0, tk.END)
        self.draw_board()
        self.update_status()
        self.root.after(80, self.maybe_ai_turn)


def main():
    root = tk.Tk()
    app = GoGameApp(root)
    app.reset_game()
    root.mainloop()


if __name__ == "__main__":
    main()
