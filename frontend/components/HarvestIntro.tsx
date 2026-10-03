"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUpRight, Leaf, MoveDown, Sprout } from "lucide-react";

const chapters = [
  {
    name: "A little beginning",
    title: "Every good harvest begins with care.",
    copy: "You put the work into growing it. Let’s put the same care into what comes next.",
  },
  {
    name: "Room to grow",
    title: "A little clarity goes a long way.",
    copy: "Bring your crop, its condition and your cash needs together. Find the options that fit your harvest.",
  },
  {
    name: "The next step",
    title: "Make the most of what you’ve grown.",
    copy: "Compare markets, understand the costs, and plan a better next step for your harvest.",
  },
];

export function openWorkspace() {
  const target = document.getElementById("workspace-start");
  if (!target) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({
    behavior: reduced ? "instant" : "smooth",
    block: "start",
  });
  target.focus({ preventScroll: true });
}

export function HarvestIntro({
  timeline,
}: {
  timeline?: { name: string; title: string; copy: string }[];
}) {
  const story = timeline?.length ? timeline : chapters;
  const root = useRef<HTMLElement>(null);
  const [chapter, setChapter] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const chapterRef = useRef(0);

  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    const update = () => {
      frame = 0;
      const bounds = element.getBoundingClientRect();
      const distance = Math.max(
        1,
        element.offsetHeight - window.innerHeight + 88,
      );
      const progress = media.matches
        ? 1
        : Math.max(0, Math.min(1, (88 - bounds.top) / distance));
      element.style.setProperty("--growth", String(progress));
      element.style.setProperty("--stem", String(Math.min(1, progress / 0.7)));
      element.style.setProperty(
        "--roots",
        String(Math.min(1, progress / 0.28)),
      );
      const next = Math.min(
        story.length - 1,
        Math.floor(progress * story.length),
      );
      if (next !== chapterRef.current) {
        chapterRef.current = next;
        setChapter(next);
      }
    };
    const queue = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    const preferenceChanged = () => {
      setReducedMotion(media.matches);
      update();
    };
    preferenceChanged();
    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("resize", queue);
    media.addEventListener("change", preferenceChanged);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", queue);
      window.removeEventListener("resize", queue);
      media.removeEventListener("change", preferenceChanged);
    };
  }, [story.length]);

  function goToChapter(index: number) {
    const element = root.current;
    if (!element) return;
    const top = window.scrollY + element.getBoundingClientRect().top - 88;
    const distance = Math.max(
      1,
      element.offsetHeight - window.innerHeight + 88,
    );
    window.scrollTo({
      top: Math.max(
        0,
        top + distance * (index / Math.max(1, story.length - 1)),
      ),
      behavior: "smooth",
    });
  }

  return (
    <section
      className="harvest-intro"
      ref={root}
      aria-label="From seed to harvest"
      data-chapter={chapter}
    >
      <div className="harvest-sticky">
        <div className="intro-topline">
          <span>
            <Sprout size={15} /> SEVEN DAYS OF REPORTED PRICES
          </span>
          <button onClick={openWorkspace}>
            Open workspace <ArrowUpRight size={16} />
          </button>
        </div>
        <div className="intro-composition">
          <div className="intro-copy">
            <span className="intro-kicker">
              <span /> FOR THE PEOPLE BEHIND THE HARVEST
            </span>
            <h2>
              From seed
              <br /> to a clearer
              <br />
              <em>decision.</em>
            </h2>
            <p className="intro-description">
              Follow the last seven calendar days.
              <br /> These are reported prices, not realised profit.
            </p>
            <button className="intro-cta" onClick={openWorkspace}>
              Market overview <ArrowUpRight size={18} />
            </button>
            <div className="intro-crops">
              <span>Onion</span>
              <i /> <span>Tomato</span>
              <i /> <span>Soybean</span>
              <span className="intro-region">Made for Maharashtra</span>
            </div>
          </div>
          <div className="botanical-scene" aria-hidden="true">
            <div className="botanical-halo" />
            <span className="specimen-label">REPORTED PRICE TIMELINE</span>
            <svg
              className="growth-illustration"
              viewBox="0 0 540 490"
              fill="none"
            >
              <defs>
                <linearGradient id="leaf-fill" x1="0" y1="0" x2="1" y2="1">
                  <stop stopColor="#779679" />
                  <stop offset="1" stopColor="#216c4c" />
                </linearGradient>
                <linearGradient id="soil-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop stopColor="#e5e9e0" stopOpacity=".6" />
                  <stop offset="1" stopColor="#f7f8f3" stopOpacity="0" />
                </linearGradient>
              </defs>
              <circle
                cx="270"
                cy="230"
                r="182"
                stroke="#dce5d6"
                strokeDasharray="2 9"
              />
              <circle
                cx="270"
                cy="230"
                r="150"
                stroke="#e5e9e0"
                strokeWidth=".7"
              />
              <path
                d="M57 362Q270 308 483 362V460H57Z"
                fill="url(#soil-fill)"
              />
              <path
                d="M48 360Q270 323 492 360M82 382Q270 348 458 382M120 405Q270 378 420 405M163 430Q270 410 377 430"
                stroke="#b8c9ae"
                strokeWidth="1"
              />
              <path
                className="plant-root"
                pathLength="1"
                d="M270 344C273 365 253 384 267 415M270 362C247 368 239 383 231 396M267 382C293 389 295 405 305 415M264 395L250 420M250 377L228 379M289 394L310 392"
                stroke="#8d9f79"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <ellipse
                className="seed-shadow"
                cx="270"
                cy="348"
                rx="39"
                ry="8"
                fill="#216c4c"
                opacity=".09"
              />
              <g className="plant-seed">
                <path
                  d="M251 335C246 317 261 300 282 300C296 318 286 341 270 345C260 347 254 343 251 335Z"
                  fill="#9b762c"
                />
                <path
                  d="M257 338Q265 316 279 305"
                  stroke="#f7f8f3"
                  strokeOpacity=".6"
                  strokeWidth="1.4"
                />
              </g>
              <path
                className="plant-stem"
                pathLength="1"
                d="M270 344C257 305 282 274 269 239C258 208 272 174 267 128"
                stroke="#216c4c"
                strokeWidth="5"
                strokeLinecap="round"
              />
              <g className="plant-leaf leaf-one">
                <path
                  d="M268 286C222 293 190 266 184 232C226 229 263 248 268 286Z"
                  fill="url(#leaf-fill)"
                />
                <path
                  d="M268 286Q222 262 193 239"
                  stroke="#c5d8b9"
                  strokeWidth="1.2"
                />
                <path
                  d="M229 264L222 244M242 272L218 275"
                  stroke="#c5d8b9"
                  strokeOpacity=".55"
                />
              </g>
              <g className="plant-leaf leaf-two">
                <path
                  d="M270 257C313 264 346 235 352 201C308 200 278 220 270 257Z"
                  fill="#216c4c"
                />
                <path
                  d="M271 256Q310 237 344 209"
                  stroke="#c5d8b9"
                  strokeWidth="1.2"
                />
                <path
                  d="M307 236L317 215M321 225L340 227"
                  stroke="#c5d8b9"
                  strokeOpacity=".55"
                />
              </g>
              <g className="plant-leaf leaf-three">
                <path
                  d="M267 212C230 214 209 191 204 161C240 161 264 181 267 212Z"
                  fill="#779679"
                />
                <path
                  d="M265 209Q237 187 211 169"
                  stroke="#edf5ec"
                  strokeOpacity=".6"
                  strokeWidth="1.1"
                />
              </g>
              <g className="plant-leaf leaf-four">
                <path
                  d="M268 181C300 181 323 157 324 132C293 136 269 153 268 181Z"
                  fill="url(#leaf-fill)"
                />
                <path d="M271 179L317 141" stroke="#c5d8b9" strokeWidth="1.1" />
              </g>
              <g className="plant-leaf leaf-five">
                <path
                  d="M267 141C243 126 241 99 252 78C275 98 281 119 267 141Z"
                  fill="#216c4c"
                />
                <path d="M267 138L254 88" stroke="#c5d8b9" strokeWidth="1.1" />
              </g>
              <g className="growth-sparkles" stroke="#9b762c" strokeWidth="1.2">
                <path d="M354 107v12m-6-6h12M172 175v8m-4-4h8M335 295v10m-5-5h10" />
                <circle cx="197" cy="112" r="2" fill="#9b762c" stroke="none" />
              </g>
              <path
                d="M135 322H93L76 306M356 164H399L421 144"
                stroke="#a4b89b"
                strokeWidth=".8"
              />
              <circle cx="135" cy="322" r="2.5" fill="#779679" />
              <circle cx="356" cy="164" r="2.5" fill="#779679" />
            </svg>
            <span className="scene-note note-care">
              A little care
              <br />
              <b>at every step.</b>
            </span>
            <span className="scene-note note-potential">
              Rooted in effort.
              <br />
              <b>Growing possibility.</b>
            </span>
            <div className="botanical-stamp">
              <Leaf size={15} />
              <span>
                Grown with care.
                <br />
                <strong>Planned with SahiDaam.</strong>
              </span>
            </div>
          </div>
        </div>
        <div className="intro-bottom">
          <div className="growth-caption" aria-live="polite">
            <span className="chapter-number">0{chapter + 1}</span>
            <div key={chapter}>
              <strong>{story[chapter].title}</strong>
              <p>{story[chapter].copy}</p>
            </div>
          </div>
          <div className="growth-controls" aria-label="Growth story chapters">
            {story.map((item, index) => (
              <button
                key={item.name}
                onClick={() => goToChapter(index)}
                aria-label={`Show chapter ${index + 1}: ${item.name}`}
                aria-pressed={chapter === index}
                disabled={reducedMotion}
              >
                <span>0{index + 1}</span>
                <i />
              </button>
            ))}
          </div>
        </div>
        <div className="intro-scroll-cue">
          <MoveDown size={15} />
          <span>
            {reducedMotion
              ? "Your next step is below"
              : "Scroll a little. Watch it grow."}
          </span>
          <ArrowDown size={12} />
        </div>
      </div>
    </section>
  );
}
