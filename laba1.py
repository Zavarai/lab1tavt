import tkinter as tk
from tkinter import filedialog, ttk
import random
import configparser

# --- НАСТРОЙКИ И КОНСТАНТЫ ---
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 550
SHIP_MAX_HP = 100
FORT_DEFAULT_HP = 1000
BASE_SHIP_DAMAGE = 5
BASE_FORT_DAMAGE = 6

# Предустановленные цвета
PRESET_COLORS = {
    "Красный": "#E74C3C",
    "Синий": "#3498DB",
    "Зеленый": "#2ECC71",
    "Желтый": "#F1C40F",
    "Оранжевый": "#E67E22",
    "Фиолетовый": "#9B59B6",
    "Розовый": "#FF69B4",
    "Голубой": "#00CED1",
    "Коричневый": "#8B4513",
    "Серый": "#7F8C8D",
    "Черный": "#000000",
    "Белый": "#FFFFFF"
}


class ColorCombobox(tk.Frame):
    """Кастомный комбобокс с цветными квадратиками"""

    def __init__(self, parent, colors_dict, initial_color, other_combo=None, show_error_callback=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.colors_dict = colors_dict
        self.color_names = list(colors_dict.keys())
        self.selected_color = initial_color
        self.selected_name = ""
        self.other_combo = other_combo
        self.show_error_callback = show_error_callback

        for name, hex_color in colors_dict.items():
            if hex_color.lower() == initial_color.lower():
                self.selected_name = name
                break

        self.display_frame = tk.Frame(self, relief="solid", bd=1, cursor="hand2")
        self.display_frame.pack(fill="x", expand=True)

        self.label = tk.Label(self.display_frame, text=self.selected_name if self.selected_name else "Выберите цвет",
                              anchor="w", padx=5, bg="white")
        self.label.pack(side="left", fill="x", expand=True)

        self.color_canvas = tk.Canvas(self.display_frame, width=30, height=20,
                                      bg=initial_color if initial_color else "white")
        self.color_canvas.pack(side="right", padx=2, pady=2)

        self.arrow = tk.Label(self.display_frame, text="▼", bg="white", padx=3)
        self.arrow.pack(side="right")

        self.display_frame.bind("<Button-1>", self.toggle_dropdown)
        self.label.bind("<Button-1>", self.toggle_dropdown)
        self.color_canvas.bind("<Button-1>", self.toggle_dropdown)
        self.arrow.bind("<Button-1>", self.toggle_dropdown)

        self.dropdown = None

    def toggle_dropdown(self, event):
        if self.dropdown and self.dropdown.winfo_exists():
            self.dropdown.destroy()
            self.dropdown = None
        else:
            self.show_dropdown()

    def show_dropdown(self):
        self.dropdown = tk.Toplevel(self)
        self.dropdown.overrideredirect(True)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.dropdown.geometry(f"+{x}+{y}")

        listbox_frame = tk.Frame(self.dropdown, relief="solid", bd=1)
        listbox_frame.pack(fill="both", expand=True)

        for color_name in self.color_names:
            hex_color = self.colors_dict[color_name]

            item_frame = tk.Frame(listbox_frame, bg="white", cursor="hand2")
            item_frame.pack(fill="x")

            item_label = tk.Label(item_frame, text=color_name, anchor="w", padx=5, bg="white", width=15)
            item_label.pack(side="left", fill="x", expand=True)

            item_canvas = tk.Canvas(item_frame, width=30, height=20, bg=hex_color, highlightthickness=1,
                                    highlightbackground="black")
            item_canvas.pack(side="right", padx=5, pady=3)

            for widget in [item_frame, item_label, item_canvas]:
                widget.bind("<Button-1>", lambda e, name=color_name, hex=hex_color: self.select_color(name, hex))
                widget.bind("<Enter>", lambda e, f=item_frame: f.config(bg="#E0E0E0"))
                widget.bind("<Leave>", lambda e, f=item_frame: f.config(bg="white"))

        self.dropdown.bind("<FocusOut>", lambda e: self.close_dropdown())
        self.after(100, lambda: self.dropdown.focus_force())

    def select_color(self, name, hex_color):
        if self.other_combo and self.other_combo.get_color().lower() == hex_color.lower():
            if self.show_error_callback:
                self.show_error_callback("Ошибка: Цвета кораблей и крепости должны отличаться!")
            self.close_dropdown()
            return

        self.selected_name = name
        self.selected_color = hex_color
        self.label.config(text=name)
        self.color_canvas.config(bg=hex_color)
        self.close_dropdown()

    def close_dropdown(self):
        if self.dropdown and self.dropdown.winfo_exists():
            self.dropdown.destroy()
            self.dropdown = None

    def get_color(self):
        return self.selected_color

    def set_color(self, hex_color):
        self.selected_color = hex_color
        for name, color in self.colors_dict.items():
            if color.lower() == hex_color.lower():
                self.selected_name = name
                self.label.config(text=name)
                self.color_canvas.config(bg=hex_color)
                break


class Entity:
    def __init__(self, x, y, hp, max_hp):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = max_hp
        self.alive = True
        self.attack_delay = 0


class Ship(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SHIP_MAX_HP, SHIP_MAX_HP)


class Fortress(Entity):
    def __init__(self, x, y, max_hp):
        super().__init__(x, y, max_hp, max_hp)


class Projectile:
    def __init__(self, x, y, target_x, target_y, damage, owner, will_hit):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.damage = damage
        self.owner = owner
        self.will_hit = will_hit  # Сразу известно, попадёт ли снаряд

        # Упрощённая физика: просто летим по прямой к цели
        dx = target_x - x
        dy = target_y - y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance > 0:
            speed = 10
            self.vx = (dx / distance) * speed
            self.vy = (dy / distance) * speed
        else:
            self.vx = 0
            self.vy = 0

        self.distance_traveled = 0
        self.total_distance = distance


class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Морская Битва: Корабли против Крепости")
        self.root.geometry(f"{CANVAS_WIDTH + 20}x{CANVAS_HEIGHT + 220}")
        self.root.resizable(False, False)

        self.game_state = 'stopped'
        self.ships = []
        self.fortress = None
        self.projectiles = []

        self.ship_color = "#E74C3C"
        self.fort_color = "#3498DB"
        self.fort_max_hp = FORT_DEFAULT_HP

        self.ship_acc_int = tk.IntVar(value=70)
        self.ship_acc_str = tk.StringVar(value="70")

        self.fort_acc_int = tk.IntVar(value=60)
        self.fort_acc_str = tk.StringVar(value="60")

        self.game_speed_int = tk.IntVar(value=10)
        self.game_speed_str = tk.StringVar(value="10")

        self.current_turn = 'ship'
        self.attack_timer = 0
        self.attack_interval = 40

        self._error_win = None

        self.setup_ui()
        self.init_game()
        self.game_loop()

    def setup_ui(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Сохранить как...", command=self.save_game)
        file_menu.add_command(label="Открыть...", command=self.load_game)
        menu_bar.add_cascade(label="Файл", menu=file_menu)

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Цвет", command=self.open_color_dialog)
        settings_menu.add_command(label="Начальное заполнение", command=self.open_hp_dialog)
        menu_bar.add_cascade(label="Настройки", menu=settings_menu)

        self.root.config(menu=menu_bar)

        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="#87CEEB", highlightthickness=2)
        self.canvas.pack(pady=5)
        self.canvas.create_rectangle(0, CANVAS_HEIGHT - 100, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#2980B9", outline="")

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)

        slider_frame = tk.Frame(bottom_frame)
        slider_frame.pack(side=tk.LEFT, padx=10)

        def create_labeled_input(parent, row, label_text, int_var, str_var, max_val=100):
            tk.Label(parent, text=label_text).grid(row=row, column=0, padx=5, sticky="w")

            scale = tk.Scale(parent, from_=1, to=max_val, orient=tk.HORIZONTAL, variable=int_var, length=150)
            scale.grid(row=row, column=1, padx=5)

            entry = tk.Entry(parent, textvariable=str_var, width=5, justify="center", font=("Arial", 10))
            entry.grid(row=row, column=2, padx=5)

            vcmd = (self.root.register(self.validate_int_input), '%P', int_var, entry)
            entry.config(validate="key", validatecommand=vcmd)

            entry.bind("<FocusOut>", lambda e: self.clamp_and_sync(e, str_var, int_var, entry, max_val))
            entry.bind("<Return>", lambda e: self.clamp_and_sync(e, str_var, int_var, entry, max_val))

            int_var.trace_add("write", lambda *args: str_var.set(str(int_var.get())))

            # Мгновенное обновление ползунка при вводе цифр
            str_var.trace_add("write", lambda *args: self.instant_sync(str_var, int_var, max_val))

            return entry

        self.ship_acc_entry = create_labeled_input(slider_frame, 0, "Точность кораблей:", self.ship_acc_int,
                                                   self.ship_acc_str)
        self.fort_acc_entry = create_labeled_input(slider_frame, 1, "Точность крепости:", self.fort_acc_int,
                                                   self.fort_acc_str)
        self.speed_entry = create_labeled_input(slider_frame, 2, "Скорость игры:", self.game_speed_int,
                                                self.game_speed_str)

        btn_frame = tk.Frame(bottom_frame)
        btn_frame.pack(side=tk.RIGHT, padx=10)

        self.btn_start = tk.Button(btn_frame, text="Старт", command=self.toggle_start_stop, width=12, bg="#2ECC71",
                                   fg="white", font=("Arial", 10, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_pause = tk.Button(btn_frame, text="Пауза", command=self.toggle_pause, width=12, bg="#F1C40F",
                                   state=tk.DISABLED, font=("Arial", 10, "bold"))
        self.btn_pause.pack(side=tk.LEFT, padx=5)

        self.btn_exit = tk.Button(btn_frame, text="Выход", command=self.root.destroy, width=12, bg="#E74C3C",
                                  fg="white", font=("Arial", 10, "bold"))
        self.btn_exit.pack(side=tk.LEFT, padx=5)

    def instant_sync(self, str_var, int_var, max_val):
        """Мгновенно синхронизирует ползунок с введённым значением"""
        val = str_var.get()
        if val and val.isdigit():
            num = int(val)
            if 1 <= num <= max_val:
                int_var.set(num)

    def validate_int_input(self, P, int_var, entry):
        if P == "":
            return True

        if not P.isdigit():
            self.show_temp_error("Ошибка: Вводите только цифры!")
            return False

        if len(P) > 1 and P.startswith('0'):
            self.show_temp_error("Ошибка: Число не может начинаться с 0!")
            return False

        return True

    def clamp_and_sync(self, event, str_var, int_var, entry, max_val=100):
        val = entry.get()
        if not val:
            entry.insert(0, str(int_var.get()))
            return

        num = int(val)
        error_msg = None

        if num > max_val:
            num = max_val
            error_msg = f"Значение ограничено максимумом: {max_val}"
        elif num < 1:
            num = 1
            error_msg = "Значение ограничено минимумом: 1"

        if error_msg:
            self.show_temp_error(error_msg)

        int_var.set(num)
        str_var.set(str(num))
        entry.delete(0, tk.END)
        entry.insert(0, str(num))

    def show_temp_error(self, message, duration=3000):
        if hasattr(self, '_error_win') and self._error_win and self._error_win.winfo_exists():
            self._error_win.destroy()

        self._error_win = tk.Toplevel(self.root)
        self._error_win.title("Ошибка")
        self._error_win.geometry("320x120")
        self._error_win.transient(self.root)
        self._error_win.grab_set()
        self._error_win.resizable(False, False)

        tk.Label(self._error_win, text=message, fg="red", font=("Arial", 11, "bold"), wraplength=300).pack(pady=10)
        tk.Button(self._error_win, text="ОК", command=self._error_win.destroy, width=10, bg="#3498DB", fg="white").pack(
            pady=5)

        self.root.after(duration, self._safe_destroy_error)

    def _safe_destroy_error(self):
        if hasattr(self, '_error_win') and self._error_win and self._error_win.winfo_exists():
            self._error_win.destroy()

    def open_color_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройка цветов")
        dialog.geometry("350x280")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Цвет кораблей (паруса):", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.ship_color_combo = ColorCombobox(dialog, PRESET_COLORS, self.ship_color,
                                              show_error_callback=self.show_temp_error)
        self.ship_color_combo.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Цвет крепости (флаг):", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.fort_color_combo = ColorCombobox(dialog, PRESET_COLORS, self.fort_color,
                                              show_error_callback=self.show_temp_error)
        self.fort_color_combo.pack(pady=5, padx=20, fill="x")

        self.ship_color_combo.other_combo = self.fort_color_combo
        self.fort_color_combo.other_combo = self.ship_color_combo

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Случайные цвета", command=self.randomize_colors, bg="#9B59B6", fg="white",
                  width=15).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="ОК", command=lambda: self.apply_colors(dialog), width=10, bg="#2ECC71",
                  fg="white").grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy, width=10).grid(row=0, column=2, padx=5)

    def randomize_colors(self):
        color_items = list(PRESET_COLORS.items())
        random.shuffle(color_items)

        name1, hex1 = color_items[0]
        name2, hex2 = color_items[1]

        self.ship_color_combo.select_color(name1, hex1)
        self.fort_color_combo.select_color(name2, hex2)

    def apply_colors(self, dialog):
        new_ship_color = self.ship_color_combo.get_color()
        new_fort_color = self.fort_color_combo.get_color()

        if new_ship_color.lower() == new_fort_color.lower():
            self.show_temp_error("Ошибка: Цвета кораблей и крепости должны отличаться!")
            return

        self.ship_color = new_ship_color
        self.fort_color = new_fort_color
        dialog.destroy()

    def open_hp_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Начальное заполнение (HP Крепости)")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Введите начальное HP для крепости:").pack(pady=10)
        entry = tk.Entry(dialog, justify="center")
        entry.insert(0, str(self.fort_max_hp))
        entry.pack()

        def apply_hp():
            try:
                val = int(entry.get())
                if val <= 0: raise ValueError
                self.fort_max_hp = val
                if self.game_state == 'stopped':
                    self.fortress.max_hp = val
                    self.fortress.hp = val
                dialog.destroy()
            except ValueError:
                self.show_temp_error("Ошибка: Введите целое положительное число!")

        tk.Button(dialog, text="Применить", command=apply_hp, bg="#2ECC71", fg="white", width=15).pack(pady=10)

    def init_game(self):
        self.ships = []
        self.projectiles = []
        self.current_turn = 'ship'
        self.attack_timer = 0

        for i in range(10):
            x = 50 + (i % 5) * 70
            y = 150 + (i // 5) * 120
            self.ships.append(Ship(x, y))

        self.fortress = Fortress(CANVAS_WIDTH - 150, CANVAS_HEIGHT // 2 - 60, self.fort_max_hp)

    def toggle_start_stop(self):
        if self.game_state == 'stopped':
            self.init_game()
            self.game_state = 'running'
            self.btn_start.config(text="Стоп", bg="#E74C3C")
            self.btn_pause.config(state=tk.NORMAL, text="Пауза", bg="#F1C40F")
        else:
            self.game_state = 'stopped'
            self.btn_start.config(text="Старт", bg="#2ECC71")
            self.btn_pause.config(state=tk.DISABLED, text="Пауза", bg="#F1C40F")

    def toggle_pause(self):
        if self.game_state == 'running':
            self.game_state = 'paused'
            self.btn_pause.config(text="Продолжить", bg="#3498DB")
        elif self.game_state == 'paused':
            self.game_state = 'running'
            self.btn_pause.config(text="Пауза", bg="#F1C40F")

    def save_game(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".ini", filetypes=[("INI files", "*.ini")])
        if not filepath: return

        config = configparser.ConfigParser()
        config['Settings'] = {
            'ship_color': self.ship_color,
            'fort_color': self.fort_color,
            'fort_max_hp': str(self.fort_max_hp),
            'ship_acc': str(self.ship_acc_int.get()),
            'fort_acc': str(self.fort_acc_int.get()),
            'game_speed': str(self.game_speed_int.get())
        }
        config['State'] = {
            'current_turn': self.current_turn,
            'fort_x': str(self.fortress.x),
            'fort_y': str(self.fortress.y),
            'fort_hp': str(self.fortress.hp),
            'fort_max_hp': str(self.fortress.max_hp),
            'fort_alive': str(self.fortress.alive)
        }

        ships_data = {}
        for i, s in enumerate(self.ships):
            ships_data[f'ship_{i}'] = f"{s.x},{s.y},{s.hp},{s.max_hp},{s.alive}"
        config['Ships'] = ships_data

        with open(filepath, 'w', encoding='utf-8') as f:
            config.write(f)
        self.show_temp_error("Игра успешно сохранена в .ini!", 2000)

    def load_game(self):
        filepath = filedialog.askopenfilename(filetypes=[("INI files", "*.ini")])
        if not filepath: return

        config = configparser.ConfigParser()
        config.read(filepath, encoding='utf-8')

        try:
            self.ship_color = config['Settings']['ship_color']
            self.fort_color = config['Settings']['fort_color']
            self.fort_max_hp = int(config['Settings']['fort_max_hp'])
            self.ship_acc_int.set(int(config['Settings']['ship_acc']))
            self.fort_acc_int.set(int(config['Settings']['fort_acc']))
            self.game_speed_int.set(int(config['Settings']['game_speed']))

            fd = config['State']
            self.fortress = Fortress(float(fd['fort_x']), float(fd['fort_y']), int(fd['fort_max_hp']))
            self.fortress.hp = float(fd['fort_hp'])
            self.fortress.alive = fd['fort_alive'] == 'True'

            self.ships = []
            for i in range(10):
                data = config['Ships'][f'ship_{i}'].split(',')
                ship = Ship(float(data[0]), float(data[1]))
                ship.hp = float(data[2])
                ship.max_hp = float(data[3])
                ship.alive = data[4] == 'True'
                self.ships.append(ship)

            self.current_turn = config['State']['current_turn']
            self.projectiles = []
            self.show_temp_error("Сохранение успешно загружено!", 2000)
        except Exception as e:
            self.show_temp_error(f"Не удалось загрузить файл:\n{e}")

    def game_loop(self):
        if self.game_state == 'running':
            self.update_logic()

        self.draw()

        speed = self.game_speed_int.get()
        delay = max(1, int(1000 / (speed * speed * 0.1 + 1)))
        self.root.after(delay, self.game_loop)

    def update_logic(self):
        alive_ships = [s for s in self.ships if s.alive]
        if not alive_ships or not self.fortress.alive:
            self.game_state = 'stopped'
            self.btn_start.config(text="Старт", bg="#2ECC71")
            self.btn_pause.config(state=tk.DISABLED, text="Пауза", bg="#F1C40F")
            msg = "Крепость пала! Корабли победили!" if not self.fortress.alive else "Крепость уничтожила все корабли!"
            self.show_temp_error(msg, 4000)
            return

        # Движение снарядов
        new_projectiles = []
        for p in self.projectiles:
            p.x += p.vx
            p.y += p.vy
            p.distance_traveled += (p.vx ** 2 + p.vy ** 2) ** 0.5

            # Проверяем, достиг ли снаряд цели
            if p.distance_traveled >= p.total_distance:
                if p.will_hit:  # Если снаряд должен попасть
                    if p.owner == 'ship':
                        self.fortress.hp -= p.damage
                        if self.fortress.hp <= 0:
                            self.fortress.hp = 0
                            self.fortress.alive = False
                    else:
                        # Находим ближайший корабль к точке попадания
                        target = min(alive_ships,
                                     key=lambda s: (s.x + 30 - p.target_x) ** 2 + (s.y + 15 - p.target_y) ** 2)
                        target.hp -= p.damage
                        if target.hp <= 0:
                            target.hp = 0
                            target.alive = False
                # Снаряд достиг цели (или промахнулся), удаляем его
                continue

            # Если снаряд ещё летит
            if 0 < p.x < CANVAS_WIDTH and 0 < p.y < CANVAS_HEIGHT:
                new_projectiles.append(p)

        self.projectiles = new_projectiles

        # Пошаговые атаки
        self.attack_timer += 1
        current_interval = max(5, self.attack_interval - (self.game_speed_int.get() // 3))

        if self.attack_timer >= current_interval:
            self.attack_timer = 0

            if self.current_turn == 'ship':
                attacker = random.choice(alive_ships)
                r = random.randint(10, 20)
                hp_ratio = attacker.hp / attacker.max_hp
                damage = r * hp_ratio + BASE_SHIP_DAMAGE

                # Упрощённая логика попадания: random < accuracy/100
                accuracy = self.ship_acc_int.get()
                will_hit = random.random() < (accuracy / 100.0)

                self.projectiles.append(Projectile(
                    attacker.x + 30, attacker.y,
                    self.fortress.x + 50, self.fortress.y + 60,
                    damage, 'ship', will_hit
                ))
                attacker.attack_delay = 15
                self.current_turn = 'fort'
            else:
                target = random.choice(alive_ships)
                r = random.randint(10, 22)
                fort_hp_ratio = self.fortress.hp / self.fortress.max_hp
                damage = r * fort_hp_ratio + BASE_FORT_DAMAGE

                # Упрощённая логика попадания
                accuracy = self.fort_acc_int.get()
                will_hit = random.random() < (accuracy / 100.0)

                self.projectiles.append(Projectile(
                    self.fortress.x, self.fortress.y + 60,
                                     target.x + 30, target.y + 15,
                    damage, 'fort', will_hit
                ))
                self.fortress.attack_delay = 15
                self.current_turn = 'ship'

        for s in self.ships:
            if s.attack_delay > 0:
                s.attack_delay -= 1
        if self.fortress.attack_delay > 0:
            self.fortress.attack_delay -= 1

    def draw(self):
        self.canvas.delete("all")
        # фон
        self.canvas.create_rectangle(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT - 100, fill="#87CEEB", outline="")
        self.canvas.create_rectangle(0, CANVAS_HEIGHT - 100, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#2980B9", outline="")
        # крепость
        if self.fortress.alive:
            fx, fy = self.fortress.x, self.fortress.y
            if self.fortress.attack_delay > 0:
                self.canvas.create_rectangle(fx - 5, fy - 5, fx + 105, fy + 125, outline="#FFD700", width=3)

            self.canvas.create_rectangle(fx, fy + 40, fx + 100, fy + 120, fill="#7F8C8D", outline="#2C3E50", width=2)
            self.canvas.create_rectangle(fx + 10, fy + 20, fx + 40, fy + 40, fill="#95A5A6", outline="#2C3E50")
            self.canvas.create_rectangle(fx + 60, fy + 20, fx + 90, fy + 40, fill="#95A5A6", outline="#2C3E50")
            self.canvas.create_line(fx + 50, fy + 20, fx + 50, fy - 20, fill="black", width=2)
            self.canvas.create_polygon(fx + 50, fy - 20, fx + 80, fy - 10, fx + 50, fy, fill=self.fort_color,
                                       outline="black")
            self.draw_hp_bar(fx, fy - 30, 100, self.fortress.hp, self.fortress.max_hp)
        else:
            self.canvas.create_polygon(self.fortress.x, CANVAS_HEIGHT - 100, self.fortress.x + 100, CANVAS_HEIGHT - 100,
                                       self.fortress.x + 80, CANVAS_HEIGHT - 130, self.fortress.x + 20,
                                       CANVAS_HEIGHT - 120, fill="#7F8C8D")
        # корабли
        for s in self.ships:
            if s.alive:
                sx, sy = s.x, s.y
                if s.attack_delay > 0:
                    self.canvas.create_rectangle(sx - 3, sy - 3, sx + 63, sy + 38, outline="#FFD700", width=3)

                self.canvas.create_polygon(sx, sy + 20, sx + 60, sy + 20, sx + 50, sy + 35, sx + 10, sy + 35,
                                           fill="#8B4513", outline="black")
                self.canvas.create_line(sx + 20, sy + 20, sx + 20, sy - 10, fill="black", width=2)
                self.canvas.create_polygon(sx + 20, sy - 10, sx + 45, sy, sx + 20, sy + 10, fill=self.ship_color,
                                           outline="black")
                self.canvas.create_line(sx + 40, sy + 20, sx + 40, sy - 5, fill="black", width=2)
                self.canvas.create_polygon(sx + 40, sy - 5, sx + 60, sy + 5, sx + 40, sy + 15, fill=self.ship_color,
                                           outline="black")
                self.draw_hp_bar(sx, sy - 20, 60, s.hp, s.max_hp)
        # снаряды
        for p in self.projectiles:
            self.canvas.create_oval(p.x - 3, p.y - 3, p.x + 3, p.y + 3, fill="black")
        # чей ход
        turn_text = "Ход: Корабли" if self.current_turn == 'ship' else "Ход: Крепость"
        self.canvas.create_text(CANVAS_WIDTH // 2, 30, text=turn_text, font=("Arial", 16, "bold"), fill="black")

    def draw_hp_bar(self, x, y, width, current_hp, max_hp):
        ratio = current_hp / max_hp
        color = "#2ECC71" if ratio > 0.5 else "#F1C40F" if ratio > 0.2 else "#E74C3C"
        self.canvas.create_rectangle(x, y, x + width, y + 8, fill="black", outline="white")
        self.canvas.create_rectangle(x, y, x + width * ratio, y + 8, fill=color, outline="")


if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()