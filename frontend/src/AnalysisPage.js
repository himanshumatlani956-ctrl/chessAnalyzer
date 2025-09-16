// AnalysisPage.js - Fixed version with working piece movement

import { useState, useEffect, useCallback } from "react";
import { Chessboard } from "react-chessboard";
import { Chess } from "chess.js";

function AnalysisPage({ gameData, onBack, playable = false, moves }) {
  // Core game state - Single source of truth
  const [gameInstance, setGameInstance] = useState(() => new Chess());
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [boardFen, setBoardFen] = useState("start");

  // Analysis data
  const [gameAnalysis, setGameAnalysis] = useState([]);
  const [allMoves, setAllMoves] = useState([]);
  const [currentEval, setCurrentEval] = useState(0);

  // UI state
  const [isAnalyzingGame, setIsAnalyzingGame] = useState(false);
  const [error, setError] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [playInterval, setPlayInterval] = useState(null);

  // Debug logging
  const debugLog = (message, data = null) => {
    console.log(`[AnalysisPage] ${message}`, data || '');
  };

  // Helper function to safely render object properties
  const renderPlayerInfo = (player) => {
    if (!player) return "Unknown";
    if (typeof player === "string") return player;
    if (typeof player === "object") {
      return player.username || player.name || player.display_name || "Unknown Player";
    }
    return String(player);
  };

  // Helper function to safely render any value
  const safeRender = (value) => {
    if (value === null || value === undefined) return "";
    if (typeof value === "string" || typeof value === "number") return value;
    if (typeof value === "object") {
      return JSON.stringify(value);
    }
    return String(value);
  };

  // Initialize game analysis
  useEffect(() => {
    if (gameData?.pgn) {
      analyzeCompleteGame(gameData.pgn);
    }
  }, [gameData]);

  // Extract moves from PGN fallback
  useEffect(() => {
    if (moves && typeof moves === "string" && allMoves.length === 0) {
      const extractedMoves = extractMovesFromPGN(moves);
      setAllMoves(extractedMoves);
      debugLog("Extracted moves from PGN", extractedMoves.slice(0, 5));
    }
  }, [moves, allMoves.length]);

  // Auto-play functionality
  useEffect(() => {
    if (isPlaying && currentMoveIndex < allMoves.length - 1) {
      const interval = setTimeout(() => {
        goToMove(currentMoveIndex + 1);
      }, 700);
      setPlayInterval(interval);
    } else if (isPlaying) {
      setIsPlaying(false);
    }

    return () => {
      if (playInterval) clearTimeout(playInterval);
    };
  }, [isPlaying, currentMoveIndex, allMoves.length]);

  // Extract moves from PGN string
  const extractMovesFromPGN = (pgnString) => {
    const movePattern = /(\d+\.+|\d+\.\.\.|[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8](?:=[NBRQ])?[+#]?|O-O-O|O-O)/g;
    let cleanPgn = pgnString
      .replace(/\[([^\]]+)\]/g, '')
      .replace(/\{[^}]*\}/g, '')
      .replace(/\([^)]*\)/g, '')
      .replace(/\$\d+/g, '')
      .replace(/[!?+#]/g, '')
      .replace(/\s+/g, ' ')
      .trim();

    const allTokens = cleanPgn.match(movePattern) || [];
    return allTokens.filter(token => {
      return !/^\d+\.+$/.test(token) && !/^\d+\.\.\.$/.test(token);
    });
  };

  // Analyze complete game
  const analyzeCompleteGame = async (pgn) => {
    setIsAnalyzingGame(true);
    setError("");
    setGameAnalysis([]);
    setAllMoves([]);
    resetToStart();

    try {
      debugLog("Starting game analysis...");
      const response = await fetch("http://localhost:5000/analyze-game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pgn }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Analysis failed: ${response.status}`);
      }

      const data = await response.json();
      setGameAnalysis(data.analysis || []);
      setAllMoves(data.moves || []);
      console.log("✅ Moves received:", data.moves?.length, data.moves);

      debugLog("Analysis completed", {
        analyzedMoves: data.analysis?.length || 0,
        totalMoves: data.moves?.length || 0
      });
    } catch (err) {
      setError("Failed to analyze game: " + err.message);
      debugLog("Analysis error", err.message);
    } finally {
      setIsAnalyzingGame(false);
    }
  };

  // Reset to starting position
  const resetToStart = useCallback(() => {
    debugLog("Resetting to start position");
    const newGame = new Chess();
    setCurrentMoveIndex(-1);
    setCurrentEval(0);
    setGameInstance(newGame);
    setBoardFen("start");
  }, []);

  // Navigate to specific move - COMPLETELY FIXED
  const goToMove = useCallback((targetMoveIndex) => {
    debugLog(`Navigating to move ${targetMoveIndex + 1}`);

    // Validate move index
    const clampedIndex = Math.max(-1, Math.min(allMoves.length - 1, targetMoveIndex));

    if (clampedIndex === -1) {
      resetToStart();
      return;
    }

    // Create fresh game and replay moves
    const freshGame = new Chess();
    let successCount = 0;

    for (let i = 0; i <= clampedIndex; i++) {
      const move = allMoves[i];
      if (!move) break;

      try {
        let result = null;
        if (typeof move === "string") {
          result = freshGame.move(move, { sloppy: true });
        } else if (move.san) {
          result = freshGame.move(move.san, { sloppy: true });
        } else if (move.from && move.to) {
          result = freshGame.move({
            from: move.from,
            to: move.to,
            promotion: move.promotion || "q"
          });
        }

        if (result) {
          successCount++;
          console.log(`✅ Applied move ${i + 1}:`, result.san, "→ FEN:", freshGame.fen());
          debugLog(`Applied move ${i + 1}`, result.san);
        } else {
          debugLog(`Failed to apply move ${i + 1}`, move);
          break;
        }
      } catch (error) {
        debugLog(`Error on move ${i + 1}`, error.message);
        break;
      }
    }

    // Update evaluation
    const newEval = gameAnalysis[clampedIndex]?.actualEval ||
      gameAnalysis[clampedIndex]?.score || 0;

    // Update all states
    setCurrentMoveIndex(clampedIndex);
    setCurrentEval(newEval);

    // 🟢 Update boardFen (forces to redraw)
    setBoardFen(freshGame.fen());

    // Keep Chess object for logic
    setGameInstance(freshGame);

    debugLog("Updating board state", {
      moveIndex: clampedIndex + 1,
      appliedMoves: successCount,
      fen: freshGame.fen().substring(0, 30) + "..."
    });

    console.log("🏁 Final board FEN at index", clampedIndex + 1, ":", freshGame.fen());
  }, [allMoves, gameAnalysis, resetToStart]);

  // Move quality helpers
  const getMoveColor = (category) => {
    const colors = {
      brilliant: "#1DB954",
      excellent: "#4CAF50",
      good: "#8BC34A",
      inaccuracy: "#FFC107",
      mistake: "#FF9800",
      blunder: "#F44336",
      "major-blunder": "#D32F2F"
    };
    return colors[category] || "#666";
  };

  const getMoveIcon = (category) => {
    const icons = {
      brilliant: "🌟",
      excellent: "✅",
      good: "👍",
      inaccuracy: "⚠️",
      mistake: "❌",
      blunder: "💥",
      "major-blunder": "💀"
    };
    return icons[category] || "⚪";
  };

  // Evaluation bar component
  const EvaluationBar = ({ score = 0 }) => {
    const safeScore = typeof score === 'number' ? score : 0;
    const clampedScore = Math.max(-10, Math.min(10, safeScore));
    const percentage = ((clampedScore + 10) / 20) * 100;

    return (
      <div style={{
        width: "100%",
        height: "20px",
        backgroundColor: "#ddd",
        borderRadius: "10px",
        overflow: "hidden",
        position: "relative",
        margin: "10px 0"
      }}>
        <div style={{
          width: `${percentage}%`,
          height: "100%",
          backgroundColor: percentage > 50 ? "#4CAF50" : "#F44336",
          borderRadius: "10px",
          transition: "width 0.3s ease",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "12px",
          fontWeight: "bold",
          color: percentage > 50 ? "#000" : "#fff"
        }}>
          {safeScore > 0 ? `+${safeScore.toFixed(1)}` : safeScore.toFixed(1)}
        </div>
      </div>
    );
  };

  // Toggle play/pause
  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  // Navigation functions
  const goToStart = () => goToMove(-1);
  const goToPrevious = () => goToMove(currentMoveIndex - 1);
  const goToNext = () => goToMove(currentMoveIndex + 1);
  const goToEnd = () => goToMove(allMoves.length - 1);

  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: "#f5f5f5",
      fontFamily: "system-ui, -apple-system, sans-serif"
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: "#2c3e50",
        color: "white",
        padding: "20px",
        display: "flex",
        alignItems: "center",
        gap: "20px"
      }}>
        <button onClick={onBack} style={{
          background: "transparent",
          border: "1px solid #34495e",
          color: "white",
          padding: "8px 16px",
          borderRadius: "6px",
          cursor: "pointer",
          fontSize: "14px"
        }}>
          ← Back
        </button>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: "600" }}>
          Game Analysis
        </h1>
      </div>

      <div style={{
        display: "flex",
        gap: "30px",
        padding: "30px",
        maxWidth: "1400px",
        margin: "0 auto"
      }}>
        {/* Left Panel - Chess Board */}
        <div style={{
          flex: "0 0 500px",
          backgroundColor: "white",
          borderRadius: "12px",
          padding: "24px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          height: "fit-content"
        }}>
          {/* Chess Board - FIXED: Using correct props and key */}
          <Chessboard
            key={boardFen}                  // forces remount when FEN changes
            position={boardFen}             // correct prop name for react-chessboard
            orientation="white"             // or "black" if you want inverted board
            width={464}
            boardStyle={{
              borderRadius: "12px",
              boxShadow: "0 4px 15px rgba(0,0,0,0.18)",
              border: "2px solid #b0c4de"
            }}
            darkSquareStyle={{ backgroundColor: "#b58863" }}
            lightSquareStyle={{ backgroundColor: "#f0d9b5" }}
            arePiecesDraggable={true}
            animationDuration={300}
          />

          {/* Evaluation Bar */}
          <div style={{ marginTop: "20px" }}>
            <div style={{
              fontSize: "16px",
              fontWeight: "600",
              marginBottom: "8px",
              color: "#2c3e50"
            }}>
              Position Evaluation: {currentEval > 0 ? `+${currentEval.toFixed(1)}` : currentEval.toFixed(1)}
            </div>
            <EvaluationBar score={currentEval} />
          </div>

          {/* Navigation Controls */}
          <div style={{
            marginTop: "24px",
            padding: "20px",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px"
          }}>
            <div style={{
              fontSize: "16px",
              fontWeight: "600",
              marginBottom: "16px",
              textAlign: "center",
              color: "#2c3e50"
            }}>
              Move {currentMoveIndex + 1} of {allMoves.length}
            </div>

            <div style={{
              display: "flex",
              gap: "8px",
              justifyContent: "center",
              flexWrap: "wrap"
            }}>
              <button
                onClick={togglePlay}
                disabled={currentMoveIndex >= allMoves.length - 1}
                style={{
                  background: isPlaying ? "#f44336" : (currentMoveIndex >= allMoves.length - 1 ? "#ccc" : "#4CAF50"),
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  cursor: currentMoveIndex >= allMoves.length - 1 ? "not-allowed" : "pointer",
                  fontSize: "14px",
                  fontWeight: "500"
                }}
              >
                {isPlaying ? "⏸️ Pause" : "▶️ Play"}
              </button>

              <button onClick={goToStart} style={{
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: "6px",
                padding: "10px 15px",
                cursor: "pointer",
                fontSize: "14px"
              }}>
                ⏮️ Start
              </button>

              <button onClick={goToPrevious} style={{
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: "6px",
                padding: "10px 15px",
                cursor: "pointer",
                fontSize: "14px"
              }}>
                ⏪ Previous
              </button>

              <button
                onClick={goToNext}
                disabled={currentMoveIndex >= allMoves.length - 1}
                style={{
                  background: currentMoveIndex >= allMoves.length - 1 ? "#ccc" : "#2196F3",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  padding: "10px 15px",
                  cursor: currentMoveIndex >= allMoves.length - 1 ? "not-allowed" : "pointer",
                  fontSize: "14px"
                }}
              >
                Next ⏩
              </button>

              <button
                onClick={goToEnd}
                disabled={currentMoveIndex >= allMoves.length - 1}
                style={{
                  background: currentMoveIndex >= allMoves.length - 1 ? "#ccc" : "#2196F3",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  padding: "10px 15px",
                  cursor: currentMoveIndex >= allMoves.length - 1 ? "not-allowed" : "pointer",
                  fontSize: "14px"
                }}
              >
                End ⏭️
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Analysis */}
        <div style={{
          flex: "1",
          backgroundColor: "white",
          borderRadius: "12px",
          padding: "24px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          overflowY: "auto",
          maxHeight: "calc(100vh - 120px)"
        }}>
          {/* Analysis Status */}
          {isAnalyzingGame && (
            <div style={{
              padding: "20px",
              textAlign: "center",
              backgroundColor: "#e3f2fd",
              borderRadius: "8px",
              marginBottom: "20px"
            }}>
              <div style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px" }}>
                🔍 Analyzing Game...
              </div>
              <div style={{ color: "#666" }}>
                This may take a moment
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div style={{
              padding: "16px",
              backgroundColor: "#ffebee",
              color: "#c62828",
              borderRadius: "8px",
              marginBottom: "20px",
              border: "1px solid #ffcdd2"
            }}>
              ❌ {error}
            </div>
          )}

          {/* Move Analysis List */}
          {gameAnalysis.length > 0 && (
            <div>
              <h2 style={{
                fontSize: "20px",
                fontWeight: "600",
                marginBottom: "16px",
                color: "#2c3e50"
              }}>
                Move Analysis
              </h2>

              <div style={{ maxHeight: "400px", overflowY: "auto" }}>
                {gameAnalysis.map((analysis, index) => (
                  <div
                    key={index}
                    onClick={() => goToMove(index)}
                    style={{
                      padding: "12px",
                      marginBottom: "8px",
                      borderRadius: "8px",
                      cursor: "pointer",
                      backgroundColor: currentMoveIndex === index ? "#e3f2fd" : "#f8f9fa",
                      border: currentMoveIndex === index ? "2px solid #2196F3" : "1px solid #e0e0e0",
                      transition: "all 0.2s ease"
                    }}
                  >
                    <div style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: "6px"
                    }}>
                      <span style={{ fontWeight: "600", fontSize: "14px" }}>
                        {Math.floor(index / 2) + 1}.{index % 2 === 0 ? '' : '..'} {safeRender(analysis.move)}
                      </span>

                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        {analysis.category && (
                          <span style={{
                            color: getMoveColor(analysis.category),
                            fontSize: "12px",
                            fontWeight: "600"
                          }}>
                            {getMoveIcon(analysis.category)} {analysis.category}
                          </span>
                        )}
                        <span style={{
                          fontSize: "12px",
                          fontWeight: "600",
                          color: "#666"
                        }}>
                          {analysis.actualEval > 0 ? '+' : ''}{analysis.actualEval?.toFixed(1) || '0.0'}
                        </span>
                      </div>
                    </div>

                    {analysis.description && (
                      <div style={{
                        fontSize: "12px",
                        color: "#666",
                        lineHeight: "1.4"
                      }}>
                        {safeRender(analysis.description)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Game Info */}
          {gameData && (
            <div style={{ marginTop: "30px" }}>
              <h2 style={{
                fontSize: "20px",
                fontWeight: "600",
                marginBottom: "16px",
                color: "#2c3e50"
              }}>
                Game Information
              </h2>

              <div style={{
                backgroundColor: "#f8f9fa",
                padding: "16px",
                borderRadius: "8px",
                fontSize: "14px",
                lineHeight: "1.6"
              }}>
                {gameData.white && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>White:</strong> {renderPlayerInfo(gameData.white)}
                  </div>
                )}

                {gameData.black && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>Black:</strong> {renderPlayerInfo(gameData.black)}
                  </div>
                )}

                {gameData.result && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>Result:</strong> {safeRender(gameData.result)}
                  </div>
                )}

                {gameData.time_control && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>Time Control:</strong> {safeRender(gameData.time_control)}
                  </div>
                )}

                {gameData.rated !== undefined && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>Type:</strong> {gameData.rated ? "Rated" : "Casual"}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AnalysisPage;