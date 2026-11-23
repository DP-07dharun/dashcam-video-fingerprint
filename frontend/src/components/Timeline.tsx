import { formatDuration } from "../format";
import type { Segment } from "../types";

interface Props {
  timeline: (number | null)[];
  interval: number;
  threshold?: number;
  segments: Segment[];
}

/** One cell per reference sample: green = frame matches, red = altered, grey = missing. */
export function Timeline({ timeline, interval, threshold = 10, segments }: Props) {
  const total = timeline.length * interval;
  const extra = segments.filter((s) => s.kind === "extra");

  return (
    <div className="timeline">
      <div className="timeline__track" role="img" aria-label="Frame-by-frame comparison timeline">
        {timeline.map((d, i) => {
          const state = d === null ? "missing" : d <= threshold ? "match" : "altered";
          const t = i * interval;
          return (
            <span
              key={i}
              className={`timeline__cell timeline__cell--${state}`}
              title={`${formatDuration(t)} – ${formatDuration(t + interval)}: ${
                d === null ? "missing in submitted video" : `${d}/64 bits differ`
              }`}
            />
          );
        })}
      </div>
      <div className="timeline__axis muted small">
        <span>0:00</span>
        <span>{formatDuration(total)}</span>
      </div>
      <div className="timeline__legend small">
        <span>
          <i className="dot dot--match" /> Matches original
        </span>
        <span>
          <i className="dot dot--altered" /> Altered content
        </span>
        <span>
          <i className="dot dot--missing" /> Missing (cut)
        </span>
        {extra.length > 0 && (
          <span>
            <i className="dot dot--extra" /> Extra footage added
          </span>
        )}
      </div>
    </div>
  );
}

/** Visual barcode of a perceptual-hash sequence: each hash becomes one coloured bar. */
export function HashStrip({ hashes }: { hashes: string[] }) {
  return (
    <div className="hashstrip" role="img" aria-label={`${hashes.length} frame hashes`}>
      {hashes.map((h, i) => {
        const hue = parseInt(h.slice(0, 3), 16) % 360;
        const light = 38 + (parseInt(h.slice(3, 5), 16) % 30);
        return (
          <span
            key={i}
            className="hashstrip__bar"
            style={{ background: `hsl(${hue} 65% ${light}%)` }}
            title={`#${i + 1}: ${h}`}
          />
        );
      })}
    </div>
  );
}
