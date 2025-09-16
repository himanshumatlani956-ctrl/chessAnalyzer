// server.js - COMPLETELY CORRECTED VERSION (UCI moves + proper perspective)
import express from "express";
import cors from "cors";
import fetch from "node-fetch";
import { spawn } from "child_process";
import { Chess } from "chess.js";

const app = express();
app.use(cors());
app.use(express.json());

const PORT = 5000;
const STOCKFISH_PATH = "C:\\Users\\asus\\Downloads\\stockfish-windows-x86-64-avx2\\stockfish\\stockfish-windows-x86-64-avx2.exe";

app.get("/", (req, res) => {
  res.send("✅ Chess Analysis API is running. Use /games/:username to fetch games or POST /analyze-game to analyze entire games.");
});

app.get("/games/:username", async (req, res) => {
  const username = req.params.username.toLowerCase();
  try {
    const archiveRes = await fetch(`https://api.chess.com/pub/player/${username}/games/archives`);
    const archiveData = await archiveRes.json();

    if (!archiveData.archives || archiveData.archives.length === 0) {
      return res.status(404).json({ error: "No game archives found" });
    }

    const allGames = [];
    for (let i = archiveData.archives.length - 1; i >= 0; i--) {
      const monthRes = await fetch(archiveData.archives[i]);
      const monthData = await monthRes.json();
      
      if (monthData.games && monthData.games.length > 0) {
        const reversedGames = monthData.games.reverse();
        allGames.push(...reversedGames);
        if (allGames.length >= 10) break;
      }
    }
    res.json({ games: allGames.slice(0, 10) });
  } catch (error) {
    console.error("Error fetching games:", error.message);
    res.status(500).json({ error: "Failed to fetch games" });
  }
});

