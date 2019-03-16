var FOLLOWED_IDS = new Set();

Board = function(target_element_id){
    var self = {};
    self._moves = [];
    self._current_move_index = 0;
    self._currentTarget = null;

    self._cell_id = function(x,y){
        return target_element_id+"-"+String(x)+"-"+String(y);
    }

    self._create = function(){
        var el=document.getElementById(target_element_id);
        for(var y=0;y<15;++y){
            var row=document.createElement('div');
            row.className="board_row";
            el.appendChild(row);
            for(var x=0;x<15;++x){
                var cellWrapper=document.createElement('div');
                cellWrapper.className="board_cell_wrapper";

                var cell=document.createElement('div');
                cell.id = self._cell_id(x,y);
                cell.className="board_cell";

                cellWrapper.appendChild(cell);
                row.appendChild(cellWrapper);
            }
        }

        $(el).click(self._navigateToTarget);
    }

    self._navigateToTarget = function(){
        if(self._currentTarget){
            window.location = self._currentTarget;
        }
    }

    self._gotoMove = function(moveIndex){
        if(moveIndex<0)
            moveIndex=0;

        if(moveIndex>=self._moves.length)
            moveIndex=self._moves.length-1;

        var replayDirection=Math.sign(moveIndex-self._current_move_index);

        while(true){
            if(replayDirection>=0){
                self._current_move_index+=replayDirection;
            }

            var move=self._moves[self._current_move_index];
            var x=move[0];
            var y=move[1];
            var cell=document.getElementById(self._cell_id(x,y));

            if(replayDirection>=0){
                cell.className=self._current_move_index % 2 == 0 ? 'board_cell_cross' : 'board_cell_circle';
                self._tryMarkWin(x,y);
            }else{
                $("#"+target_element_id).find(".winning_move").removeClass("winning_move");
                cell.className="";
            }

            if(replayDirection<0){
                self._current_move_index+=replayDirection;
            }

            if(self._current_move_index==moveIndex)
                break;
        }
    }

    self.firstMove = function(){
        self._gotoMove(0);
    }

    self.lastMove = function(){
        self._gotoMove(self._moves.length);
    }

    self.previousMove = function(){
        self._gotoMove(self._current_move_index-1);
    }

    self.nextMove = function(){
        self._gotoMove(self._current_move_index+1);
    }

    self.move = function(x,y){
        self._moves.push([x,y]);
        self.lastMove()
    }

    self.loadMoves = function(moves){
        for(move_id in moves){
            move=moves[move_id];
            self.move(move[0],move[1]);
        }
    }

    self.players = function(p1,p2){
        var p1Label=self._getPlayerLabel("p1");
        var p2Label=self._getPlayerLabel("p2");

        $(p1Label).text(p1);
        $(p2Label).text(p2);
    }

    self.setTarget = function(targetLink){
        self._currentTarget = targetLink;
    }

    self.clear = function(){
        for(var moveId in self._moves){
            var move=self._moves[moveId];
            var x=move[0];
            var y=move[1];
            var cell=document.getElementById(self._cell_id(x,y));
            cell.className="";
        }

        $("#"+target_element_id).find(".winning_move").removeClass("winning_move");
        self._moves=[]
        self._current_move_index=0;
        self.players("","");
    }

    self._tryMarkWin=function(x,y){
        self._tryMarkWinDirection(x,y,1,0);
        self._tryMarkWinDirection(x,y,1,1);
        self._tryMarkWinDirection(x,y,0,1);
        self._tryMarkWinDirection(x,y,-1,1);
    }

    self._tryMarkWinDirection=function(x,y,xdir, ydir){
        var targetColor=self._getColor(x,y);

        // find start of the direction
        while(x-xdir>=0 && y-ydir>=0 && x-xdir<=15 && y-ydir<=15){
            var newx=x-xdir;
            var newy=y-ydir;
            if(self._getColor(newx,newy)!=targetColor)
                break;

            x=newx;
            y=newy;
        }

        var fields=[];
        while(x>=0 && y>=0 && x<=15 && y<=15){
            fields.push([x,y]);
            var x=x+xdir;
            var y=y+ydir;
            if(self._getColor(x,y)!=targetColor)
                break;
        }

        if(fields.length<5)
            return;

        for(var fieldId in fields){
            var field=fields[fieldId];
            var cell=document.getElementById(self._cell_id(field[0],field[1]));
            $(cell).parent().addClass('winning_move');
        }
    }

    self._getColor = function(x,y){
        var cell=document.getElementById(self._cell_id(x,y));

        if(cell==null || cell.className==null)
            return 0;

        if(cell.className.includes("cross"))
            return 1;

        if(cell.className.includes("circle"))
            return -1;

        return 0;
    }

    self._getPlayerLabel = function(tag){
        var labelId=target_element_id +"-"+tag;
        var pEl=document.getElementById(labelId);
        if(!pEl){
            pEl=document.createElement('div');
            pEl.id=labelId;
            pEl.className=tag;
            document.getElementById(target_element_id).appendChild(pEl);
        }
        return pEl;
    }


    self._create();
    return self;
}