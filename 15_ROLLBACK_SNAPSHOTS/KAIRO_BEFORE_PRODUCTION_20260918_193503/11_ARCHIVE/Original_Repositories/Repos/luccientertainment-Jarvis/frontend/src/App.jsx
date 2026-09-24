import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("idle");
  const [view, setView] = useState("home");
  const [completedResearch, setCompletedResearch] = useState([]);
  const [selectedResearch, setSelectedResearch] = useState(null);
  const [researchSummary, setResearchSummary] = useState({ completed_count: 0, active_count: 0, active_research: null,});
  const [calendarSummary, setCalendarSummary] = useState({ event_count: 0, events: [],});
  const [gmailSummary, setGmailSummary] = useState({ unread_count: 0,});  
  const normalizedStatus = status === "online" ? "idle" : status;
  const formatDate = (dateValue) => {
    if (!dateValue) return "Unknown date";

    const date = new Date(dateValue);

    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };
  const openCompletedResearch = () => {
  fetch("http://localhost:8000/research/show-completed")
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to trigger completed research view.");
      }

    })
    .catch((err) => {
      console.error("Error opening completed research:", err);
    });
};

  useEffect(() => {
  const socket = new WebSocket("ws://localhost:8000/ws");
  const loadGmailSummary = () => {
  fetch("http://localhost:8000/gmail/summary")
    .then((response) => response.json())
    .then((data) => {
      setGmailSummary({
        unread_count: data.unread_count || 0,
      });
    })
    .catch((err) => {
      console.error("Error loading Gmail summary:", err);
    });
};
   
  const loadCalendarSummary = () => {
    fetch("http://localhost:8000/calendar/summary")
      .then((response) => response.json())
      .then((data) => {
        setCalendarSummary({
          event_count: data.event_count || 0,
          events: data.events || [],
        });
      })
      .catch((err) => {
        console.error("Error loading calendar summary:", err);
      });
  };

  const loadResearchSummary = () => {
    fetch("http://localhost:8000/research/summary")
      .then((response) => response.json())
      .then((data) => {
        setResearchSummary({
          completed_count: data.completed_count || 0,
          active_count: data.active_count || 0,
          active_research: data.active_research || null,
        });
      })
      .catch((err) => {
        console.error("Error loading research summary:", err);
      });
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === "show_completed_research") {
        setCompletedResearch(data.items || []);
        setSelectedResearch(null);
        setView("completedResearch");

        // Refresh badge counts when completed research opens
        loadResearchSummary();
        return;
      }

      if (data.type === "home") {
        setSelectedResearch(null);
        setView("home");

        // Refresh badge counts when returning home
        loadResearchSummary();
        return;
      }

      if (data.type === "gmail_summary") {
        setGmailSummary({
          unread_count: data.unread_count || 0,
        });
        return;
      }

      if (data.type === "calendar_summary") {
        setCalendarSummary({
          event_count: data.event_count || 0,
          events: data.events || [],
        });
        return;
}

      if (data.type === "research_summary") {
        setResearchSummary({
          completed_count: data.completed_count || 0,
          active_count: data.active_count || 0,
          active_research: data.active_research || null,
        });
        return;
      }

      if (data.status) {
        setStatus(data.status.toLowerCase());
      }
    } catch (err) {
      console.error("Error parsing WebSocket message:", err);
    }
  };

  socket.onclose = () => setStatus("offline");
  socket.onerror = () => setStatus("offline");

  // Run once immediately
  loadResearchSummary();
  loadGmailSummary();
  loadCalendarSummary();

  // Then keep checking every 3 seconds
  const summaryInterval = setInterval(loadResearchSummary, 3000);
  const gmailInterval = setInterval(loadGmailSummary, 10000);
  const calendarInterval = setInterval(loadCalendarSummary, 60000);

  return () => {
    socket.close();
    clearInterval(summaryInterval);
    clearInterval(gmailInterval);
    clearInterval(calendarInterval);
  };
}, []);

  if (view === "completedResearch") {
    return (
      <div className="screen hud-screen research-screen">
        <div className="hud-grid"></div>
        <div className="scan-line"></div>
       
        <button
          type="button"
          className="research-page-close"
          onClick={() => {
            setSelectedResearch(null);
            setView("home");
          }}
        >
          Close
        </button>

        <h1 className="research-title">
          Completed Research
        </h1>

        <div className="research-panel">
          {completedResearch.length === 0 ? (
            <p>No completed research yet.</p>
          ) : (
            completedResearch.map((item, index) => (
              <div
                className="research-card"
                key={index}
                onClick={() => setSelectedResearch(item)}
              >
                <h2>{item.topic}</h2>

                <p className="research-date">{formatDate(item.created_at)}</p>

                <p className="research-preview">
                  {item.summary || item.report}
                </p>
              </div>
            ))
          )}
        </div>

        {selectedResearch && (
          <div
            className="research-modal-backdrop"
            onClick={() => setSelectedResearch(null)}
          >
            <div
              className="research-modal"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="research-close"
                onClick={() => setSelectedResearch(null)}
              >
                ×
              </button>

              <h2>{selectedResearch.topic}</h2>

              <p className="research-date">
                {formatDate(selectedResearch.created_at)}
              </p>

              <div className="research-full-report">
                {selectedResearch.report || selectedResearch.summary}
              </div>

              {selectedResearch.facts?.length > 0 && (
                <>
                  <h3>Facts</h3>

                  <div className="research-facts">
                    {selectedResearch.facts.map((fact, index) => (
                      <div className="research-fact" key={index}>
                        <h4>{fact.query}</h4>
                        <p>{fact.facts}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {selectedResearch.sources?.length > 0 && (
                <>
                  <h3>Sources</h3>

                  <div className="research-sources">
                    {selectedResearch.sources.map((source, index) => (
                      <a
                        key={index}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {source.title || source.url}
                      </a>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`screen hud-screen ${normalizedStatus}`}>
      <div className="hud-grid"></div>
      <div className="scan-line"></div>

      <div className="corner corner-top-left"></div>
      <div className="corner corner-top-right"></div>
      <div className="corner corner-bottom-left"></div>
      <div className="corner corner-bottom-right"></div>

      
      <div className="core reactor-core">
        <div className="hud-ring hud-ring-outer"></div>
        <div className="hud-ring hud-ring-mid"></div>
        <div className="hud-ring hud-ring-inner"></div>

        <div className="reactor-orb">
          <div className="reactor-triangle"></div>
          <div className="reactor-center"></div>
        </div>
      </div>

      <div className="hud-top-badge-row">
        <div className="hud-badge-left">
          <button
            type="button"
            className="research-hud-badge research-clickable"
            onClick={openCompletedResearch}
          >
            Completed Research: {researchSummary.completed_count}
          </button>

          {researchSummary.active_count > 0 && (
            <div className="research-hud-badge active">
              Active Research: {researchSummary.active_count}
              {researchSummary.active_research?.topic && (
                <span>{researchSummary.active_research.topic}</span>
              )}
            </div>
          )}
        </div>

        <div className="hud-badge-right">
          {gmailSummary.unread_count > 0 && (
            <div className="research-hud-badge email has-email">
              New Email: {gmailSummary.unread_count}
            </div>
          )}

          {calendarSummary.event_count > 0 && (
            <div className="research-hud-badge calendar has-calendar">
              Calendar: {calendarSummary.event_count}
            </div>
          )}
        </div>
      

      </div>
            

      {normalizedStatus === "speaking" && (
        <div className="voice-bars">
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
        </div>
      )}

      {normalizedStatus === "thinking" && (
        <div className="thinking-text">PROCESSING</div>
      )}
    </div>
  );
}

export default App;