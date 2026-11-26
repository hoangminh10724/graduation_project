import { notFound } from "next/navigation";
import { Screen } from "@/components/screen";
import { sections, type Section } from "@/lib/content";

export function generateStaticParams() {
  return Object.keys(sections).map((section) => ({ section }));
}
export const dynamicParams = false;

export function generateMetadata({ params }: { params: { section: string } }) {
  return { title: sections[params.section as Section]?.[0] ?? "WordSpeak" };
}

export default function SectionPage({ params }: { params: { section: string } }) {
  if (!Object.hasOwn(sections, params.section)) notFound();
  return <Screen section={params.section as Section} />;
}
