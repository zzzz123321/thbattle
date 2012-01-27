# All Actions, EventHandlers are here
from game.autoenv import Game, EventHandler, Action, GameError

from network import Endpoint
import random
import types

class GenericAction(Action): pass # others

class UserAction(Action): pass # card/character skill actions
class BaseAction(UserAction): pass # attack, graze, heal

class InternalAction(Action): pass # actions for internal use, should not be intercepted by EHs

class Damage(GenericAction):

    def __init__(self, target, amount=1):
        self.target = target
        self.amount = amount

    def apply_action(self):
        self.target.gamedata.life -= self.amount
        return True

class Attack(BaseAction):

    def __init__(self, target, damage=1):
        self.target = target
        self.damage = damage

    def apply_action(self):
        g = Game.getgame()
        target = self.target
        choose_action = ChooseCard(target, lambda cl: len(cl) == 1 and cl[0].type == 'graze')
        if not g.process_action(choose_action):
            return g.process_action(Damage(target, amount=self.damage))
        else:
            drop = DropCardIndex(target, card_indices=choose_action.card_indices)
            g.process_action(drop)
            return False

class Heal(BaseAction):

    def __init__(self, target, amount=1):
        self.target = target
        self.amount = amount

    def apply_action(self):
        self.target.gamedata.life += self.amount
        return True

class DropCardIndex(GenericAction):

    def __init__(self, target, card_indices):
        self.target = target
        self.card_indices = card_indices

    def apply_action(self):
        g = Game.getgame()
        target = self.target

        card_indices = self.card_indices
        ci_sorted = sorted(card_indices, reverse=True)

        cards = [target.gamedata.cards[i] for i in card_indices]
        for i in ci_sorted:
            del target.gamedata.cards[i]

        for p in g.players.exclude(target):
            cards = p.reveal(cards)

        self.cards = cards
        return True

class ChooseCard(GenericAction):

    def __init__(self, target, cond):
        self.target = target
        self.cond = cond

    def apply_action(self):
        g = Game.getgame()
        target = self.target
        input = target.user_input('choose_card', self)

        if not (input and isinstance(input, list)):
            return False # default action

        n = len(input)
        if not n: return False

        if [i.__class__ for i in input] != [int]*n: # must be a list of ints
            return False

        input.sort()
        if input[0] < 0 or input[-1] >= len(target.gamedata.cards): # index out of range
            return False

        cards = [target.gamedata.cards[i] for i in input]
        for p in g.players.exclude(target):
            cards = p.reveal(cards)

        if self.cond(cards):
            self.card_indices = input
            return True
        else:
            return False

    def default_action(self):
        return False

class DropUsedCard(DropCardIndex): pass

class DropCardStage(GenericAction):

    def __init__(self, target):
        self.target = target

    def apply_action(self):
        target = self.target
        life = target.gamedata.life
        n = len(target.gamedata.cards) - life
        if n<=0:
            return True
        g = Game.getgame()
        choose_action = ChooseCard(target, cond = lambda cl: len(cl) == n)
        if g.process_action(choose_action):
            g.process_action(DropCardIndex(target, card_indices=choose_action.card_indices))
        else:
            g.process_action(DropCardIndex(target, card_indices=range(n)))
        return True

class DrawCards(GenericAction):

    def __init__(self, target, amount=2):
        self.target = target
        self.amount = amount

    def apply_action(self):
        from cards import Card, HiddenCard
        g = Game.getgame()
        target = self.target
        if Game.SERVER_SIDE:
            cards = [Card(random.choice(['attack','graze', 'heal'])) for i in xrange(self.amount)]

        if Game.CLIENT_SIDE:
            cards = [HiddenCard] * self.amount

        cards = target.reveal(cards)
        target.gamedata.cards.extend(cards)
        self.cards = cards
        return True

class DrawCardStage(DrawCards): pass

class ActionStage(GenericAction):

    def __init__(self, target):
        self.target = target

    def default_action(self):
       return True

    def apply_action(self):
        g = Game.getgame()
        target = self.target

        while True:
            input = target.user_input('action_stage_usecard')
            if not input: break
            if type(input) != list: break

            card_index, object_index = input

            if type(card_index) != int or type(object_index) != int:
                break

            n = len(target.gamedata.cards)
            if not 0 <= card_index < n:
                break

            if not 0 <= object_index < len(g.players):
                break

            card = target.gamedata.cards[card_index]
            for p in g.players.exclude(target): # This looks WEIRD!
                card = p.reveal(card)

            object = g.players[object_index]
            action = card.assocated_action
            g.process_action(DropUsedCard(target, card_indices=[card_index]))
            if action:
                action = action(target=object)
                action.source = target
                g.process_action(action)

        return True