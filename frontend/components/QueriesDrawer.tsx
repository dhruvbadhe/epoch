"use client";
import { useEffect } from "react";
import { MessageCircle, RefreshCw } from "lucide-react";
import { getQueries } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { Drawer } from "./Drawer";
import { Empty, ErrorState, Loading, SourceBadge, SourceNote } from "./ui";
export function QueriesDrawer({ onClose }: { onClose: () => void }) {
  const { result, loading, error, reload } = useResource("queries", getQueries);
  useEffect(() => {
    const timer = setInterval(reload, 10000);
    return () => clearInterval(timer);
  }, []);
  return (
    <Drawer
      title="Conversations from the field."
      subtitle="The last 20 WhatsApp queries. Sender details are masked."
      onClose={onClose}
      footer={
        <>
          <span className="tiny">Refreshes every 10 seconds</span>
          <button className="button secondary" onClick={reload}>
            <RefreshCw size={15} />
            Refresh
          </button>
        </>
      }
    >
      {result && <SourceBadge mock={result.mock} />}
      <SourceNote result={result} />
      {loading ? (
        <Loading text="Loading farmer queries…" />
      ) : error ? (
        <ErrorState error={error} retry={reload} />
      ) : result?.data.length ? (
        result.data.slice(0, 20).map((q, i) => (
          <article className="query-card" key={`${q.time}:${i}`}>
            <header>
              <span>
                <MessageCircle size={16} />
                {q.sender}
              </span>
              <time>
                {new Date(q.time).toLocaleString("en-IN", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
            </header>
            <div className="query-text">{q.text}</div>
            <div className="query-reply">{q.reply}</div>
          </article>
        ))
      ) : (
        <Empty
          title="No queries yet"
          text="Incoming farmer conversations will appear here when the WhatsApp adapter is connected."
        />
      )}
    </Drawer>
  );
}
