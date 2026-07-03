import { useEffect, useRef, useState } from "react";

const PARAGRAPH = `Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium
doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore
veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim
ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia
consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.`;

const BACKEND_URL = "http://localhost:5000/process-frame";

export default function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [error, setError] = useState(null);
  const [processedFrame, setProcessedFrame] = useState(null);
  const [facesDetected, setFacesDetected] = useState(0);
  const [results, setResults] = useState([]); // <-- NEW: holds gender + age results

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
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState !== 4) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const frameDataUrl = canvas.toDataURL("image/jpeg", 0.7);

      try {
        const res = await fetch(BACKEND_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frame: frameDataUrl }),
        });
        const result = await res.json();
        setProcessedFrame(result.frame);
        setFacesDetected(result.faces_detected);
        setResults(result.results || []); // <-- NEW: update results state
      } catch (err) {
        console.error("Failed to process frame:", err);
      }
    }, 200);

    return () => clearInterval(interval);
  }, [error]);

  return (
    <div style={styles.page}>
      {/* Left half: wall of text */}
      <div style={styles.textPane}>
        {/* NEW: banner showing detected gender/age, placed above the paragraphs */}
        {results.length > 0 && (
          <div style={styles.genderBanner}>
            {results.map((r, i) => (
              <div key={i}>
                Person {i + 1}: {r.gender} ({(r.gender_confidence * 100).toFixed(0)}%),{" "}
                Age {r.age} ({(r.age_confidence * 100).toFixed(0)}%)
              </div>
            ))}
          </div>
        )}

        <div style={styles.textColumns}>
          {Array.from({ length: 8 }).map((_, i) => (
            <p key={i} style={styles.paragraph}>
              {PARAGRAPH}
            </p>
          ))}
        </div>
      </div>

      {/* Right half: webcam feed */}
      <div style={styles.cameraPane}>
        {error ? (
          <p style={styles.errorMessage}>{error}</p>
        ) : (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={styles.hiddenVideo}
            />
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {processedFrame ? (
              <img
                src={processedFrame}
                alt="Processed webcam feed"
                style={styles.video}
              />
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
    overflow: "hidden",
    background: "#f4f1ea",
    padding: "2rem",
    boxSizing: "border-box",
  },
  genderBanner: {
    fontFamily: "sans-serif",
    fontSize: "1rem",
    fontWeight: "bold",
    color: "#2b2b2b",
    marginBottom: "1rem",
    padding: "0.5rem",
    background: "#e8e4d8",
    borderRadius: "4px",
  },
  textColumns: {
    columnCount: 2,
    columnGap: "1.5rem",
    height: "100%",
  },
  paragraph: {
    fontFamily: "Georgia, 'Times New Roman', serif",
    fontSize: "0.85rem",
    lineHeight: 1.5,
    textAlign: "justify",
    color: "#2b2b2b",
    marginTop: 0,
    marginBottom: "1rem",
  },
  cameraPane: {
    width: "50%",
    height: "100%",
    background: "#000",
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
    transform: "scaleX(-1)",
  },
  faceCount: {
    position: "absolute",
    bottom: "1rem",
    right: "1rem",
    color: "#fff",
    fontFamily: "sans-serif",
    fontSize: "0.9rem",
    background: "rgba(0,0,0,0.5)",
    padding: "0.3rem 0.6rem",
    borderRadius: "4px",
  },
  errorMessage: {
    color: "#fff",
    fontFamily: "sans-serif",
    fontSize: "1rem",
    padding: "2rem",
    textAlign: "center",
  },
};