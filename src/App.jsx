import { useEffect, useRef, useState } from "react";

const BACKEND = "http://localhost:5000";
const BACKEND_URL = `${BACKEND}/process-frame`;

// How many recent frames to vote over when logging an order
const HISTORY_FRAMES = 6;

function mostCommon(values) {
  const counts = {};
  values.forEach((v) => (counts[v] = (counts[v] || 0) + 1));
  return Object.keys(counts).reduce((a, b) => (counts[a] >= counts[b] ? a : b));
}

function average(values) {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

// Single frames flicker, so combine the last few detections of the patron
function stablePatron(history) {
  if (history.length === 0) return null;
  return {
    gender: mostCommon(history.map((r) => r.gender)),
    age: mostCommon(history.map((r) => r.age)),
    is_smiling: history.filter((r) => r.is_smiling).length * 2 > history.length,
    gender_confidence: average(history.map((r) => r.gender_confidence)),
    age_confidence: average(history.map((r) => r.age_confidence)),
    faces_detected: Math.round(average(history.map((r) => r.faces_detected))),
  };
}

// The biggest face is the person closest to the bar
function largestFace(results) {
  return results.reduce((a, b) => (a.box.w * a.box.h >= b.box.w * b.box.h ? a : b));
}

export default function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [error, setError] = useState(null);
  const [processedFrame, setProcessedFrame] = useState(null);
  const [facesDetected, setFacesDetected] = useState(0);
  const [results, setResults] = useState([]);
  const inFlightRef = useRef(false);
  const historyRef = useRef([]);
  const [drinks, setDrinks] = useState([]);
  const [logStatus, setLogStatus] = useState(null);
  const [ordersLogged, setOrdersLogged] = useState(0);

  useEffect(() => {
    fetch(`${BACKEND}/drinks`)
      .then((res) => res.json())
      .then((data) => setDrinks(data.drinks))
      .catch((err) => console.error("Failed to load drinks:", err));
  }, []);

  useEffect(() => {
    let stream;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        setError("Camera access was denied or is unavailable.");
      }
    }

    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (error) return;

    const interval = setInterval(async () => {
      if (inFlightRef.current) return; // skip if previous request still running

      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState !== 4) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const frameDataUrl = canvas.toDataURL("image/jpeg", 0.7);

      inFlightRef.current = true;
      try {
        const res = await fetch(BACKEND_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frame: frameDataUrl }),
        });
        if (!res.ok) throw new Error(`Backend responded ${res.status}`);
        const result = await res.json();
        setProcessedFrame(result.frame);
        setFacesDetected(result.faces_detected);
        setResults(result.results || []);
        if (result.results && result.results.length > 0) {
          const patron = { ...largestFace(result.results), faces_detected: result.faces_detected };
          historyRef.current = [...historyRef.current, patron].slice(-HISTORY_FRAMES);
        } else {
          historyRef.current = [];
        }
      } catch (err) {
        console.error("Failed to process frame:", err);
      } finally {
        inFlightRef.current = false;
      }
    }, 500);

    return () => clearInterval(interval);
  }, [error]);

  const activeRecommendation = results.length > 0 ? largestFace(results).drink_rec : null;
  const topRecs = results.length > 0 ? largestFace(results).drink_recs || [] : [];

  async function logOrder(drink) {
    const patron = stablePatron(historyRef.current);
    if (!patron) {
      setLogStatus("No face in view - order not logged.");
      return;
    }
    try {
      const res = await fetch(`${BACKEND}/log-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...patron, drink }),
      });
      if (!res.ok) throw new Error(`Backend responded ${res.status}`);
      setOrdersLogged((n) => n + 1);
      setLogStatus(`Logged ${drink} for ${patron.gender}, ${patron.age}`);
    } catch (err) {
      console.error("Failed to log order:", err);
      setLogStatus("Failed to log order - is the backend running?");
    }
  }

  return (
    <div style={styles.page}>
      {/* Left half: Drink Recommendations & Analytics */}
      <div style={styles.textPane}>
        <div style={styles.rainbowHeader}>
          <h1 style={styles.mainTitle}>Drink Suggestor</h1>
        </div>

        {/* Dynamic Drink Recommendation Module */}
        <div style={styles.recommendationCard}>
          <div style={styles.drinkNamePlaceholder}>
            {activeRecommendation ? `Suggested: ${activeRecommendation}` : "Awaiting Face Data..."}
          </div>
          
          {/* Image Space Wrapper */}
          <div style={styles.imageSpace}>
            <span style={styles.imageTextPlaceholder}>
              {activeRecommendation ? `${activeRecommendation} Preview` : "Beverage Image Preview"}
            </span>
          </div>

          {topRecs.length > 1 && (
            <div style={styles.topRecs}>
              {topRecs.map((rec) => (
                <div key={rec.drink}>
                  {rec.drink} &mdash; {(rec.probability * 100).toFixed(0)}%
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Order logging: record what the patron actually ordered, for training */}
        <div style={styles.metricsCard}>
          <h3 style={styles.metricsHeading}>What did they order?</h3>
          <div style={styles.drinkButtons}>
            {drinks.map((drink) => (
              <button
                key={drink}
                style={styles.drinkButton}
                disabled={results.length === 0}
                onClick={() => logOrder(drink)}
              >
                {drink}
              </button>
            ))}
          </div>
          {logStatus && (
            <p style={styles.logStatus}>
              {logStatus} ({ordersLogged} logged this session)
            </p>
          )}
        </div>

        {/* Analytics Breakdown Panel */}
        <div style={styles.metricsCard}>
          <h3 style={styles.metricsHeading}>Detected Characteristics</h3>
          {results.length > 0 ? (
            results.map((r, i) => (
              <div key={i} style={styles.metricRow}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                  <div>
                    <strong>Person {i + 1}:</strong> {r.gender} ({(r.gender_confidence * 100).toFixed(0)}%) | 
                    &nbsp;Age {r.age} ({(r.age_confidence * 100).toFixed(0)}%)
                    <div style={{ fontSize: "0.85rem", color: "#666", marginTop: "4px" }}>
                      Suggested: <strong>{r.drink_rec}</strong>
                    </div>
                  </div>
                  {/* Visual indicator tag for the expression */}
                  <div style={r.is_smiling ? styles.smileTag : styles.neutralTag}>
                    {r.is_smiling ? "Smiling" : "Neutral"}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p style={styles.noMetricsText}>Waiting for face data stream...</p>
          )}
        </div>
      </div>

      {/* Right half: webcam feed */}
      <div style={styles.cameraPane}>
        {error ? (
          <p style={styles.errorMessage}>{error}</p>
        ) : (
          <>
            <video ref={videoRef} autoPlay playsInline muted style={styles.hiddenVideo} />
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {processedFrame ? (
              <img src={processedFrame} alt="Processed webcam feed" style={styles.video} />
            ) : (
              <p style={styles.errorMessage}>Connecting to backend...</p>
            )}

            <div style={styles.faceCount}>Faces detected: {facesDetected}</div>
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    width: "100vw",
    height: "100vh",
    margin: 0,
    overflow: "hidden",
  },
  textPane: {
    width: "50%",
    height: "100%",
    display: "flex",
    flexDirection: "column",
    gap: "1.5rem",
    overflowY: "auto",
    background: "#dedbd8", // Soft warm beige/cream
    padding: "2.5rem",
    boxSizing: "border-box",
  },
  rainbowHeader: {
    padding: "0.25rem",
    background: "#dedbd8",
    borderRadius: "12px",
    boxShadow: "0 4px 6px rgba(0,0,0,0.05)",
  },
  mainTitle: {
    margin: 0,
    padding: "0.75rem",
    background: "#dedbd8",
    borderRadius: "10px",
    textAlign: "center",
    fontFamily: "Georgia, 'Times New Roman', serif",
    color: "#4e5d6c",
    fontSize: "1.8rem",
    fontWeight: "bold",
  },
  recommendationCard: {
    background: "#",
    border: "3px solid #dedbd8",
    borderRadius: "16px",
    padding: "2rem",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    boxShadow: "0 6px 12px rgba(108, 76, 62, 0.05)",
  },
  moduleHeading: {
    margin: "0 0 0.5rem 0",
    fontFamily: "Georgia, 'Times New Roman', serif",
    color: "#4e5d6c",
    fontSize: "1.4rem",
    textAlign: "center",
  },
  drinkNamePlaceholder: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "1.1rem",
    color: "#4e5d6c",
    fontWeight: "bold",
    marginBottom: "1.5rem",
    letterSpacing: "0.5px",
  },
  imageSpace: {
    width: "100%",
    maxWidth: "320px",
    height: "220px",
    borderRadius: "12px",
    border: "3px dashed #e3d264", // yella
    backgroundColor: "#dedbd8",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.3s ease",
  },
  imageTextPlaceholder: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    color: "#4e5d6c",
    fontSize: "0.95rem",
    fontWeight: "500",
  },
  topRecs: {
    marginTop: "1rem",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "0.95rem",
    color: "#4e5d6c",
    textAlign: "center",
    lineHeight: 1.6,
  },
  drinkButtons: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
  },
  drinkButton: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "0.95rem",
    color: "#4e5d6c",
    background: "#f6e6b8",
    border: "2px solid #e3d264",
    borderRadius: "8px",
    padding: "0.5rem 0.9rem",
    cursor: "pointer",
  },
  logStatus: {
    margin: "0.75rem 0 0 0",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "0.9rem",
    color: "#4e5d6c",
  },
  metricsCard: {
    background: "#dedbd8", // Super soft retro pastel blue-grey tint
    border: "2px solid #dedbd8",
    borderRadius: "12px",
    padding: "1.25rem",
  },
  metricsHeading: {
    margin: "0 0 0.75rem 0",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "1rem",
    color: "#4e5d6c",
    textTransform: "uppercase",
    letterSpacing: "1px",
  },
  metricRow: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "1rem",
    color: "#4e5d6c",
    padding: "0.5rem 0",
    borderBottom: "1px solid #e2ecf0",
  },
  noMetricsText: {
    margin: 0,
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "0.95rem",
    color: "#7fa6b5",
    fontStyle: "italic",
  },
  cameraPane: {
    width: "50%",
    height: "100%",
    background: "#3e4a5a", // Warm dark slate
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  hiddenVideo: {
    display: "none",
  },
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
  },
  faceCount: {
    position: "absolute",
    bottom: "1rem",
    right: "1rem",
    color: "#fff",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "0.95rem",
    background: "rgba(108, 76, 62, 0.75)",
    padding: "0.4rem 0.8rem",
    borderRadius: "8px",
    boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
  },
  errorMessage: {
    color: "#fff",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "1rem",
    padding: "2rem",
    textAlign: "center",
  },
  smileTag: {
    fontSize: "0.85rem",
    fontWeight: "bold",
    background: "#c5dfb5", // 70's Pastel Green
    color: "#2b4c16",
    padding: "0.2rem 0.6rem",
    borderRadius: "20px",
  },
  neutralTag: {
    fontSize: "0.85rem",
    fontWeight: "bold",
    background: "#f6e6b8", // 70's Pastel Yellow
    color: "#614e1b",
    padding: "0.2rem 0.6rem",
    borderRadius: "20px",
  },
};
