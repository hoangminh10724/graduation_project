import Image from "next/image";
import Link from "next/link";
import { Action, Icon } from "@/components/ui";
import { practiceAreas } from "@/components/practice-banner";

const vocabulary = [
  ["ipa", "grid", "Bản đồ IPA", "Nghe các từ ví dụ và tìm những âm hay nhầm."],
  ["tu-dien", "book", "Từ điển", "Tra nghĩa, nghe cách đọc và xem từ trong câu."],
  ["tu-da-luu", "bookmark", "Từ đã lưu", "Xem lại những từ bạn muốn đưa vào buổi luyện tiếp theo."],
];

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">
            <Icon name="wave" size={17} /> LUYỆN NÓI TIẾNG ANH
          </span>
          <h1>
            Nói tiếng Anh
            <br />
            <em>tự tin hơn.</em>
          </h1>
          <p>
            Bắt đầu từ một âm. Nghe lại bản thu, thử một điều chỉnh và dùng từ vừa học trong hội thoại.
          </p>
          <div className="row">
            <Action href="/luyen-ngu-am" primary icon="mic">
              Bắt đầu luyện
            </Action>
            <Action href="/ipa">Khám phá IPA</Action>
          </div>
        </div>
        <Image
          src="/wordspeak-hero.svg"
          width={540}
          height={342}
          priority
          alt=""
          className="hero-image"
        />
      </section>
      <section className="stack home-section">
        <h2>Luyện tập</h2>
        <div className="grid cards">
          {Object.entries(practiceAreas).map(([href, { title, description, icon, theme }]) => (
            <Link
              className={`panel learn-card featured-card practice-${theme}`}
              href={`/${href}`}
              key={href}
            >
              <span className="tile">
                <Icon name={icon} size={25} />
              </span>
              <h3>{title}</h3>
              <p>{description}</p>
            </Link>
          ))}
        </div>
      </section>
      <section className="stack home-section">
        <h2>Từ vựng</h2>
        <div className="grid cards">
          {vocabulary.map(([href, icon, title, description]) => (
            <Link className="panel learn-card" href={"/" + href} key={href}>
              <span className="tile">
                <Icon name={icon} />
              </span>
              <h3>{title}</h3>
              <p>{description}</p>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
