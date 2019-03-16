var LiveManager = function(boardIds, websocketPort){
    var self = {};
    var boards = [];
    var idToBoard = {};

    for(var id in boardIds){
        var boardId = boardIds[id];
        var board = Board(boardId);
        board.finishTime = 0;
        boards.push(board);
    }


    self.start = function(){
        idToBoard = {};

        var wsPath = "ws://" + document.location.hostname + ":" + websocketPort + "/ws";
        var ws = new WebSocket(wsPath);

        ws.onmessage = function(evt) {self._dataArrived($.parseJSON(evt.data))};
        ws.onclose = function(evt) { setTimeout(self.start, 1000); };
        ws.onopen = function(evt) { };
    }

    self._dataArrived = function(data){
        if("board" in data){
            var board = self._tryFindFreeBoard();
            if(board == null)
                return;

            var boardData = data["board"];
            board.clear();
            board.players(boardData["player1"], boardData["player2"]);
            board.setTarget("/board/" + boardData["_id"]);
            idToBoard[boardData["_id"]] = board;

            // in case board came with some moves already, play them
            var moves = boardData["moves"];
            for(var moveId in moves){
                var move = moves[moveId];
                board.move(move[0], move[1]);
            }
        }else if("finished_board" in data){
            var id = data["finished_board"]["_id"];
            if(id in idToBoard){
                idToBoard[id].finishTime = new Date().getTime();
                delete idToBoard[id];
            }
        }else if("move" in data){
            var id = data["_id"];
            var move = data["move"];
            if(id in idToBoard){
                idToBoard[id].move(move[0],move[1]);
            }
        }else{
            console.warning(data);
        }
    }

    self._tryFindFreeBoard = function(){
        var freeBoards = [];

        for(var boardId in boards){
            var board = boards[boardId];
            if(self._isBoardAvailable(board)){
                freeBoards.push(board);
            }
        }

        if(freeBoards.length == 0)
            return null;

        freeBoards.sort(function(a, b){return b.finishTime - a.finishTime})

        return freeBoards[0];
    }

    self._isBoardAvailable = function(board) {
        if(new Date().getTime() - board.finishTime < 5000)
            // keep the finished game displayed for some time
            return false;

        for(var id in idToBoard){
            if(board == idToBoard[id])
                return false;
        }

        return true;
    }

    return self;
}