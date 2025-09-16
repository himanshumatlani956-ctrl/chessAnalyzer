const {Engine } =  require('nocde-uci') ; 
const enginePath = "C:\\Users\\asus\\Downloads\\stockfish-windows-x86-64-avx2\\stockfish\\stockfish-windows-x86-64-avx2.exe";
async function analyzeGame(moves){
    const engine = new Engine(enginePath) ;
    await engine.init() ;
    await engine.isReady() ;
    await engine.ucinewgame() ; 
    let results = [] ;
    for(let  i = 0  ; i < moves.length ; i ++){
        let position =  moves.slice(0,i+1).join(" ") ; 
        await engine.position("startpos" , positionMoves.split(" ")) ; 
        const analysis = await engine.go({depth : 15}) ; 
        results.push({
            moves:moves[i] ,
            evaluation:analysis.info[analysis.info.length -1].score,
            bestmove:analysis.bestmove ,  

        }) ; 
    }
    await engine.quit() ;
    return results ;
}
module.exports = {analyzeGame} ;
