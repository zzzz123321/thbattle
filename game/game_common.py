class GameError(Exception):
    pass

class EventHandler(object):

    def handle(self, evt_type, act):
        raise GameError('Override handle function to implement EventHandler logics!')

    def interested(self, evt_type, act):
        raise GameError('Override this!')

class Action(object):
    def __init__(self):
        pass

    def can_fire(self):
        '''
        Return true if the action can be fired.
        '''
        return Game.get_current().emit_event('action_can_fire', self)
    
    def apply_action_server(self):
        raise GameError('Override apply_action to implement Action logics!')
    
    def apply_action_client(self):
        raise GameError('Override apply_action to implement Action logics!')

    def set_up(self):
        '''
        Execute before 'action_before' event
        '''
        pass
    
    def clean_up(self):
        '''
        Execute after all event handlers finished there work.
        '''
        pass
    
    def cancel(self, cancel=True):
        self.cancelled = cancel

class DataHolder(object):
    def __data__(self):
        return self.__dict__

class Player(object):

    def __data__(self):
        d = User.__data__(self)
        d.update(
            dummy='dummy',
        )
        return d

class Game(object):
    '''
    The Game class, all game mode derives from this.
    Provides fundamental behaviors.

    Instance variables:
        players: list(Players)
        event_handlers: list(EventHandler)

        and all game related vars, eg. tags used by [EventHandler]s and [Action]s
    '''
    CLIENT_SIDE = 0
    SERVER_SIDE = 1

    def __init__(self, side):
        self.side = ['client', 'server'].index(side)

    def game_start(self):
        '''
        Game logic goes here.
        GameModes should override this.
        '''
        raise GameError('Override this function to implement Game logics!')
    
    def emit_event(self, evt_type, data):
        '''
        Fire an event, all relevant event handlers will see this,
        data can be modified.
        '''
        for evt in self.event_handlers:
            if evt.interested(evt_type, data):
                data = evt.handle(evt_type, data)
        return data

    def process_action(self, action):
        '''
        Process an action
        '''
        if action.can_fire():
            action.set_up()
            action = self.emit_event('action_before', action)
            if action.can_fire() and not action.cancelled:
                rst = [action.apply_action_client, action.apply_action_server][self.side]()
                assert rst in [True, False], 'Action.apply_action_* must return boolean!'
            else:
                return False
            action = self.emit_event('action_after', action)
            action.clean_up()
            return rst
        else:
            return False