// Extract moves from PGN
function extractActualMoves(pgn) {
  console.log("🎯 Extracting actual moves from PGN...");
  
  let cleanPgn = pgn
    .replace(/\[([^\]]+)\]/g, '') // Remove headers
    .replace(/\{[^}]*\}/g, '') // Remove comments in braces
    .replace(/\([^)]*\)/g, '') // Remove comments in parentheses
    .replace(/\$\d+/g, '') // Remove numeric annotations
    .replace(/[!?+#]/g, '') // Remove move annotations
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
  
  const movePattern = /(\d+\.+|\d+\.\.\.|[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8](?:=[NBRQ])?[+#]?|O-O-O|O-O)/g;
  const allTokens = cleanPgn.match(movePattern) || [];
  
  const actualMoves = allTokens.filter(token => {
    if (/^\d+\.+$/.test(token)) return false;
    if (/^\d+\.\.\.$/.test(token)) return false;
    return true;
  });
  
  console.log("🎯 Filtered actual moves:", actualMoves.slice(0, 20));
  return actualMoves;
}

// FIXED: Convert SAN move to UCI format for Stockfish
function convertToUCI(moveObject) {
  // moveObject has: { from: "e2", to: "e4", promotion: "q" (optional) }
  let uci = moveObject.from + moveObject.to;
  if (moveObject.promotion) {
    uci += moveObject.promotion.toLowerCase();
  }
  return uci;
}

// FIXED: Normalize evaluation to White's perspective (single normalization)
function normalizeToWhite(evalCp, sideToMove) {

  return sideToMove === 'w' ? evalCp : -evalCp;
}

// Get evaluation from Stockfish using UCI moves
function getStockfishEvaluation(uciMoves) {
  return new Promise((resolve, reject) => {
    console.log(`   📤 Sending to Stockfish: position startpos moves ${uciMoves.join(" ")}`);
    
    const stockfish = spawn(STOCKFISH_PATH);
    let output = "";
    let analysisComplete = false;

    const timeout = setTimeout(() => {
      if (!analysisComplete) {
        stockfish.kill();
        reject(new Error("Stockfish timeout"));
      }
    }, 8000);

    stockfish.stdin.write("uci\n");
    stockfish.stdin.write("isready\n");
    stockfish.stdin.write(`position startpos moves ${uciMoves.join(" ")}\n`);
    stockfish.stdin.write("go depth 15\n");

    stockfish.stdout.on("data", (data) => {
      output += data.toString();
      
      if (output.includes("bestmove")) {
        analysisComplete = true;
        clearTimeout(timeout);
        
        const lines = output.split("\n");
        let rawScore = 0;
        let foundScore = false;
        
        // Look for the final depth 15 evaluation
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i];
          if (line.includes("info depth 15") && line.includes("score cp")) {
            const match = line.match(/score cp (-?\d+)/);
            if (match) {
              rawScore = parseInt(match[1]);
              foundScore = true;
              console.log(`   📥 Stockfish eval: ${rawScore} cp (depth 15)`);
              break;
            }
          } else if (line.includes("info depth 15") && line.includes("score mate")) {
            const match = line.match(/score mate (-?\d+)/);
            if (match) {
              const mateIn = parseInt(match[1]);
              rawScore = mateIn > 0 ? 5000 : -5000;
              foundScore = true;
              console.log(`   📥 Stockfish eval: mate in ${mateIn}`);
              break;
            }
          }
        }

        if (!foundScore) {
          console.log(`   ⚠️ No score found in Stockfish output`);
        }

        // Determine who's to move to normalize perspective
        const tempGame = new Chess();
        for (const uciMove of uciMoves) {
          // Convert UCI back to move object for chess.js
          const from = uciMove.substring(0, 2);
          const to = uciMove.substring(2, 4);
          const promotion = uciMove.length > 4 ? uciMove.substring(4) : undefined;
          tempGame.move({ from, to, promotion });
        }
        const sideToMove = tempGame.turn();
        
        // Normalize to White's perspective
        const normalizedScore = normalizeToWhite(rawScore, sideToMove);
        console.log(`   🔄 Normalized to White perspective: ${normalizedScore} cp (was ${rawScore} from ${sideToMove}'s perspective)`);

        stockfish.kill();
        resolve({
          rawScore,
          normalizedScore,
          sideToMove
        });
      }
    });

    stockfish.on("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
  });
}

// Calculate centipawn loss with proper methodology
function calculateCentipawnLoss(bestResult, actualResult, moveNumber) {
  console.log(`   🎯 CPL Calculation for move ${moveNumber}:`);
  console.log(`      Best move: ${bestResult.rawScore} cp (${bestResult.sideToMove}) → ${bestResult.normalizedScore} cp (White perspective)`);
  console.log(`      Actual move: ${actualResult.rawScore} cp (${actualResult.sideToMove}) → ${actualResult.normalizedScore} cp (White perspective)`);
  
  // Both evaluations normalized to White's perspective - direct comparison
  const cpl = Math.abs(bestResult.normalizedScore - actualResult.normalizedScore);
  console.log(`      CPL = |${bestResult.normalizedScore} - ${actualResult.normalizedScore}| = ${cpl} cp`);
  
  return cpl;
}

// Classify move quality
function classifyMoveQuality(cpl) {
  let evaluation, category, description;

  if (cpl <= 10) {
    evaluation = "Best";
    category = "excellent";
    description = "Excellent! Very close to the engine's top choice.";
  } else if (cpl <= 30) {
    evaluation = "Good";
    category = "good";
    description = "A solid move that maintains the position well.";
  } else if (cpl <= 100) {
    evaluation = "Inaccuracy";
    category = "inaccuracy";
    description = "A slight inaccuracy that worsens the position.";
  } else if (cpl <= 200) {
    evaluation = "Mistake";
    category = "mistake";
    description = "A mistake that clearly deteriorates the position.";
  } else {
    evaluation = "Blunder";
    category = "blunder";
    description = "A blunder that seriously damages the position!";
  }

  return { evaluation, category, description, cpl };
}

// MAIN ANALYSIS ROUTE - COMPLETELY FIXED
app.post("/analyze-game", async (req, res) => {
  const { pgn } = req.body;
  
  if (!pgn || typeof pgn !== 'string' || pgn.trim().length === 0) {
    return res.status(400).json({ error: "No valid PGN provided" });
  }

  console.log("📋 Starting CORRECTED analysis (UCI + proper normalization)...");

  try {
    // Extract moves from PGN
    const actualMoves = extractActualMoves(pgn);
    
    if (actualMoves.length === 0) {
      return res.status(400).json({ error: "No chess moves found in PGN" });
    }

    // Validate moves and convert to UCI format
    const game = new Chess();
    const validMoves = [];
    const uciMoves = [];
    
    for (let i = 0; i < actualMoves.length; i++) {
      const move = actualMoves[i].trim();
      if (!move) continue;
      
      try {
        const result = game.move(move, { sloppy: true });
        if (result) {
          validMoves.push(result);
          // FIXED: Convert to UCI format for Stockfish
          const uci = convertToUCI(result);
          uciMoves.push(uci);
          console.log(`✅ Move ${i + 1}: ${result.san} → ${uci}`);
        } else {
          break;
        }
      } catch (moveError) {
        break;
      }
    }

    if (validMoves.length === 0) {
      return res.status(400).json({ error: "Could not validate any moves from PGN" });
    }

    console.log(`✅ Successfully validated ${validMoves.length} moves`);

    // CORRECTED ANALYSIS: Same position, different moves, UCI notation
    const analysisResults = [];
    const maxMoves = validMoves.length; // Analyze first 20 moves
    console.log(`🔍 Analyzing ${maxMoves} moves with CORRECTED methodology...`);


    const uciHistory = [];
    
    for (let i = 0; i < maxMoves; i++) {
      const moveToAnalyze = validMoves[i];
      const uciMoveToAnalyze = uciMoves[i];
      const currentPlayer = i % 2 === 0 ? 'White' : 'Black';
      
      console.log(`\n📊 ===== MOVE ${i + 1}: ${currentPlayer} plays ${moveToAnalyze.san} (${uciMoveToAnalyze}) =====`);
      console.log(`🎯 Current position UCI: [${uciHistory.join(" ")}]`);
      
      try {
        // STEP 1: Get BEST move evaluation from current position
        console.log(`🔍 Step 1: Getting best move evaluation from current position...`);
        const bestResult = await getStockfishEvaluation(uciHistory);
        
        // STEP 2: Get evaluation after ACTUAL move
        const positionAfterMove = [...uciHistory, uciMoveToAnalyze];
        console.log(`🔍 Step 2: Getting evaluation after actual move...`);
        const actualResult = await getStockfishEvaluation(positionAfterMove);
        
        // STEP 3: Calculate centipawn loss (both already normalized to White's perspective)
        const cpl = calculateCentipawnLoss(bestResult, actualResult, i + 1);
        
        // STEP 4: Classify move quality
        const moveQuality = classifyMoveQuality(cpl);
        console.log(`   ✅ FINAL RESULT: ${moveQuality.evaluation} (${cpl} cp loss)`);
        
        analysisResults.push({
          moveNumber: i + 1,
          move: moveToAnalyze.san,
          uciMove: uciMoveToAnalyze,
          from: moveToAnalyze.from,
          to: moveToAnalyze.to,
          bestEval: bestResult.normalizedScore,
          actualEval: actualResult.normalizedScore,
          score: bestResult.normalizedScore / 100,
          centipawnLoss: cpl,
          evaluation: moveQuality.evaluation,
          category: moveQuality.category,
          description: moveQuality.description,
          color: currentPlayer.toLowerCase()
        });
        
        // FIXED: Add UCI move to history for next iteration
        uciHistory.push(uciMoveToAnalyze);
        
      } catch (analysisError) {
        console.log(`⚠️ Analysis failed for move ${i + 1}: ${analysisError.message}`);
        
        analysisResults.push({
          moveNumber: i + 1,
          move: moveToAnalyze.san,
          uciMove: uciMoveToAnalyze,
          from: moveToAnalyze.from,
          to: moveToAnalyze.to,
          bestEval: 0,
          actualEval: 0,
          score: 0,
          centipawnLoss: 0,
          evaluation: "Analysis Failed",
          category: "error",
          description: "Could not analyze this position",
          color: currentPlayer.toLowerCase()
        });
        
        // Still add UCI move to history to keep sequence valid
        uciHistory.push(uciMoveToAnalyze);
      }
    }

    console.log("\n✅ ===== CORRECTED ANALYSIS COMPLETED =====");
    
    // Calculate statistics
    const validResults = analysisResults.filter(r => r.category !== 'error');
    const stats = {
      best: validResults.filter(r => r.category === 'excellent').length,
      good: validResults.filter(r => r.category === 'good').length,
      inaccuracy: validResults.filter(r => r.category === 'inaccuracy').length,
      mistake: validResults.filter(r => r.category === 'mistake').length,
      blunder: validResults.filter(r => r.category === 'blunder').length,
      errors: analysisResults.filter(r => r.category === 'error').length
    };
    
    const avgCPL = validResults.length > 0 
      ? validResults.reduce((sum, r) => sum + r.centipawnLoss, 0) / validResults.length
      : 0;
    
    console.log("📊 FINAL STATISTICS:", stats);
    console.log(`📊 Average CPL: ${avgCPL.toFixed(1)} cp`);
    console.log(`📊 Distribution: ${stats.best} best, ${stats.good} good, ${stats.inaccuracy} inaccuracies, ${stats.mistake} mistakes, ${stats.blunder} blunders`);
    
    res.json({ 
      success: true, 
      totalMoves: validMoves.length,
      analyzedMoves: analysisResults.length,
      analysis: analysisResults,
      statistics: stats,
      averageCPL: Math.round(avgCPL * 10) / 10,
      moves: validMoves.map((m, idx) => ({
        san: m.san,
        uci: uciMoves[idx],
        from: m.from,
        to: m.to
      })),
      fixes: {
        uciNotation: "Now sending UCI moves (e2e4) instead of SAN (e4) to Stockfish",
        singleNormalization: "Normalizing evaluations once to White's perspective",
        samePositionComparison: "Comparing best vs actual move from identical position",
        properCPL: "CPL = |normalize(best_eval) - normalize(actual_eval)|"
      }
    });

  } catch (error) {
    console.error("❌ Analysis error:", error.message);
    res.status(500).json({ 
      error: "Failed to analyze game: " + error.message
    });
  }
});

app.listen(PORT, () => console.log(`✅ Server running at http://localhost:${PORT} - CORRECTED VERSION`));