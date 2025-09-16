import { useState } from "react";
import AnalysisPage from "./AnalysisPage";

function App() {
  const [username, setUsername] = useState("");
  const [games, setGames] = useState([]);
  const [loadingGames, setLoadingGames] = useState(false);
  const [error, setError] = useState("");
  
  // Navigation states
  const [currentView, setCurrentView] = useState("games"); // "games" or "analysis"
  const [selectedGame, setSelectedGame] = useState(null);

  // Fetch games from backend
  const fetchGames = async () => {
    if (!username.trim()) {
      setError("Please enter a Chess.com username");
      return;
    }

    setLoadingGames(true);
    setError("");

    try {
      const res = await fetch(`http://localhost:5000/games/${username.trim()}`);
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || `Failed to fetch games: ${res.status}`);
      }
      
      const data = await res.json();
      setGames(data.games || []);
      
      if (data.games && data.games.length === 0) {
        setError("No games found for this user");
      }
    } catch (err) {
      setError("Error fetching games: " + err.message);
      setGames([]);
    } finally {
      setLoadingGames(false);
    }
  };

  // Navigate to analysis page
  const goToAnalysis = (gameData) => {
    // Pass moves from PGN to AnalysisPage
    setSelectedGame(gameData);
    setCurrentView("analysis");
  };

  // Navigate back to games list
  const goBackToGames = () => {
    setCurrentView("games");
    setSelectedGame(null);
  };

  // Render analysis page
  if (currentView === "analysis" && selectedGame) {
    return (
      <AnalysisPage 
        gameData={selectedGame} 
        onBack={goBackToGames}
      />
    );
  }

  // Render games list (main page)
  return (
    <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto", backgroundColor: "#f8f9fa", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ 
        textAlign: "center", 
        marginBottom: "30px",
        backgroundColor: "white",
        padding: "30px",
        borderRadius: "15px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.1)"
      }}>
        <h1 style={{ 
          margin: "0 0 10px 0", 
          color: "#333",
          fontSize: "2.5em",
          fontWeight: "bold"
        }}>
          ♟️ Chess.com Game Analyzer
        </h1>
        <p style={{ 
          color: "#666", 
          fontSize: "1.2em", 
          margin: 0 
        }}>
          Fetch your Chess.com games and get professional Stockfish analysis
        </p>
      </div>
      
      {error && (
        <div style={{ 
          color: "#d32f2f", 
          marginBottom: "20px", 
          padding: "15px", 
          border: "2px solid #d32f2f", 
          borderRadius: "8px",
          backgroundColor: "#ffebee",
          textAlign: "center",
          fontWeight: "bold"
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Game Fetching Section */}
      <div style={{ 
        marginBottom: "30px", 
        padding: "30px", 
        backgroundColor: "white",
        borderRadius: "15px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.1)"
      }}>
        <h2 style={{ 
          margin: "0 0 20px 0", 
          color: "#333",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          🔥 Fetch Your Chess.com Games
        </h2>
        
        <div style={{ 
          display: "flex", 
          alignItems: "center", 
          gap: "15px", 
          marginBottom: "20px",
          flexWrap: "wrap"
        }}>
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="Enter Chess.com username"
            style={{ 
              padding: "12px 16px", 
              borderRadius: "8px", 
              border: "2px solid #ddd",
              fontSize: "16px",
              minWidth: "250px",
              outline: "none",
              transition: "border-color 0.2s"
            }}
            onFocus={e => e.target.style.borderColor = "#2196F3"}
            onBlur={e => e.target.style.borderColor = "#ddd"}
            onKeyPress={e => e.key === 'Enter' && fetchGames()}
          />
          <button 
            onClick={fetchGames} 
            disabled={loadingGames}
            style={{ 
              padding: "12px 24px", 
              borderRadius: "8px",
              border: "none",
              backgroundColor: loadingGames ? "#ccc" : "#4CAF50",
              color: "white",
              cursor: loadingGames ? "not-allowed" : "pointer",
              fontSize: "16px",
              fontWeight: "bold",
              transition: "background-color 0.2s",
              display: "flex",
              alignItems: "center",
              gap: "8px"
            }}
          >
            {loadingGames ? "⏳ Loading..." : "🚀 Fetch Games"}
          </button>
        </div>

        {loadingGames && (
          <div style={{ 
            textAlign: "center", 
            padding: "20px",
            color: "#666",
            fontSize: "1.1em"
          }}>
            <div style={{ marginBottom: "10px" }}>🔍 Fetching your recent games...</div>
            <div style={{ 
              width: "100%", 
              height: "6px", 
              backgroundColor: "#e0e0e0", 
              borderRadius: "3px",
              overflow: "hidden"
            }}>
              <div style={{ 
                width: "40%", 
                height: "100%", 
                backgroundColor: "#4CAF50",
                animation: "loading 2s infinite ease-in-out",
                borderRadius: "3px"
              }}></div>
            </div>
          </div>
        )}

        {games.length > 0 && (
          <div>
            <h3 style={{ 
              margin: "0 0 20px 0", 
              color: "#333",
              display: "flex",
              alignItems: "center",
              gap: "10px"
            }}>
              🎮 Your Last {games.length} Games
            </h3>
            <div style={{ 
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))",
              gap: "20px",
              maxHeight: "600px", 
              overflowY: "auto",
              padding: "10px"
            }}>
              {games.map((gameData, i) => (
                <div 
                  key={i} 
                  style={{ 
                    padding: "20px", 
                    border: "2px solid #e0e0e0", 
                    borderRadius: "12px",
                    backgroundColor: "white",
                    boxShadow: "0 2px 10px rgba(0,0,0,0.08)",
                    transition: "all 0.3s ease",
                    cursor: "pointer"
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.boxShadow = "0 4px 20px rgba(0,0,0,0.15)";
                    e.currentTarget.style.borderColor = "#2196F3";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.boxShadow = "0 2px 10px rgba(0,0,0,0.08)";
                    e.currentTarget.style.borderColor = "#e0e0e0";
                  }}
                >
                  <div style={{ marginBottom: "15px" }}>
                    <div style={{ 
                      fontSize: "1.1em", 
                      fontWeight: "bold", 
                      color: "#333",
                      marginBottom: "8px"
                    }}>
                      🏆 Game {i + 1}
                    </div>
                    <div style={{ 
                      fontSize: "1em", 
                      color: "#555",
                      marginBottom: "5px"
                    }}>
                      <strong>⚪ {gameData.white?.username}</strong> ({gameData.white?.rating}) 
                      <span style={{ margin: "0 8px", color: "#999" }}>vs</span>
                      <strong>⚫ {gameData.black?.username}</strong> ({gameData.black?.rating})
                    </div>
                    <div style={{ 
                      display: "flex", 
                      gap: "15px", 
                      fontSize: "0.9em", 
                      color: "#666",
                      marginBottom: "15px"
                    }}>
                      <span>📅 {gameData.end_time && new Date(gameData.end_time * 1000).toLocaleDateString()}</span>
                      <span>⏱️ {gameData.time_control}</span>
                      <span>🎯 {gameData.rated ? "Rated" : "Casual"}</span>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => goToAnalysis(gameData)}
                    style={{
                      width: "100%",
                      padding: "12px 20px",
                      borderRadius: "8px",
                      border: "none",
                      backgroundColor: "#2196F3",
                      color: "white",
                      cursor: "pointer",
                      fontSize: "16px",
                      fontWeight: "bold",
                      transition: "background-color 0.2s",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "8px"
                    }}
                    onMouseEnter={e => e.target.style.backgroundColor = "#1976D2"}
                    onMouseLeave={e => e.target.style.backgroundColor = "#2196F3"}
                  >
                    🔍 Analyze with Stockfish
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes loading {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(0%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}

export default App;