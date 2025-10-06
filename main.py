import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import random
import threading
from typing import Dict, List, Optional, Set, Tuple

# -------------------------------------------------------------------------
# 한글 유니코드 분해/합성 및 두음법칙 유틸리티
# -------------------------------------------------------------------------
HANGUL_BASE = 0xAC00
CHOS = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
JUNGS = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
JONGS = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

CHO_N = 2
CHO_R = 5
CHO_YIEUNG = 11

# ㄴ/ㄹ이 단어 첫머리에 올 때 'ㅇ'으로 떨어지는 모음군(ㅣ계열·y계열·ㅖ·ㅒ·ㅟ·(보수적으로)ㅢ)
IY_JUNG_IDX = {20, 2, 6, 12, 17, 7, 16, 3, 19}


def is_hangul_syllable(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    return 0xAC00 <= o <= 0xD7A3


def decompose(ch: str) -> Optional[Tuple[int, int, int]]:
    if not is_hangul_syllable(ch):
        return None
    code = ord(ch) - HANGUL_BASE
    cho = code // 588
    jung = (code % 588) // 28
    jong = code % 28
    return cho, jung, jong


def compose(cho: int, jung: int, jong: int) -> str:
    return chr(HANGUL_BASE + cho * 588 + jung * 28 + jong)


def dueum_transform(syll: str) -> Optional[str]:
    """두음법칙에 따른 음절 변환."""
    decomp = decompose(syll)
    if decomp is None:
        return None

    cho, jung, jong = decomp
    if cho == CHO_N:
        if jung in IY_JUNG_IDX:
            return compose(CHO_YIEUNG, jung, jong)
        return None

    if cho == CHO_R:
        if jung in IY_JUNG_IDX:
            return compose(CHO_YIEUNG, jung, jong)
        return compose(CHO_N, jung, jong)

    return None

class WordChainGame:
    def __init__(self, root):
        self.root = root
        self.root.title("끝말잇기 게임")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")
        self.try_maximize_window()
        
        # 게임 데이터
        self.words_data: Dict = {}
        self.words_by_first_char: Dict[str, List[str]] = {}
        self.words_by_last_char_variants: Dict[str, Set[str]] = {}
        self.used_words: Set[str] = set()
        self.game_history: List[Tuple[str, str]] = []  # (speaker, word)
        self.current_last_char: str = ""
        self.bot_difficulty: int = 3  # 1-5, 초기 슬라이더 값(3)에 대응

        self.word_tag_counter = 0
        self.base_turn_time_limit = 30
        self.turn_time_limit = self.base_turn_time_limit
        self.timer_seconds_remaining = 0
        self.timer_after_id: Optional[str] = None
        self.pending_bot_after_id: Optional[str] = None
        self.bot_turn_sequence = 0
        self.game_active = False

        self.stats_file = "game_stats.json"
        self.win_count = 0
        self.loss_count = 0
        self.stats_by_difficulty = {
            level: {"wins": 0, "losses": 0} for level in range(1, 6)
        }
        self.difficulty_stats_rows = {}
        self.active_game_difficulty: Optional[int] = None

        self.load_stats()

        self.setup_ui()
        self.refresh_difficulty_stats_panel()
        self.load_words()

    def try_maximize_window(self):
        """가능한 경우 창을 전체 화면 크기로 시작"""
        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)
            except tk.TclError:
                self.root.attributes('-fullscreen', True)
                self.root.bind('<Escape>', self.exit_fullscreen)

    def exit_fullscreen(self, _event=None):
        """전체 화면 모드 해제"""
        self.root.attributes('-fullscreen', False)
        self.root.unbind('<Escape>')
        
    def setup_ui(self):
        # 스타일 설정
        style = ttk.Style()
        style.theme_use('clam')
        
        # 헤더
        header_frame = tk.Frame(self.root, bg="#4a90e2", height=80)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🎮 끝말잇기 게임", 
                               font=("맑은 고딕", 24, "bold"),
                               bg="#4a90e2", fg="white")
        title_label.pack(pady=20)
        
        # 메인 컨테이너
        main_container = tk.Frame(self.root, bg="#f5f5f5")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 왼쪽 패널 (게임 영역)
        left_panel = tk.Frame(main_container, bg="#f5f5f5")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 난이도 설정
        difficulty_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        difficulty_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(difficulty_frame, text="봇 난이도:", font=("맑은 고딕", 18),
                bg="white").pack(side=tk.LEFT, padx=10, pady=10)
        
        self.difficulty_var = tk.IntVar(value=3)
        difficulty_scale = tk.Scale(
            difficulty_frame,
            from_=1,
            to=5,
            variable=self.difficulty_var,
            orient=tk.HORIZONTAL,
            length=200,
            resolution=1,
            showvalue=0,
            bg="white",
            highlightthickness=0,
        )
        difficulty_scale.set(self.difficulty_var.get())
        difficulty_scale.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.difficulty_label = tk.Label(difficulty_frame, text="3",
                                         font=("맑은 고딕", 18, "bold"),
                                         bg="white", fg="#4a90e2")
        self.difficulty_label.pack(side=tk.LEFT, padx=10)

        difficulty_scale.config(command=self.on_difficulty_change)
        self.on_difficulty_change(self.difficulty_var.get())
        
        # 게임 상태
        status_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(status_frame,
                                     text="'시작' 버튼을 눌러 게임을 시작하세요",
                                     font=("맑은 고딕", 18),
                                     bg="white", fg="#666", wraplength=500)
        self.status_label.pack(pady=15, padx=10)

        timer_container = tk.Frame(status_frame, bg="white")
        timer_container.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.timer_label = tk.Label(timer_container,
                                    text="남은 시간: --",
                                    font=("맑은 고딕", 16),
                                    bg="white", fg="#c0392b")
        self.timer_label.pack(anchor=tk.W)

        self.timer_progress = ttk.Progressbar(timer_container,
                                              maximum=self.turn_time_limit,
                                              value=0,
                                              mode='determinate')
        self.timer_progress.pack(fill=tk.X, pady=(5, 0))
        
        # 채팅 영역
        chat_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(chat_frame, text="게임 진행", font=("맑은 고딕", 20, "bold"),
                bg="white").pack(anchor=tk.W, padx=10, pady=5)
        
        self.chat_text = scrolledtext.ScrolledText(chat_frame, 
                                                   font=("맑은 고딕", 16),
                                                   bg="#fafafa", 
                                                   relief=tk.FLAT,
                                                   wrap=tk.WORD,
                                                   state=tk.DISABLED)
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 태그 설정
        self.chat_text.tag_config("user", foreground="#2c5aa0", font=("맑은 고딕", 16, "bold"))
        self.chat_text.tag_config("bot", foreground="#e74c3c", font=("맑은 고딕", 16, "bold"))
        self.chat_text.tag_config("system", foreground="#7f8c8d", font=("맑은 고딕", 14, "italic"))
        self.chat_text.tag_config("word_link", foreground="#4a90e2", underline=True)
        self.chat_text.tag_bind("word_link", "<Enter>",
                               lambda e: self.chat_text.config(cursor="hand2"))
        self.chat_text.tag_bind("word_link", "<Leave>",
                               lambda e: self.chat_text.config(cursor=""))
        
        # 입력 영역
        input_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        input_frame.pack(fill=tk.X)
        
        self.word_entry = tk.Entry(input_frame, font=("맑은 고딕", 20),
                                   relief=tk.FLAT, bg="#fafafa")
        self.word_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, 
                            padx=10, pady=10)
        self.word_entry.bind('<Return>', lambda e: self.submit_word())

        self.word_entry.config(state=tk.DISABLED)
        
        submit_btn = tk.Button(input_frame, text="제출", 
                              font=("맑은 고딕", 18, "bold"),
                              bg="#4a90e2", fg="white",
                              relief=tk.FLAT, padx=20,
                              command=self.submit_word)
        submit_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # 오른쪽 패널 (단어 정보)
        right_panel = tk.Frame(main_container, bg="white",
                              relief=tk.RAISED, bd=1, width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_panel.pack_propagate(False)

        stats_panel = tk.Frame(right_panel, bg="#eef5ff", relief=tk.GROOVE, bd=1)
        stats_panel.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(stats_panel, text="난이도별 전적",
                 font=("맑은 고딕", 16, "bold"),
                 bg="#eef5ff", fg="#2c3e50").pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.difficulty_stats_rows = {}
        for level in range(1, 6):
            row_frame = tk.Frame(stats_panel, bg="#eef5ff")
            row_frame.pack(fill=tk.X, padx=10, pady=2)

            level_label = tk.Label(row_frame,
                                   text=f"{level}단계",
                                   font=("맑은 고딕", 13, "bold"),
                                   bg="#eef5ff", fg="#2c3e50")
            level_label.pack(side=tk.LEFT)

            value_label = tk.Label(row_frame,
                                   text="승리 0 | 패배 0",
                                   font=("맑은 고딕", 12),
                                   bg="#eef5ff", fg="#2c3e50")
            value_label.pack(side=tk.RIGHT)

            self.difficulty_stats_rows[level] = (row_frame, level_label, value_label)

        ttk.Separator(right_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(right_panel, text="단어 정보",
                font=("맑은 고딕", 20, "bold"),
                bg="white").pack(anchor=tk.W, padx=10, pady=10)
        
        self.info_text = scrolledtext.ScrolledText(right_panel,
                                                   font=("맑은 고딕", 14),
                                                   bg="#fafafa",
                                                   relief=tk.FLAT,
                                                   wrap=tk.WORD,
                                                   state=tk.DISABLED)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 하단 버튼
        button_frame = tk.Frame(self.root, bg="#f5f5f5")
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        start_btn = tk.Button(button_frame, text="게임 시작", 
                             font=("맑은 고딕", 18, "bold"),
                             bg="#27ae60", fg="white",
                             relief=tk.FLAT, padx=30, pady=10,
                             command=self.start_game)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        forfeit_btn = tk.Button(button_frame, text="포기",
                                font=("맑은 고딕", 18, "bold"),
                                bg="#c0392b", fg="white",
                                relief=tk.FLAT, padx=30, pady=10,
                                command=self.forfeit_game)
        forfeit_btn.pack(side=tk.LEFT, padx=5)
        
    def load_words(self):
        """words.json 파일 로드"""
        try:
            with open('words.json', 'r', encoding='utf-8') as f:
                self.words_data = json.load(f)
            self.build_word_indexes()
            self.add_system_message(f"✓ 사전 로드 완료: {len(self.words_data)}개 단어")
        except FileNotFoundError:
            self.show_warning_message("words.json 파일을 찾을 수 없습니다.")
        except json.JSONDecodeError:
            self.show_warning_message("JSON 파일 형식이 올바르지 않습니다.")

    def load_stats(self):
        """게임 전적 로드"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.win_count = int(data.get('wins', 0))
            self.loss_count = int(data.get('losses', 0))
            self.stats_by_difficulty = {
                level: {"wins": 0, "losses": 0} for level in range(1, 6)
            }

            by_difficulty = data.get('by_difficulty', {})
            if isinstance(by_difficulty, dict):
                for key, value in by_difficulty.items():
                    try:
                        level = int(key)
                    except (TypeError, ValueError):
                        continue

                    if not isinstance(value, dict):
                        continue

                    try:
                        wins = int(value.get('wins', 0))
                    except (TypeError, ValueError):
                        wins = 0

                    try:
                        losses = int(value.get('losses', 0))
                    except (TypeError, ValueError):
                        losses = 0

                    if level not in self.stats_by_difficulty:
                        self.stats_by_difficulty[level] = {"wins": 0, "losses": 0}

                    self.stats_by_difficulty[level]['wins'] = max(wins, 0)
                    self.stats_by_difficulty[level]['losses'] = max(losses, 0)
        except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
            self.win_count = 0
            self.loss_count = 0
            self.stats_by_difficulty = {
                level: {"wins": 0, "losses": 0} for level in range(1, 6)
            }

    def save_stats(self):
        """게임 전적 저장"""
        try:
            by_difficulty = {
                str(level): {
                    'wins': stats.get('wins', 0),
                    'losses': stats.get('losses', 0)
                }
                for level, stats in sorted(self.stats_by_difficulty.items())
            }

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'wins': self.win_count,
                    'losses': self.loss_count,
                    'by_difficulty': by_difficulty
                }, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def refresh_difficulty_stats_panel(self):
        rows = getattr(self, 'difficulty_stats_rows', None)
        if not rows:
            return

        for level, (row_frame, level_label, value_label) in rows.items():
            stats = self.stats_by_difficulty.get(level, {"wins": 0, "losses": 0})
            value_label.config(
                text=f"승리 {stats.get('wins', 0)} | 패배 {stats.get('losses', 0)}"
            )

            highlight = self.bot_difficulty == level
            bg_color = "#d6eaff" if highlight else "#eef5ff"

            row_frame.config(bg=bg_color)
            level_label.config(bg=bg_color)
            value_label.config(bg=bg_color)

    def update_stats(self, wins: int = 0, losses: int = 0, difficulty: Optional[int] = None):
        if wins == 0 and losses == 0:
            return

        self.win_count += wins
        self.loss_count += losses

        if difficulty is None:
            difficulty = self.active_game_difficulty or self.bot_difficulty

        try:
            difficulty_int = int(difficulty) if difficulty is not None else None
        except (TypeError, ValueError):
            difficulty_int = None

        if difficulty_int is not None:
            if difficulty_int not in self.stats_by_difficulty:
                self.stats_by_difficulty[difficulty_int] = {"wins": 0, "losses": 0}

            self.stats_by_difficulty[difficulty_int]['wins'] += wins
            self.stats_by_difficulty[difficulty_int]['losses'] += losses

        self.refresh_difficulty_stats_panel()
        self.save_stats()
        self.active_game_difficulty = None

    def build_word_indexes(self):
        """단어 검색 속도를 높이기 위해 색인 생성"""
        words_by_first_char: Dict[str, List[str]] = {}
        words_by_last_char_variants: Dict[str, Set[str]] = {}

        for word in self.words_data.keys():
            if not word:
                continue

            first_char = self.get_first_char(word)
            words_by_first_char.setdefault(first_char, []).append(word)

            last_char = self.get_last_char(word)
            for variant in self.get_dueum_variants(last_char):
                words_by_last_char_variants.setdefault(variant, set()).add(word)

        self.words_by_first_char = words_by_first_char
        self.words_by_last_char_variants = words_by_last_char_variants
    
    def on_difficulty_change(self, value):
        """난이도 변경 처리"""
        rounded_value = int(round(float(value)))
        if rounded_value != self.difficulty_var.get():
            self.difficulty_var.set(rounded_value)

        self.bot_difficulty = rounded_value
        self.difficulty_label.config(text=str(rounded_value))
        self.update_turn_time_limit()
        self.refresh_difficulty_stats_panel()

    def get_effective_difficulty(self) -> int:
        """기존 6~10 단계에 맞춘 보정 난이도."""
        return self.bot_difficulty + 5

    def update_turn_time_limit(self):
        """난이도에 따른 생각 시간 조정"""
        extra_time = 0 if self.get_effective_difficulty() >= 10 else 0
        new_limit = self.base_turn_time_limit + extra_time

        if new_limit == self.turn_time_limit:
            return

        old_limit = self.turn_time_limit
        self.turn_time_limit = new_limit

        if self.timer_seconds_remaining > 0:
            if new_limit > old_limit:
                self.timer_seconds_remaining = min(
                    new_limit,
                    self.timer_seconds_remaining + (new_limit - old_limit)
                )
            else:
                self.timer_seconds_remaining = min(self.timer_seconds_remaining, new_limit)
            self.timer_progress.config(maximum=new_limit)
            self.timer_progress['value'] = min(self.timer_seconds_remaining, new_limit)
            self.update_timer_display()
        else:
            self.timer_progress.config(maximum=new_limit)

    def start_game(self):
        """게임 시작"""
        self.reset_game()
        self.active_game_difficulty = self.bot_difficulty
        self.add_system_message(f"{self.bot_difficulty}단계 봇과의 게임이 시작되었습니다! 아무 단어나 입력하세요.")
        self.status_label.config(text="당신의 차례입니다", fg="#27ae60")
        self.word_entry.config(state=tk.NORMAL)
        self.word_entry.focus()
        self.game_active = True
        self.start_timer()

    def reset_game(self):
        """게임 초기화"""
        self.game_active = False
        self.active_game_difficulty = None
        self.cancel_pending_bot_turn()
        self.invalidate_bot_turn()
        self.used_words.clear()
        self.game_history.clear()
        self.current_last_char = ""
        self.word_tag_counter = 0

        self.stop_timer()
        self.reset_timer_display()

        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state=tk.DISABLED)
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state=tk.DISABLED)
        
        self.word_entry.delete(0, tk.END)
        self.word_entry.config(state=tk.NORMAL)
        
        # 이음 수 원래대로 복원
        try:
            with open('words.json', 'r', encoding='utf-8') as f:
                self.words_data = json.load(f)
            self.build_word_indexes()
        except:
            pass
    
    def add_system_message(self, message):
        """시스템 메시지 추가"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[시스템] {message}\n", "system")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def add_system_message_with_word_links(self, prefix: str, words: List[str]):
        """클릭 가능한 단어 목록이 포함된 시스템 메시지 추가"""
        if not words:
            self.add_system_message(prefix.strip())
            return

        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, "[시스템] ", "system")
        self.chat_text.insert(tk.END, prefix, "system")

        for idx, word in enumerate(words):
            if idx > 0:
                self.chat_text.insert(tk.END, ", ", "system")

            tag_name = f"word_link_{self.word_tag_counter}"
            self.word_tag_counter += 1

            self.chat_text.insert(
                tk.END,
                word,
                ("system", tag_name, "word_link"),
            )
            self.chat_text.tag_bind(
                tag_name,
                "<Button-1>",
                lambda e, w=word: self.show_word_info(w),
            )

        self.chat_text.insert(tk.END, "\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def show_warning_message(self, message: str):
        """경고 메시지를 화면에 출력"""
        self.add_system_message(f"⚠️ {message}")
        self.status_label.config(text=message, fg="#c0392b")
    
    def add_word_message(self, speaker, word):
        """단어 메시지 추가 (클릭 가능)"""
        self.chat_text.config(state=tk.NORMAL)
        
        if speaker == "user":
            self.chat_text.insert(tk.END, "당신: ", "user")
        else:
            self.chat_text.insert(tk.END, "봇: ", "bot")
        
        # 클릭 가능한 단어
        tag_name = f"word_link_{self.word_tag_counter}"
        self.word_tag_counter += 1
        self.chat_text.insert(tk.END, word, (tag_name, "word_link"))

        # 클릭 이벤트 바인딩
        self.chat_text.tag_bind(tag_name, "<Button-1>",
                               lambda e, w=word: self.show_word_info(w))
        
        self.chat_text.insert(tk.END, "\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def show_word_info(self, word):
        """단어 정보 표시"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        if word in self.words_data:
            self.info_text.insert(tk.END, f"📖 {word}\n\n", "title")
            
            for idx, entry in enumerate(self.words_data[word], 1):
                self.info_text.insert(tk.END, f"[의미 {idx}]\n", "header")
                self.info_text.insert(tk.END, f"발음: {entry.get('발음', '-')}\n")
                self.info_text.insert(tk.END, f"구분: {entry.get('고유어 여부', '-')}\n")
                self.info_text.insert(tk.END, f"뜻: {entry.get('뜻풀이', '-')}\n")
                
                if '전문 분야' in entry:
                    self.info_text.insert(tk.END, f"분야: {entry['전문 분야']}\n")
                
                if '용례' in entry and entry['용례']:
                    self.info_text.insert(tk.END, f"\n용례:\n{entry['용례']}\n")
                
                if idx < len(self.words_data[word]):
                    self.info_text.insert(tk.END, "\n" + "-"*40 + "\n\n")
        else:
            self.info_text.insert(tk.END, f"'{word}' 단어 정보를 찾을 수 없습니다.")
        
        self.info_text.config(state=tk.DISABLED)
    
    def get_first_char(self, word):
        """단어의 첫 글자"""
        return word[0] if word else ""

    def get_last_char(self, word):
        """마지막 글자"""
        return word[-1]

    def get_dueum_variants(self, syllable: str) -> Set[str]:
        """두음법칙을 적용한 가능한 시작 음절 집합"""
        if not syllable:
            return set()

        variants = {syllable}
        transformed = dueum_transform(syllable)
        if transformed:
            variants.add(transformed)
        return variants

    def count_available_followups(self, last_char: str,
                                  exclude_word: Optional[str] = None,
                                  used_words: Optional[Set[str]] = None) -> int:
        """특정 글자로 시작하는 사용 가능한 단어 수를 계산"""
        if not last_char:
            return 0

        allowed_chars = self.get_dueum_variants(last_char)
        used = self.used_words if used_words is None else used_words
        available_words: Set[str] = set()

        for char in allowed_chars:
            for word in self.words_by_first_char.get(char, []):
                if word == exclude_word or word in used:
                    continue
                available_words.add(word)

        return len(available_words)

    def get_possible_user_words(self, limit: int = 10) -> List[str]:
        """현재 상태에서 사용자가 말할 수 있었던 단어 목록을 반환"""
        if not self.current_last_char:
            return []

        allowed_chars = self.get_dueum_variants(self.current_last_char)
        candidates: List[Tuple[str, int]] = []
        seen: Set[str] = set()

        for char in allowed_chars:
            for word in self.words_by_first_char.get(char, []):
                if word in self.used_words or word in seen:
                    continue
                seen.add(word)

                entries = self.words_data[word]
                max_euem = max(entry.get('이음 수', 0) for entry in entries)

                # 게임 시작 후 4턴까지는 이음 수가 0인 단어 사용 불가 규칙 적용
                if len(self.game_history) < 4 and max_euem == 0:
                    continue

                candidates.append((word, max_euem))

        candidates.sort(key=lambda item: (-item[1], item[0]))
        return [word for word, _ in candidates[:limit]]

    def show_possible_user_words(self, limit: int = 10):
        """사용자가 말할 수 있었던 단어 예시를 시스템 메시지로 출력"""
        suggestions = self.get_possible_user_words(limit)

        if not self.current_last_char:
            return

        if not suggestions:
            self.add_system_message("사용자가 말할 수 있는 단어가 없었습니다.")
            return

        prefix = f"사용자가 말할 수 있었던 단어 예시 (최대 {limit}개 표시됨): "
        self.add_system_message_with_word_links(prefix, suggestions)

    def apply_dueum_decrease(self, char):
        """해당 글자와 두음 변환 결과로 끝나는 모든 단어의 이음 수 -1"""
        if not char:
            return

        for word in self.words_by_last_char_variants.get(char, set()):
            entries = self.words_data.get(word, [])
            for entry in entries:
                if '이음 수' in entry:
                    entry['이음 수'] = max(0, entry['이음 수'] - 1)

    def cancel_pending_bot_turn(self):
        """대기 중인 봇 실행 예약 취소"""
        if self.pending_bot_after_id is not None:
            self.root.after_cancel(self.pending_bot_after_id)
            self.pending_bot_after_id = None

    def invalidate_bot_turn(self) -> int:
        """현재 봇 턴 시퀀스를 갱신"""
        self.bot_turn_sequence += 1
        return self.bot_turn_sequence

    def submit_word(self):
        """사용자 단어 제출"""
        if not self.game_active:
            return

        word = self.word_entry.get().strip()
        self.word_entry.delete(0, tk.END)

        if not word:
            return
        
        # 단어 검증
        if not is_hangul_syllable(word[0]) or not is_hangul_syllable(word[-1]):
            self.show_warning_message(f"{word}(은)는 잘못된 단어입니다: 한글로 시작하고 끝나야 합니다.")
            return
        
        if len(word) < 2:
            self.show_warning_message(f"{word}(은)는 잘못된 단어입니다: 최소 2글자 이상이어야 합니다.")
            return

        if word not in self.words_data:
            self.show_warning_message(f"{word}(은)는 잘못된 단어입니다: 사전에 없는 단어이거나 명사가 아닙니다.")
            return

        max_euem = max((entry.get('이음 수', 0)
                         for entry in self.words_data[word]), default=0)
        if len(self.game_history) < 4 and max_euem == 0:
            self.show_warning_message(
                f"{word}(은)는 잘못된 단어입니다: 게임 시작 후 4턴까지는 이음 수가 0인 단어를 사용할 수 없습니다.")
            return

        if word in self.used_words:
            self.show_warning_message(f"{word}(은)는 잘못된 단어입니다: 이미 사용된 단어입니다.")
            return

        first_char = self.get_first_char(word)

        # 첫 단어가 아니면 끝말잇기 규칙 검사
        if self.current_last_char:
            allowed_chars = self.get_dueum_variants(self.current_last_char)
            if first_char not in allowed_chars:
                self.show_warning_message(
                    f"{word}(은)는 잘못된 단어입니다: '{self.current_last_char}'(으)로 시작하는 단어를 입력하세요.")
                return
        
        # 단어 추가
        self.used_words.add(word)
        self.game_history.append(("user", word))
        self.add_word_message("user", word)

        self.stop_timer()

        # 마지막 글자 업데이트
        last_char = self.get_last_char(word)
        self.current_last_char = last_char
        
        # 이음 수 감소
        self.apply_dueum_decrease(first_char)
        
        # 봇 차례
        self.status_label.config(text="봇이 생각 중...", fg="#e67e22")
        self.word_entry.config(state=tk.DISABLED)
        self.cancel_pending_bot_turn()
        turn_id = self.invalidate_bot_turn()
        self.pending_bot_after_id = self.root.after(
            1000, lambda: self.bot_turn(turn_id)
        )

    def bot_turn(self, turn_id: int):
        """봇의 차례를 백그라운드 스레드로 처리"""
        self.pending_bot_after_id = None
        if turn_id != self.bot_turn_sequence or not self.game_active:
            return

        threading.Thread(
            target=self._bot_turn_worker,
            args=(turn_id,),
            daemon=True
        ).start()

    def _bot_turn_worker(self, turn_id: int):
        if turn_id != self.bot_turn_sequence or not self.game_active:
            return

        result = self._compute_bot_decision()

        if turn_id != self.bot_turn_sequence or not self.game_active:
            return

        self.root.after(0, lambda: self._apply_bot_result(turn_id, result))

    def _compute_bot_decision(self) -> Dict[str, Optional[str]]:
        possible_words: List[Tuple[str, int]] = []
        used_words_snapshot = set(self.used_words)
        game_history_snapshot = list(self.game_history)
        last_required_char = self.current_last_char

        if not game_history_snapshot:
            return {"type": "no_word"}

        allowed_chars: Optional[Set[str]] = None
        if last_required_char:
            allowed_chars = self.get_dueum_variants(last_required_char)

        for word, entries in self.words_data.items():
            if word in used_words_snapshot:
                continue

            first_char = self.get_first_char(word)
            if allowed_chars is not None and first_char not in allowed_chars:
                continue

            max_euem = max(entry.get('이음 수', 0) for entry in entries)
            if len(game_history_snapshot) < 4 and max_euem == 0:
                continue

            min_threshold = max(0, 3200 - (self.get_effective_difficulty() * 400))
            if max_euem < min_threshold:
                continue

            possible_words.append((word, max_euem))

        if not possible_words:
            return {"type": "no_word"}

        safe_words: List[Tuple[str, int]] = []
        for word, euem in possible_words:
            last_char = self.get_last_char(word)
            remaining = self.count_available_followups(
                last_char, exclude_word=word, used_words=used_words_snapshot
            )
            if remaining > 0:
                safe_words.append((word, euem))

        if safe_words:
            possible_words = safe_words

        last_user_word = game_history_snapshot[-1][1]
        last_euem = max(
            entry.get('이음 수', 0)
            for entry in self.words_data[last_user_word]
        )

        base_prob = 1.0
        if last_euem < 1000:
            difficulty_factor = self.get_effective_difficulty() / 10.0
            euem_factor = last_euem / 1000.0

            base_skill = 0.35 + (0.65 * difficulty_factor)
            penalty_scale = (1 - difficulty_factor) ** 3
            low_euem_penalty = (1 - euem_factor) * 0.4 * penalty_scale
            euem_bonus = euem_factor * 0.25 * (1 - penalty_scale)

            base_prob = base_skill - low_euem_penalty + euem_bonus
            base_prob = max(0.1, min(1.0, base_prob))

        should_fail = False
        if self.get_effective_difficulty() < 10:
            should_fail = random.random() > base_prob

        if should_fail:
            return {"type": "fail", "base_prob": base_prob}

        min_euem = min(euem for _, euem in possible_words)
        max_euem_val = max(euem for _, euem in possible_words)
        difficulty_factor = self.get_effective_difficulty() / 10.0

        if self.get_effective_difficulty() >= 10:
            min_candidates = [
                word for word, euem in possible_words if euem == min_euem
            ]
            selected_word = random.choice(min_candidates)
        else:
            if max_euem_val == min_euem:
                weights = [1.0 for _ in possible_words]
            else:
                weights = []
                for _, euem in possible_words:
                    normalized = (euem - min_euem) / (max_euem_val - min_euem)
                    high_pref = (1.0 - difficulty_factor) * normalized
                    low_pref = difficulty_factor * (1.0 - normalized)
                    weights.append(high_pref + low_pref + 0.05)

            selected_word = random.choices(
                [word for word, _ in possible_words], weights=weights, k=1
            )[0]

        return {
            "type": "word",
            "word": selected_word,
            "first_char": self.get_first_char(selected_word),
            "last_char": self.get_last_char(selected_word),
        }

    def _apply_bot_result(self, turn_id: int, result: Dict[str, Optional[str]]):
        if turn_id != self.bot_turn_sequence or not self.game_active:
            return

        outcome = result.get("type")

        if outcome == "no_word":
            self.add_system_message("봇이 말할 수 있는 단어가 없습니다. 당신의 승리!")
            self.status_label.config(text="게임 종료 - 당신의 승리! 🎉", fg="#27ae60")
            self.word_entry.config(state=tk.DISABLED)
            self.game_active = False
            self.stop_timer()
            self.reset_timer_display()
            self.update_stats(wins=1)
            return

        if outcome == "fail":
            base_prob = result.get("base_prob", 0.0)
            self.add_system_message(
                f"봇이 단어를 찾지 못했습니다. 당신의 승리!"
            )
            self.status_label.config(text="게임 종료 - 당신의 승리! 🎉", fg="#27ae60")
            self.word_entry.config(state=tk.DISABLED)
            self.game_active = False
            self.stop_timer()
            self.reset_timer_display()
            self.update_stats(wins=1)
            return

        if outcome != "word":
            return

        selected_word = result.get("word")
        if not selected_word:
            return

        selected_first_char = result.get("first_char", "")
        last_char = result.get("last_char", "")

        self.used_words.add(selected_word)
        self.game_history.append(("bot", selected_word))
        self.add_word_message("bot", selected_word)

        self.current_last_char = last_char
        self.apply_dueum_decrease(selected_first_char)

        self.status_label.config(
            text=f"'{last_char}'(으)로 시작하는 단어를 입력하세요",
            fg="#2c5aa0"
        )
        self.word_entry.config(state=tk.NORMAL)
        self.word_entry.focus()
        if self.game_active:
            self.start_timer()

    def start_timer(self):
        """사용자 턴 타이머 시작"""
        self.stop_timer()
        self.update_turn_time_limit()
        self.timer_seconds_remaining = self.turn_time_limit
        self.timer_progress.config(maximum=self.turn_time_limit)
        self.timer_progress['value'] = self.turn_time_limit
        self.update_timer_display()
        self.timer_after_id = self.root.after(1000, self.update_timer)

    def stop_timer(self):
        """타이머 중지"""
        if self.timer_after_id is not None:
            self.root.after_cancel(self.timer_after_id)
            self.timer_after_id = None

    def update_timer(self):
        """타이머 갱신"""
        if self.timer_seconds_remaining <= 0:
            return

        self.timer_seconds_remaining -= 1
        self.timer_progress['value'] = self.timer_seconds_remaining
        self.update_timer_display()

        if self.timer_seconds_remaining <= 0:
            self.timer_progress['value'] = 0
            self.handle_time_out()
        else:
            self.timer_after_id = self.root.after(1000, self.update_timer)

    def update_timer_display(self):
        """타이머 라벨 텍스트 갱신"""
        if self.timer_seconds_remaining > 0:
            self.timer_label.config(text=f"남은 시간: {self.timer_seconds_remaining:02d}초")
        else:
            self.timer_label.config(text="남은 시간: 00초")

    def reset_timer_display(self):
        """타이머 표시 초기화"""
        self.timer_seconds_remaining = 0
        self.timer_label.config(text="남은 시간: --")
        self.timer_progress['value'] = 0

    def handle_time_out(self):
        """사용자 시간 초과 처리"""
        if not self.game_active:
            return

        self.game_active = False
        self.cancel_pending_bot_turn()
        self.invalidate_bot_turn()
        self.stop_timer()
        self.word_entry.config(state=tk.DISABLED)
        self.status_label.config(text="게임 종료 - 시간 초과! ⏰", fg="#c0392b")
        self.add_system_message("시간 초과! 봇의 승리입니다.")
        self.show_possible_user_words()
        self.update_stats(losses=1)

    def forfeit_game(self):
        """사용자 기권 처리"""
        if not self.game_active:
            return

        self.game_active = False
        self.cancel_pending_bot_turn()
        self.invalidate_bot_turn()
        self.stop_timer()
        self.word_entry.config(state=tk.DISABLED)
        self.status_label.config(text="게임 종료 - 당신의 패배", fg="#c0392b")
        self.add_system_message("당신이 기권했습니다. 봇의 승리!")
        self.show_possible_user_words()
        self.reset_timer_display()
        self.update_stats(losses=1)

if __name__ == "__main__":
    root = tk.Tk()
    app = WordChainGame(root)
    root.mainloop()
    