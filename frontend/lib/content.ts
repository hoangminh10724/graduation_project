export const sections = {
  "luyen-ngu-am": ["Luyện ngữ âm", "mic"],
  ipa: ["Bản đồ IPA", "grid"],
  "luyen-ngu-dieu": ["Luyện ngữ điệu", "wave"],
  "tu-dien": ["Từ điển", "book"],
  "tu-da-luu": ["Từ đã lưu", "bookmark"],
  talk: ["Hội thoại AI", "talk"],
  "tien-do": ["Tiến độ", "chart"],
  "lich-su": ["Lịch sử", "history"],
  "ho-so": ["Hồ sơ", "user"],
  "cai-dat": ["Cài đặt", "settings"],
  "dang-nhap": ["Đăng nhập", "user"],
  "dang-ky": ["Đăng ký", "user"],
} as const;

export type Section = keyof typeof sections;

const groups = {
  "Nguyên âm đơn":
    "iː:seat|ɪ:sit|ɛ:bed|æ:bad|uː:food|ʊ:book|ʌ:cup|ɒ:hot|ɔː:thought|ɑː:father|ɜː:bird|ə:about",
  "Nguyên âm đôi": "eɪ:day|aɪ:time|ɔɪ:boy|aʊ:now|əʊ:go|ɪə:near|eə:hair|ʊə:tour",
  "Phụ âm":
    "p:pen|b:bed|t:ten|d:dog|k:key|ɡ:go|f:fan|v:van|θ:think|ð:this|s:see|z:zoo|ʃ:she|ʒ:vision|h:hat|tʃ:chair|dʒ:jam|m:moon|n:name|ŋ:sing|l:light|r:red|j:yes|w:water",
};
const tips: Record<string, [string, string, string, number, number, number]> = {
  iː: ["Giãn nhẹ môi, nâng phần trước lưỡi.", "take a seat", "ɪ", 0.88, 0.25, 0.15],
  ɪ: ["Giữ môi thả lỏng và hạ lưỡi một chút.", "please sit", "iː", 0.7, 0.36, 0.24],
  ɛ: ["Mở hàm vừa phải, để lưỡi ở phía trước.", "make the bed", "æ", 0.78, 0.5, 0.31],
  æ: ["Hạ hàm rõ hơn, giữ lưỡi ở phía trước.", "a bad day", "ɛ", 0.82, 0.79, 0.39],
  uː: ["Thu và làm tròn môi, nâng phần sau lưỡi.", "good food", "ʊ", 0.28, 0.28, 0.8],
  ʊ: ["Giữ môi hơi tròn và thả lỏng hàm.", "read a book", "uː", 0.46, 0.38, 0.68],
  p: ["Khép hai môi, sau đó mở nhanh để nhả hơi.", "a blue pen", "t", 0.76, 0, 0.5],
  t: ["Chạm đầu lưỡi vào gờ sau răng trên rồi nhả.", "count to ten", "k", 0.67, 0.24, 0.12],
  k: ["Nâng phần sau lưỡi về vòm mềm rồi nhả.", "find the key", "t", 0.68, 0.34, 0.89],
  s: ["Để luồng hơi đi qua khe hẹp phía trước.", "I can see", "ʃ", 0.78, 0.19, 0.12],
  ʃ: ["Lùi vùng tạo khe nhẹ so với /s/ và hơi tròn môi.", "there she is", "s", 0.4, 0.28, 0.43],
};
const difficult = new Set(["iː", "ɪ", "æ", "θ", "ð", "ʃ", "ʒ", "tʃ", "dʒ", "z", "r"]);
const unsupportedTips: Record<string, string> = {
  θ: "Đưa đầu lưỡi nhẹ giữa hai hàm răng rồi thổi hơi.",
  ð: "Đặt lưỡi như /θ/ và thêm rung giọng.",
  ŋ: "Nâng phần sau lưỡi và để hơi thoát qua mũi.",
  l: "Chạm đầu lưỡi vào gờ răng và để hơi đi hai bên.",
  f: "Đưa môi dưới gần răng trên và thổi hơi.",
  v: "Đưa môi dưới gần răng trên và thêm rung giọng.",
  r: "Nhấc đầu lưỡi về phía vòm, giữ một khoảng cách nhỏ.",
  z: "Giữ khe hơi như /s/ và thêm rung giọng.",
  b: "Khép môi rồi nhả, có rung giọng.",
  d: "Chạm đầu lưỡi vào gờ răng rồi nhả, có rung giọng.",
};
export const sounds = Object.entries(groups).flatMap(([group, entries]) =>
  entries.split("|").map((entry) => {
    const [ipa, word] = entry.split(":");
    const hint = tips[ipa];
    return {
      ipa,
      word,
      group,
      difficult: difficult.has(ipa),
      supported: Boolean(hint && ipa !== "ʊ"),
      hint,
      guide:
        hint?.[0] ??
        unsupportedTips[ipa] ??
        (group === "Nguyên âm đôi"
          ? "Nói liền hai vị trí nguyên âm trong cùng một âm tiết."
          : "Nghe từ mẫu và chú ý vị trí của âm khi phát ra."),
    };
  }),
);
export type Sound = (typeof sounds)[number];
export const targets = sounds.filter((sound) => sound.supported);

