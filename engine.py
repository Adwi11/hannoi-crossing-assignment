from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum
from typing import Any


class Player(str, Enum):
    
    A = "A"
    B = "B"

    def index(self,):
        return 0 if self is Player.A else 1 
    
class Pole(int, Enum):
    
    A1=0
    B1=1
    SHARED=2
    A3=3
    B3=4

#so that each player cannot cheat
VISIBLE_POLES ={
Player.A : (Pole.A1,Pole.SHARED, Pole.A3),
Player.B : (Pole.B1,Pole.SHARED, Pole.B3)
}

Stack = tuple[int, ...]

class ActionType(str, Enum):
    SKIP = "skip"
    LIFT = "lift"
    PLACE = "place"

@dataclass
class Action:
    type: ActionType
    pole: int | None = None

    def __post_init__(self):
        self.type = ActionType(self.type)

        if self.type == ActionType.SKIP and self.pole is not None:
            raise ValueError("Skip action cannot have a pole")

        if self.type == ActionType.PLACE and self.pole is None:
            raise ValueError("Place action must have a pole")

        if self.type == ActionType.LIFT and self.pole is None:
            raise ValueError("Lift action must have a pole")

        if self.pole is not None and not (1 <= self.pole <= 3):
            raise ValueError("Pole must be between 1 and 3")
    
    # for convinience we return class objs 
    @classmethod
    def skip(cls):
        return cls(ActionType.SKIP, None)
    
    @classmethod
    def place(cls, pole: int):
        return cls(ActionType.PLACE, pole)
    
    @classmethod
    def lift(cls, pole: int):
        return cls(ActionType.LIFT, pole)
    
    @property
    def index(self,):
        return ACTIONS.index(self)
    
        
            
#XXX: check 
ACTIONS : tuple[Action, ...] = (Action.skip(), Action.place(1), Action.place(2), Action.place(3), Action.lift(1), Action.lift(2), Action.lift(3))


class IllegalReason(str, Enum):
    HAND_FULL = "hand_full"
    HAND_EMPTY = "hand_empty"
    POLE_FULL = "pole_full"
    POLE_EMPTY = "pole_empty"
    POLE_ILLEGAL = "pole_illegal"
    SMALLER_DISK_ON_LARGER_DISK = "smaller_disk_on_larger_disk"

# to view the curr_state for the player 
@dataclass
class Observation:

    player: Player
    n: int
    turn: int
    poles: tuple[Stack, Stack, Stack]
    hand: int | None
    winner: Player | None
    over: bool = field(init=False) #derived from winner
    # loser: Player


    def __post_init__(self):
        object.__setattr__(self, "over",self.winner is not None)

    def check_state(self, action: Action) -> IllegalReason | None:
        if action.type == ActionType.SKIP:
            return None

        stack = self.poles[action.pole - 1]

        if action.type == ActionType.LIFT:
            if self.hand is not None:
                return IllegalReason.HAND_FULL
            if not stack:
                return IllegalReason.POLE_EMPTY
            return None

        if self.hand is None:
            return IllegalReason.HAND_EMPTY
        # place 
        if stack and stack[-1] < self.hand:
            return IllegalReason.SMALLER_DISK_ON_LARGER_DISK
        return None
    
@dataclass
class CurrentState:
    n: int
    turn: int
    poles: tuple[Stack, Stack, Stack, Stack, Stack]
    hands: tuple[int | None, int | None]
    winner: Player | None
    over: bool = field(init=False) #derived from winner

    def __post_init__(self):
        p1A,p2A,p3A = self._local_poles(Player.A)
        p1B,p2B,p3B = self._local_poles(Player.B)
        if self.hand(Player.A) is None and not p1A and not p2A and bool(p3A):
            winner = Player.A
        elif self.hand(Player.B) is None and not p1B and not p2B and bool(p3B):
            winner = Player.B
        else:
            winner = None
        object.__setattr__(self, "winner",winner)
        object.__setattr__(self, "over",winner is not None)

    @classmethod
    def new(cls, n):
        if not isinstance(n, int) or n < 1:
            raise ValueError("n must be a positive integer")
        
        first_player_disk, second_player_disk = tuple(range(2*n-1,0,-2)), tuple(range(2*n,0,-2))
        poles = [()] * len(Pole)
        poles[Pole.A1] = first_player_disk
        poles[Pole.B1] = second_player_disk

        # start state is both hands are empty
        return cls(n=n, turn=0, poles = tuple(poles), hands = (None, None), winner=None)
    
    def hand(self, player):
        return self.hands[player.index()]
    
    def observe(self, player):
        return Observation(player, self.n, self.turn, self._local_poles(player), self.hand(player), self.winner)

    def _local_poles(self, player: Player) -> Stack:
        return tuple(self.poles[p] for p in VISIBLE_POLES[player])
    
    def nextStep(self, player, action):
        reason = self.observe(player).check_state(action)
        if reason is not None or action.type == ActionType.SKIP:
            return TurnResult(state=self, action=action, reason=reason)

        pole = VISIBLE_POLES[player][action.pole - 1].value
        poles = list(self.poles)
        hands = list(self.hands)

        if action.type == ActionType.LIFT:
            hands[player.index()] = poles[pole][-1]
            poles[pole] = poles[pole][:-1]
        else:
            poles[pole] = poles[pole] + (hands[player.index()],)
            hands[player.index()] = None

        return TurnResult(
            state=CurrentState(self.n, self.turn + 1, tuple(poles), tuple(hands), None),
            action=action,
            reason=None,
        )

@dataclass
class TurnResult:

    state: CurrentState
    action: Action
    reason: IllegalReason | None

    def legal(self) -> bool:
        return self.reason is None

    
