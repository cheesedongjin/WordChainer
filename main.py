import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import random
from typing import Dict, List, Set, Tuple

class WordChainGame:
    def __init__(self, root):
        self.root = root
        self.root.title("끝말잇기 게임")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")
        
        # 게임 데이터
        self.words_data: Dict = {}
        self.used_words: Set[str] = set()
        self.game_history: List[Tuple[str, str]] = []  # (speaker, word)
        self.current_last_char: str = ""
        self.bot_difficulty: int = 5  # 1-10
        
        # 두음법칙 매핑
        self.dueum_map = {
            # ㄴ → 삭제 (ㅣ 또는 이중모음 ㅑ, ㅕ, ㅛ, ㅠ, ㅖ 등)
            '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '냐': '야', '네': '예',
            # ㄹ → 삭제 (ㅣ 또는 ㅣ를 포함한 이중모음)
            '려': '여', '료': '요', '류': '유', '례': '예', '리': '이', '랴': '야',
            # ㄹ → ㄴ (단모음 또는 ㅏ, ㅗ, ㅜ, ㅡ, ㅐ, ㅔ, ㅚ)
            '라': '나', '락': '낙', '란': '난', '람': '남', '랍': '납', '랑': '낭',
            '래': '내', '랭': '냉', '량': '냥',
            '로': '노', '록': '녹', '론': '논', '롱': '농',
            '뢰': '뇌', '뇨': '요',
            '루': '누', '룩': '눅', '룬': '눈', '룡': '농',
            '르': '느', '륵': '늑', '른': '는', '릉': '능'
        }
        
        self.setup_ui()
        self.load_words()
        
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
        
        tk.Label(difficulty_frame, text="봇 난이도:", font=("맑은 고딕", 11),
                bg="white").pack(side=tk.LEFT, padx=10, pady=10)
        
        self.difficulty_var = tk.IntVar(value=5)
        difficulty_scale = ttk.Scale(difficulty_frame, from_=1, to=10, 
                                    variable=self.difficulty_var,
                                    orient=tk.HORIZONTAL, length=200,
                                    command=self.on_difficulty_change)
        difficulty_scale.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.difficulty_label = tk.Label(difficulty_frame, text="5", 
                                         font=("맑은 고딕", 11, "bold"),
                                         bg="white", fg="#4a90e2")
        self.difficulty_label.pack(side=tk.LEFT, padx=10)
        
        # 게임 상태
        status_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(status_frame, 
                                     text="'시작' 버튼을 눌러 게임을 시작하세요",
                                     font=("맑은 고딕", 11),
                                     bg="white", fg="#666", wraplength=500)
        self.status_label.pack(pady=15, padx=10)
        
        # 채팅 영역
        chat_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(chat_frame, text="게임 진행", font=("맑은 고딕", 12, "bold"),
                bg="white").pack(anchor=tk.W, padx=10, pady=5)
        
        self.chat_text = scrolledtext.ScrolledText(chat_frame, 
                                                   font=("맑은 고딕", 10),
                                                   bg="#fafafa", 
                                                   relief=tk.FLAT,
                                                   wrap=tk.WORD,
                                                   state=tk.DISABLED)
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 태그 설정
        self.chat_text.tag_config("user", foreground="#2c5aa0", font=("맑은 고딕", 10, "bold"))
        self.chat_text.tag_config("bot", foreground="#e74c3c", font=("맑은 고딕", 10, "bold"))
        self.chat_text.tag_config("system", foreground="#7f8c8d", font=("맑은 고딕", 9, "italic"))
        self.chat_text.tag_config("word_link", foreground="#4a90e2", underline=True)
        
        # 입력 영역
        input_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        input_frame.pack(fill=tk.X)
        
        self.word_entry = tk.Entry(input_frame, font=("맑은 고딕", 12),
                                   relief=tk.FLAT, bg="#fafafa")
        self.word_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, 
                            padx=10, pady=10)
        self.word_entry.bind('<Return>', lambda e: self.submit_word())
        
        submit_btn = tk.Button(input_frame, text="제출", 
                              font=("맑은 고딕", 11, "bold"),
                              bg="#4a90e2", fg="white",
                              relief=tk.FLAT, padx=20,
                              command=self.submit_word)
        submit_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # 오른쪽 패널 (단어 정보)
        right_panel = tk.Frame(main_container, bg="white", 
                              relief=tk.RAISED, bd=1, width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        tk.Label(right_panel, text="단어 정보", 
                font=("맑은 고딕", 12, "bold"),
                bg="white").pack(anchor=tk.W, padx=10, pady=10)
        
        self.info_text = scrolledtext.ScrolledText(right_panel,
                                                   font=("맑은 고딕", 9),
                                                   bg="#fafafa",
                                                   relief=tk.FLAT,
                                                   wrap=tk.WORD,
                                                   state=tk.DISABLED)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 하단 버튼
        button_frame = tk.Frame(self.root, bg="#f5f5f5")
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        start_btn = tk.Button(button_frame, text="게임 시작", 
                             font=("맑은 고딕", 11, "bold"),
                             bg="#27ae60", fg="white",
                             relief=tk.FLAT, padx=30, pady=10,
                             command=self.start_game)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(button_frame, text="다시 시작",
                             font=("맑은 고딕", 11, "bold"),
                             bg="#e67e22", fg="white",
                             relief=tk.FLAT, padx=30, pady=10,
                             command=self.reset_game)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
    def load_words(self):
        """words.json 파일 로드"""
        try:
            with open('words.json', 'r', encoding='utf-8') as f:
                self.words_data = json.load(f)
            self.add_system_message(f"✓ 사전 로드 완료: {len(self.words_data)}개 단어")
        except FileNotFoundError:
            messagebox.showerror("오류", "words.json 파일을 찾을 수 없습니다.")
        except json.JSONDecodeError:
            messagebox.showerror("오류", "JSON 파일 형식이 올바르지 않습니다.")
    
    def on_difficulty_change(self, value):
        """난이도 변경 처리"""
        self.bot_difficulty = int(float(value))
        self.difficulty_label.config(text=str(self.bot_difficulty))
    
    def start_game(self):
        """게임 시작"""
        self.reset_game()
        self.add_system_message("게임이 시작되었습니다! 아무 단어나 입력하세요.")
        self.status_label.config(text="당신의 차례입니다", fg="#27ae60")
        self.word_entry.config(state=tk.NORMAL)
        self.word_entry.focus()
    
    def reset_game(self):
        """게임 초기화"""
        self.used_words.clear()
        self.game_history.clear()
        self.current_last_char = ""
        
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
        except:
            pass
    
    def add_system_message(self, message):
        """시스템 메시지 추가"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[시스템] {message}\n", "system")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def add_word_message(self, speaker, word):
        """단어 메시지 추가 (클릭 가능)"""
        self.chat_text.config(state=tk.NORMAL)
        
        if speaker == "user":
            self.chat_text.insert(tk.END, "당신: ", "user")
        else:
            self.chat_text.insert(tk.END, "봇: ", "bot")
        
        # 클릭 가능한 단어
        start_index = self.chat_text.index(tk.END)
        self.chat_text.insert(tk.END, word, "word_link")
        end_index = self.chat_text.index(tk.END)
        
        # 클릭 이벤트 바인딩
        self.chat_text.tag_bind("word_link", "<Button-1>", 
                               lambda e, w=word: self.show_word_info(w))
        self.chat_text.tag_bind("word_link", "<Enter>",
                               lambda e: self.chat_text.config(cursor="hand2"))
        self.chat_text.tag_bind("word_link", "<Leave>",
                               lambda e: self.chat_text.config(cursor=""))
        
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
                
                self.info_text.insert(tk.END, f"이음 수: {entry.get('이음 수', 0)}\n")
                
                if '용례' in entry and entry['용례']:
                    self.info_text.insert(tk.END, f"\n용례:\n{entry['용례']}\n")
                
                if idx < len(self.words_data[word]):
                    self.info_text.insert(tk.END, "\n" + "-"*40 + "\n\n")
        else:
            self.info_text.insert(tk.END, f"'{word}' 단어 정보를 찾을 수 없습니다.")
        
        self.info_text.config(state=tk.DISABLED)
    
    def get_first_char(self, word):
        """두음법칙 적용한 첫 글자"""
        first = word[0]
        return self.dueum_map.get(first, first)
    
    def get_last_char(self, word):
        """마지막 글자"""
        return word[-1]
    
    def apply_dueum_decrease(self, char):
        """해당 글자로 끝나는 모든 단어의 이음 수 -1"""
        # 두음법칙 역매핑: 표준형으로 끝나는 글자를 찾아서 원래 두음법칙 글자들도 포함
        possible_chars = [char]
        
        # char로 변환되는 모든 두음법칙 글자 찾기
        for dueum_char, standard_char in self.dueum_map.items():
            if standard_char == char:
                # 두음법칙 글자의 첫 음절만 추출 (예: '락'에서 '라')
                if len(dueum_char) == 1:
                    possible_chars.append(dueum_char)
        
        # 해당 글자들로 끝나는 모든 단어의 이음 수 감소
        for word, entries in self.words_data.items():
            if word[-1] in possible_chars:
                for entry in entries:
                    if '이음 수' in entry:
                        entry['이음 수'] = max(0, entry['이음 수'] - 1)
    
    def submit_word(self):
        """사용자 단어 제출"""
        word = self.word_entry.get().strip()
        self.word_entry.delete(0, tk.END)
        
        if not word:
            return
        
        # 단어 검증
        if word not in self.words_data:
            messagebox.showwarning("경고", "사전에 없는 단어입니다.")
            return
        
        if word in self.used_words:
            messagebox.showwarning("경고", "이미 사용된 단어입니다.")
            return
        
        # 첫 단어가 아니면 끝말잇기 규칙 검사
        if self.current_last_char:
            first_char = self.get_first_char(word)
            if first_char != self.current_last_char:
                messagebox.showwarning("경고", 
                    f"'{self.current_last_char}'(으)로 시작하는 단어를 입력하세요.")
                return
        
        # 단어 추가
        self.used_words.add(word)
        self.game_history.append(("user", word))
        self.add_word_message("user", word)
        
        # 마지막 글자 업데이트
        last_char = self.get_last_char(word)
        self.current_last_char = last_char
        
        # 이음 수 감소
        self.apply_dueum_decrease(self.get_first_char(word))
        
        # 봇 차례
        self.status_label.config(text="봇이 생각 중...", fg="#e67e22")
        self.word_entry.config(state=tk.DISABLED)
        self.root.after(1000, self.bot_turn)
    
    def bot_turn(self):
        """봇의 차례"""
        # 사용 가능한 단어 찾기
        possible_words = []
        
        for word, entries in self.words_data.items():
            if word in self.used_words:
                continue
            
            first_char = self.get_first_char(word)
            if first_char != self.current_last_char:
                continue
            
            # 이음 수 확인
            max_euem = max(entry.get('이음 수', 0) for entry in entries)
            
            # 난이도에 따른 필터링
            min_threshold = 3000 - (self.bot_difficulty * 250)
            if max_euem < min_threshold:
                continue
            
            possible_words.append((word, max_euem))
        
        if not possible_words:
            self.add_system_message("봇이 말할 수 있는 단어가 없습니다. 당신의 승리!")
            self.status_label.config(text="게임 종료 - 당신의 승리! 🎉", fg="#27ae60")
            self.word_entry.config(state=tk.DISABLED)
            return
        
        # 사용자가 사용한 마지막 단어의 이음 수
        last_user_word = self.game_history[-1][1]
        last_euem = max(entry.get('이음 수', 0) 
                       for entry in self.words_data[last_user_word])
        
        # 성공 확률 계산
        base_prob = 1.0
        if last_euem < 1000:
            difficulty_factor = self.bot_difficulty / 10.0
            euem_factor = last_euem / 1000.0
            base_prob = 0.3 + (0.7 * difficulty_factor) + (euem_factor * 0.3)
            base_prob = min(1.0, base_prob)
        
        # 확률에 따라 실패할 수도 있음
        if random.random() > base_prob:
            self.add_system_message(f"봇이 단어를 찾지 못했습니다! (성공 확률: {base_prob:.1%})")
            self.status_label.config(text="게임 종료 - 당신의 승리! 🎉", fg="#27ae60")
            self.word_entry.config(state=tk.DISABLED)
            return
        
        # 단어 선택 (이음 수가 높은 것 우선)
        possible_words.sort(key=lambda x: x[1], reverse=True)
        selected_word = possible_words[0][0]
        
        # 봇 단어 추가
        self.used_words.add(selected_word)
        self.game_history.append(("bot", selected_word))
        self.add_word_message("bot", selected_word)
        
        # 마지막 글자 업데이트
        last_char = self.get_last_char(selected_word)
        self.current_last_char = last_char
        
        # 이음 수 감소
        self.apply_dueum_decrease(self.get_first_char(selected_word))
        
        # 사용자 차례
        self.status_label.config(text=f"'{last_char}'(으)로 시작하는 단어를 입력하세요", 
                                fg="#2c5aa0")
        self.word_entry.config(state=tk.NORMAL)
        self.word_entry.focus()

if __name__ == "__main__":
    root = tk.Tk()
    app = WordChainGame(root)
    root.mainloop()
    