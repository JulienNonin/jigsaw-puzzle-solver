import numpy as np
import matplotlib.pyplot as plt
from enum import Enum
from copy import copy, deepcopy
from skimage import  color

'''
Here we define the way we see a Puzzle. Many classes are defined in this file and are useful for any solvers.
We invite you to explore the classes so that you can get a better understanding of our code.

'''

def findtwoFactors(n):
    "Compute two factors of an integer n enabling to cut a dimension into two"

    for i in range(int(np.sqrt(n))+1,1,-1):
        if n%i==0:
            return [i,n//i]

    return False


def initialize(puzzle,img_cropped,ps,shuffled=True):
    '''handle the initialization of a puzzle with the image correctly cropped
       when shuffled=False, we construct the ground_truth, else the pieces are shuffled
       in the bag of pieces'''



    ## Populate the bag of pieces or the board
    n_rows,n_columns=puzzle.shape
    for i in range(n_rows):
        for j in range(n_columns):
            piece = Piece(img_cropped[i * ps:(i + 1) * ps, j * ps:(j + 1) * ps], i * n_columns + j)
            if shuffled:
                puzzle.bag_of_pieces.append(piece)
            else:
                puzzle.board[i, j] = piece

    puzzle.patch_size = ps
    if shuffled: puzzle.shuffle()

def patch(ps):
    "Return a function which enables to initialize a Puzzle given a patch_size"

    def create_puzzle(puzzle,shuffled=True):
        height, width, _ = puzzle.img.shape
        n_rows, n_columns = height // ps, width // ps
        puzzle.board = Board(n_rows, n_columns)
        img_cropped = puzzle.img[:n_rows * ps, :n_columns * ps]

        initialize(puzzle, img_cropped, ps, shuffled)


    return create_puzzle


def nb_pieces(np):
    "Return a function which enables to initialize a Puzzle given a number of pieces"
    assert np != 2, "Come on, this isn't really a puzzle"
    assert np <= 500, "This is too complex"

    def create_puzzle(puzzle,shuffled=True):
        height, width, _ = puzzle.img.shape
        # We check if the number of pieces given is a prime number
        nb_final_pieces = np if findtwoFactors(np) else np + 1
        n_rows, n_columns = findtwoFactors(nb_final_pieces)
        puzzle.board = Board(n_rows, n_columns)
        ps = min(height // n_rows, width // n_columns)
        img_cropped = puzzle.img[:n_rows * ps, :n_columns * ps]

        if np != nb_final_pieces:
            print(f"I can't perfectly cut your puzzle into {nb_pieces} squared pieces. Instead, I cutted it into {nb_final_pieces} pieces")

        initialize(puzzle, img_cropped, ps, shuffled)

    return create_puzzle


def nb_rows_and_columns(rows_and_columns):
    "Return a function which enables to initialize a Puzzle given a number of rows and a number of columns"
    assert rows_and_columns[0] >= 3 and rows_and_columns[1] >= 3, "Come on, this isn't really a puzzle"
    assert rows_and_columns[0] <= 100 and rows_and_columns[1] <= 100, "This is too complex"

    def create_puzzle(puzzle,shuffled=True):
        height, width, _ = puzzle.img.shape
        n_rows, n_columns = rows_and_columns
        puzzle.board = Board(n_rows, n_columns)
        ps = min(height // n_rows, width // n_columns)
        img_cropped = puzzle.img[:n_rows * ps, :n_columns * ps]

        initialize(puzzle, img_cropped, ps, shuffled)

    return create_puzzle


class Border(Enum):
    def __new__(cls, value, slice):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.slice = slice
        return obj
    TOP = (0, np.index_exp[0,:])
    RIGHT = (1, np.index_exp[:,-1])
    BOTTOM = (2, np.index_exp[-1,:])
    LEFT = (3, np.index_exp[:,0])

    @property
    def opposite(self):
        opposite_value = (self.value + 2) % 4
        if 0 <= opposite_value <= 3:
            return Border(opposite_value)
        raise NotImplementedError     


class Board():
    def __init__(self, n_rows, n_cols):
        self._grid = np.array([[Slot(i * n_cols + j) for j in range(n_cols)] for i in range(n_rows)])

    def __getitem__(self, coords):
        i, j = coords
        return self._grid[i,j]

    def __setitem__(self, coords, value):
        assert isinstance(value, Slot) or isinstance(value, Piece), (
            f"value is an instance of {type(value)} instead of Slot or Piece")
        i, j = coords
        self._grid[i,j] = value

    def __iter__(self):
        for i in range(self.shape[0]):
            for j in range(self.shape[1]):
                yield self._grid[i,j]

    def enumerate(self):
        for i in range(self.shape[0]):
            for j in range(self.shape[1]):
                yield (i, j), self._grid[i,j]

    @property
    def shape(self):
        return self._grid.shape

    def neighbors(self, i, j):
        if i > 0:
            yield Border.TOP.value, self[i-1, j]
        if j < self.shape[1]-1:
            yield Border.RIGHT.value, self[i, j+1]
        if i < self.shape[0]-1:
            yield Border.BOTTOM.value, self[i+1, j]
        if j > 0:
            yield Border.LEFT.value, self[i, j-1]


    def adjacent_empty_slots(self, i, j):
        for delta_i, delta_j in zip([1,-1,0,0], [0,0,1,-1]):
            if 0 <= i + delta_i < self.shape[0] and 0<= j + delta_j < self.shape[1] \
                and isinstance(self[i + delta_i, j + delta_j], Slot):
                yield i + delta_i, j + delta_j


class Slot():
    def __init__(self, id):
        self._id = id
        self.available = False
    
    @property
    def id(self):
        return self._id

    @property
    def picture(self):
            return 0



class Piece():
    def __init__(self, picture, id=None):
        picture = np.array(picture)
        assert picture.ndim == 3, "The picture must be 3-dimensional, i.e. of shape (n,n,3)"
        assert picture.shape[2] == 3, "Each pixel of the picture must have 3 color values"
        assert picture.shape[0] == picture.shape[1], "The image must not be rectangular but squared in shape"

        self._id = id
        self.picture = picture
        self._is_placed = False

    @property
    def id(self):
        return self._id

    @property
    def is_placed(self):
        return self._is_placed

    @property
    def size(self):
        return len(self.picture)

    def get_border(self, border):
        return self.picture[border.slice]

    def rgb_to_lab(self):
        return Piece(color.rgb2lab(self.picture),self.id)

    def lab_to_rgb(self):
        return Piece(color.lab2rgb(self.picture),self.id)

    def _clean(self):
        self._is_placed = False

    def __eq__(self, other):
        if isinstance(other, Piece):
            return np.allclose(self.picture, other.picture)
        return False

    def copy(self):
        return Piece(self.picture.copy())


class Puzzle():
    def __init__(self,img,initializer=patch(100),seed=0):
        '''@patch_size : The size of the pieces wanted by the user
           | Ex : I want to cut an image into pieces of size 100x100 pixels"
        '''

        self.img=img
        self.seed = seed
        self.bag_of_pieces = []
        self.initializer=initializer
        initializer(self,shuffled=True)



    @property
    def ground_truth(self):
        '''return the ground truth arrangement '''
        original=copy(self)
        original.initializer(original,shuffled=False)
        return original


    @property
    def shape(self):
        '''Return the shape of the board of the Puzzle'''
        assert self.board, "Puzzle board is empty."
        return self.board.shape

    @property
    def pieces_placed(self):
        return filter(lambda piece: piece.is_placed, self.bag_of_pieces)

    @property
    def pieces_remaining(self):
        return [piece for piece in self.bag_of_pieces if not piece.is_placed]
        #≡ return filter(lambda piece: not piece.is_placed, self.bag_of_pieces)

    def change_structure(self,new_initializer):
        self.initializer=new_initializer
        self.bag_of_pieces=[]
        new_initializer(self)

    def shuffle(self):
        '''Took all pieces from the board to the bag of pieces, and shuffle it'''
        n_rows, n_columns = self.shape
        np.random.seed(self.seed)  # for reproducibility
        self.board = Board(n_rows, n_columns)
        np.random.shuffle(self.bag_of_pieces)
        self.new_ids={}

        for i,piece in enumerate(self.bag_of_pieces):
            piece._is_placed = False
            self.new_ids[piece.id] = i
            piece._id=i

    
    def place(self, piece, coords):
        """Places a piece at the given coordinates
            * set _is_placed to True
            * make the neighboring slots available
        """
        i, j = coords
        assert isinstance(piece, Piece), "must be an instance of Piece."
        assert isinstance(self.board[i, j], Slot), f"A piece is already placed at {coords}."
        assert not piece._is_placed, "This Piece has already been placed"
        
        self.board[i,j] = piece
        piece._is_placed = True
        piece.position = (i,j)
        for position, slot in self.board.neighbors(i, j):
            if isinstance(slot, Slot):
                slot.available = True


    def display(self, show_borders=True):
        assert self.board, "Puzzle board is empty"
        n_rows, n_columns = self.shape
        ps = self.patch_size
        vsize, hsize = n_rows * ps, n_columns * ps
        puzzle_plot = np.zeros([vsize, hsize, 3], dtype=int)
        for i in range(n_rows):
            for j in range(n_columns):
                puzzle_plot[i*ps:(i+1)*ps, j*ps:(j+1)*ps, :] = self.board[i,j].picture

        if show_borders:
            for i in range(n_rows):
                plt.axhline(i*ps-.5, c="w")
            for j in range(n_columns):
                plt.axvline(j*ps-.5, c="w")
        plt.xticks(np.arange(-.5, hsize+1, ps), np.arange(0, hsize+1, ps))
        plt.yticks(np.arange(-.5, vsize+1, ps), np.arange(0, vsize+1, ps))
    
        plt.imshow(puzzle_plot)
        # plt.show()

    def find_position(self,id):
        '''
        find the position of the piece with given id 
        @id: given id
        Return
        @(i,j): position of the piece with given id
        '''

        assert self.board, 'A board must be created'
        assert not(self.pieces_remaining), 'All the pieces must be placed to call this function'
        assert (self.new_ids[id] in [piece.id for piece in self.bag_of_pieces]), 'The id provided should correspond to the id of ' \
                                                                   'a Piece in the Puzzle !'
        n,m = self.shape

        for i in range(n):
            for j in range(m):
                if (self.board[i,j].id==id):
                    return (i,j)

    def clean(self):
        "clean the current puzzle | Restart the party"
        self.board = Board(*self.shape)
        for piece in self.bag_of_pieces:
            piece._clean()


    def __copy__(self):
        " copy the current puzzle "
        new_puzzle = Puzzle(self.img,self.initializer)
        new_puzzle.bag_of_pieces = copy(self.bag_of_pieces)
        new_puzzle.board = deepcopy(self.board)
        return new_puzzle
