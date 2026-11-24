import { Icon } from "./ui";

export const practiceAreas = {
  "luyen-ngu-am": {
    title: "Luyện ngữ âm",
    description: "Chọn một âm, quan sát cách đặt môi và lưỡi, rồi ghi âm để kiểm tra.",
    icon: "mic",
    theme: "phonetics",
  },
  "luyen-ngu-dieu": {
    title: "Luyện ngữ điệu",
    description: "Nghe nhịp và trọng âm của mẫu, rồi thu hai lần để tự so sánh.",
    icon: "wave",
    theme: "prosody",
  },
  talk: {
    title: "Hội thoại AI",
    description:
      "Dùng từ đã học để trả lời bằng giọng nói. Nghe gia sư phản hồi rồi tiếp tục cuộc trò chuyện.",
    icon: "talk",
    theme: "conversation",
  },
} as const;

export type PracticeArea = keyof typeof practiceAreas;

export function PracticeBanner({ area }: { area: PracticeArea }) {
  const { title, description, theme } = practiceAreas[area];
  return (
    <header className={`practice-banner practice-${theme}`}>
      <div className="practice-banner-copy">
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="practice-art" aria-hidden="true">
        {area === "luyen-ngu-am" ? (
          <span className="practice-symbol">/ʃ/</span>
        ) : area === "luyen-ngu-dieu" ? (
          <div className="practice-bars">
            {[16, 31, 49, 27, 58, 42, 24, 50, 29, 15].map((height, index) => (
              <span key={index} style={{ height }} />
            ))}
          </div>
        ) : (
          <div className="practice-bubbles">
            <Icon name="talk" size={38} />
            <Icon name="wave" size={27} />
          </div>
        )}
      </div>
    </header>
  );
}