export const entries = [
  ["seat", "siːt", "danh từ", "chỗ ngồi", "Please take a seat.", "iː"],
  ["sit", "sɪt", "động từ", "ngồi", "You can sit next to me.", "ɪ"],
  ["bed", "bɛd", "danh từ", "giường", "I make my bed each morning.", "ɛ"],
  ["bad", "bæd", "tính từ", "tồi, xấu", "It was a bad day.", "æ"],
  ["food", "fuːd", "danh từ", "thức ăn", "The food is delicious.", "uː"],
  ["pen", "pɛn", "danh từ", "bút mực", "May I borrow your pen?", "p"],
  ["ten", "tɛn", "số từ", "mười", "There are ten books on the shelf.", "t"],
  ["key", "kiː", "danh từ", "chìa khóa", "I found the key in my bag.", "k"],
  ["see", "siː", "động từ", "thấy, nhìn thấy", "I can see the sea.", "s"],
  ["she", "ʃiː", "đại từ", "cô ấy", "She listens to music on the train.", "ʃ"],
  ["think", "θɪŋk", "động từ", "nghĩ, suy nghĩ", "What do you think about this idea?", ""],
  ["about", "əˈbaʊt", "giới từ", "về, liên quan đến", "Tell me about your day.", ""],
  ["book", "bʊk", "danh từ", "cuốn sách", "I read a book before bed.", ""],
  ["travel", "ˈtrævəl", "động từ", "đi du lịch", "I travel by train when I can.", ""],
  ["friend", "frɛnd", "danh từ", "bạn bè", "I met a friend at the market.", ""],
  ["really", "ˈrɪəli", "trạng từ", "thật sự", "I really like this song.", ""],
  ["music", "ˈmjuːzɪk", "danh từ", "âm nhạc", "I listen to music every day.", ""],
  ["coffee", "ˈkɒfi", "danh từ", "cà phê", "Would you like a cup of coffee?", ""],
  ["market", "ˈmɑːkɪt", "danh từ", "chợ, thị trường", "We buy fruit at the market.", ""],
  ["water", "ˈwɔːtə", "danh từ", "nước", "Please bring some water.", ""],
].map(([word, ipa, kind, meaning, example, sound]) => ({ word, ipa, kind, meaning, example, sound }));
export type Entry = (typeof entries)[number];

export const dictionaryCategories = [
  { title: "Đồ vật và nơi chốn", words: ["seat", "bed", "pen", "key", "book", "market"] },
  { title: "Ăn uống và sở thích", words: ["food", "music", "coffee", "water"] },
  { title: "Con người và hoạt động", words: ["sit", "see", "she", "think", "travel", "friend"] },
  { title: "Mô tả và bổ nghĩa", words: ["bad", "ten", "about", "really"] },
] as const;

export const prosody = [
  {
    title: "Trọng âm từ",
    cue: "Giữ âm đầu nhẹ và kéo sự chú ý về âm cuối.",
    examples: [{ text: "about", segments: ["a", "bout"], emphasize: 1 }],
  },
  {
    title: "Nhấn ý",
    cue: "Đổi từ nổi bật để thay đổi trọng tâm của câu hỏi.",
    examples: [
      {
        text: "What do you think?",
        segments: ["What", "do", "you", "think?"],
        emphasize: 2,
      },
      {
        text: "What do you think?",
        segments: ["What", "do", "you", "think?"],
        emphasize: 3,
      },
    ],
  },
  {
    title: "Lên và xuống giọng",
    cue: "Nghe từ cuối đi lên khi hỏi lại và đi xuống khi xác nhận.",
    examples: [
      { text: "Really?", segments: ["Real", "ly?"], emphasize: -1 },
      { text: "Really.", segments: ["Real", "ly."], emphasize: -1 },
    ],
  },
  {
    title: "Nối âm",
    cue: "Nối take với a trong một nhịp, rồi nhấn seat.",
    examples: [{ text: "Take a seat.", segments: ["Take a", "seat."], emphasize: 1 }],
  },
];
