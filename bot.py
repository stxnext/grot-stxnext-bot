import http.client
import json
import random
import sys
import time
import threading


class Field(object):
    """
    Holds field state.
    """

    def __init__(self, x, y, data):
        self.x = x
        self.y = y
        self.points = data['points']
        self.direction = data['direction']


class Board(object):

    def __init__(self, data):
        self.size = len(data)

        self.fields = [
            [Field(x, y, data[y][x]) for x in range(self.size)]
            for y in range(self.size)
        ]

    def get_field(self, x, y):
        """
        Returns the field at the given coordinates.
        """
        return self.fields[y][x]

    def get_next_field(self, field, direction=None):
        """
        Returns next field in chain reaction and information is it last step
        in this chain reaction.
        """
        direction = field.direction or direction

        if direction == 'left':
            if field.x == 0:
                return None
            next_field = self.get_field(field.x - 1, field.y)

        elif direction == 'right':
            if field.x == (self.size - 1):
                return None
            next_field = self.get_field(field.x + 1, field.y)

        elif direction == 'up':
            if field.y == 0:
                return None
            next_field = self.get_field(field.x, field.y - 1)

        elif direction == 'down':
            if field.y == (self.size - 1):
                return None
            next_field = self.get_field(field.x, field.y + 1)

        if next_field.direction is None:
            # if next was alread cleared than go further in the same direction
            return self.get_next_field(next_field, direction)

        return next_field

    def lower_field(self, field):
        """
        When chain reaction is over fields that are 'flying' should be lowered.
        """
        new_y = field.y
        while new_y < self.size - 1:
            if self.get_field(field.x, new_y + 1).direction is not None:
                # next field below is not empty, so finish lowering
                break
            new_y += 1

        if new_y != field.y:
            next_field = self.get_field(field.x, new_y)
            # swap fields values
            field.points, next_field.points = next_field.points, field.points
            field.direction, next_field.direction = next_field.direction, field.direction

    def lower_fields(self):
        """
        Lower fields (use gravity).
        """
        for y in reversed(range(self.size - 1)):
            for x in range(self.size):
                self.lower_field(self.get_field(x, y))

    def fill_empty_fields(self):
        """
        Reset fields in empty places.
        """
        for x in range(self.size):
            for y in range(self.size):
                field = self.get_field(x, y)
                if field.direction is None:
                    field.reset()

    def get_extra_points(self):
        """
        Return extra points for the empty rows and columns.
        """
        extra_points = 0

        for x in range(self.size):
            is_empty = True
            for y in range(self.size):
                if self.get_field(x, y).direction is not None:
                    is_empty = False
                    break

            if is_empty:
                extra_points += self.size * 10

        for y in range(self.size):
            is_empty = True
            for x in range(self.size):
                if self.get_field(x, y).direction is not None:
                    is_empty = False
                    break

            if is_empty:
                extra_points += self.size * 10


        return extra_points


class Game(object):

    def __init__(self, data, score):
        self.board = Board(data)
        self.score = score

    def start_move(self, x, y):
        """
        Set initial values and start chain reaction.
        """
        field = self.board.get_field(x, y)

        self.move_score = 0
        self.move_length = 0
        self.move_bonus = 0

        self.move_next_field(field)

    def move_next_field(self, start_field):
        """
        One step in chain reaction.
        """
        next_field = self.board.get_next_field(start_field)
        start_field.direction = None
        self.move_score += start_field.points
        self.move_length += 1

        if next_field is None:
            self.finish_move()
        else:
            self.move_next_field(next_field)

    def finish_move(self):
        """
        Finish the move.
        """
        self.move_score += self.board.get_extra_points()
        self.score += self.move_score

        threshold = (self.score // (5*self.board.size**2)) + self.board.size - 1
        if self.move_length > threshold:
            self.move_bonus = self.move_length - threshold


class App(object):
    def __init__(self, token):
        self.token = token

    def get_result(self, data):
        board = data['board']
        score = data['score']
        size = len(board)

        best_x = 0
        best_y = 0
        best_value = 0
        best = None

        for x in range(size):
            for y in range(size):
                game = Game(board, score)
                game.start_move(x, y)
                move_value = game.move_score + game.move_bonus*10 - game.move_length

                if move_value > best_value:
                    best_x = x
                    best_y = y
                    best_value = move_value
                    best = game

        return {'x': best_x, 'y': best_y}

    def start(self):
        client = http.client.HTTPConnection('localhost', 8080)
        client.connect()

        client.request('GET', '/games/2/board?token={}'.format(self.token))
        response = client.getresponse()

        while response.status == 200:
            data = json.loads(response.read().decode())
            result = self.get_result(data)

            client.request(
                'POST', '/games/2/board?token={}'.format(self.token),
                json.dumps(result),
            )

            response = client.getresponse()


if __name__ == '__main__':
    token = sys.argv[1]
    app = App(token)
    app.start()

