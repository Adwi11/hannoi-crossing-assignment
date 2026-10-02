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




Where AI was significantly used:

1. Used composer to write the next step function. opus 5.5 medium 

prompt : I need to create the nextStep func basuically moving we will be return the turnresult in it.
any player can have any turn at any time. you can chekc the action by calling on observing that action def observe(self, player):.
if it is nont None or actionn is a skip then we will return self unchnaged else we will replace the turn wil self.turn +1  adn rest same  in the turn result 
do similar for when legal 
2. also fixed bugs in my code in engine 

3. converting class results to dict so need not import class everytime (to dict and from dict)




# Screen capture of creation of engine 
https://drive.google.com/drive/folders/1aBnte7ShTOdmDdVh5eBVVV_dqH3OViVd?usp=sharing