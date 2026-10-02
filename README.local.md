1. we will need a state and action. 
2. post action we need to see the state again.

Design decisions:
1. Will be storing stack in a pole in () tuple
2. {A1:(),B1:(),2:(),A3:(),B3:()} state storage
3. Will have Observation + CurrentState -> might merge into one but we must not since gamestate can show the other player's hand so someone can invoke it and cheat.
4. Current state would return CurrentState(
    n=1,
    turn=0,
    poles=(..., ..., ..., ..., ...),  # full internal 5-pole layout
    hands=(None, None),
    winner=None,
)

# Used composer to write the next step function. opus 5.5 medium 
# also fixed bugs in my code in engine 
