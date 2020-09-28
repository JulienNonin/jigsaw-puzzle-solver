import numpy as np
import matplotlib.pyplot as plt

from enum import Enum
from copy import copy, deepcopy
from skimage import io, color

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
    def __init__(self, n_rows, n_cols, patch_size):
        self._grid = [[Slot(patch_size) for j in range(n_cols)] for i in range(n_rows)]

    def __getitem__(self, coords):
        i, j = coords
        return self._grid[i][j]

    def __setitem__(self, coords, value):
        assert isinstance(value, Slot) or isinstance(value, Piece), (
            f"value is an instance of {type(value)} instead of Slot or Piece")
        i, j = coords
        self._grid[i][j] = value

    def __iter__(self):
        for i in range(self.shape[0]):
            for j in range(self.shape[1]):
                yield self._grid[i][j]

    @property
    def shape(self):
        return (len(self._grid), len(self._grid[0]))

    def neighbors(self, i, j):
        # top
        if i > 0:
            yield self[i-1, j]
        # right
        if j < self.shape[1]-1:
            yield self[i, j+1]
        # down
        if i < self.shape[0]-1:
            yield self[i+1, j]
        # left
        if j > 0:
            yield self[i, j-1]


class Slot():
    def __init__(self, patch_size):
        self.patch_size = patch_size

    @property
    def picture(self):
            return np.zeros((self.patch_size, self.patch_size, 3))



class Piece():
    def __init__(self, picture):
        picture = np.array(picture, dtype=int)
        assert picture.ndim == 3, "The picture must be 3-dimensional, i.e. of shape (n,n,3)"
        assert picture.shape[2] == 3, "Each pixel of the picture must have 3 color values"
        assert picture.shape[0] == picture.shape[1], "The image must not be rectangular but squared in shape"

        self.picture = picture

    @property
    def size(self):
        return len(self.picture)

    def get_border(self, border):
        return self.picture[border.slice]

    def rgb_to_lab(self):
        return color.rgb2lab(self.picture)

    def lab_to_rgb(self):
        return color.lab2rgb(self.picture)

    def diss(self,other,lab_space=False):
        '''Return the dissimilarities between the current Piece and the other for the four sides'''

        currentPiece=self.rgb_to_lab() if lab_space else self

        diss = {}
        for border in Border:
            diss[border] = np.sum(
                np.power(self.get_border(border) - other.get_border(border.opposite), 2)
            )
        return diss

    def __eq__(self, otherPiece):
        return np.allclose(self.picture,otherPiece.picture)




class Puzzle():
    def __init__(self, patch_size=100, seed=0):
        self.patch_size = patch_size
        self.seed = seed
        self.bag_of_pieces = []
        self.board = None

    @property
    def shape(self):
        '''Return the shape of the board of the Puzzle'''
        assert self.board, "Puzzle board is empty."
        return self.board.shape


    def create_from_img(self, img):
        '''Create the pieces from an img and put them in the board'''
        np.random.seed(self.seed)  # for reproducibility

        ## Crop the image for its size to be a multiple of the patch size
        height, width, _ = img.shape
        ps = self.patch_size
        n_rows, n_columns = height // ps, width // ps
        img_cropped = img[:n_rows * ps, :n_columns * ps]
    
        ## Populate the board
        self.board = Board(n_rows, n_columns, ps)
        for i in range(n_rows):
            for j in range(n_columns):
                self.board[i,j] = Piece(img_cropped[i*ps:(i+1)*ps, j*ps:(j+1)*ps])
        return self


    def shuffle(self):
        '''Took all pieces from the board to the bag of pieces, and shuffle it'''
        n_rows, n_colums = self.shape
        for i in range(n_rows):
            for j in range(n_colums):
                self.bag_of_pieces.append(self.board[i,j])
        self.board = Board(n_rows, n_colums, self.patch_size)
        np.random.shuffle(self.bag_of_pieces)


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
        plt.show()

    def set_CM(self):
        "set the compatibility matrix associated to our current puzzle"

        assert self.bag_of_pieces, "A puzzle should be created"

        CM=[]

        #function enabling to jump from dissimilarities into probabilities
        h = lambda x,sigma: np.round(np.exp(-x / (2 * (sigma ** 2))),2)

        for i,Piece in enumerate(self.bag_of_pieces):

            #We need to obtain the dissimilarities between the current
            #Piece and all the others Piece.
            f=lambda otherPiece: Piece.diss(otherPiece)
            g=lambda otherPiece: list(f(otherPiece).values())

            CM.append([f(otherPiece) for otherPiece in self.bag_of_pieces])

            # **Normalization of dissimilarities (suggested by the Cho Paper)**

            #We don't count the current piece for the normalization
            Values = list((map(g,filter(lambda x: x!=Piece,self.bag_of_pieces))))

            #Then, we need the two smallest dissimilarities so we can sort our list values to obtain them
            Values=np.sort(np.array(Values).reshape(-1))

            #kind of standard deviation - handling of the case where there are only two pieces
            try:
                sigma=Values[1]-Values[0]
            except:
                sigma=Values[0]

            #Normalization
            for diss in CM[-1]:
                for key in diss.keys():
                    diss[key]=h(diss[key],sigma)

            self.CM=np.array(CM)


    def __copy__(self):
        new_puzzle = Puzzle(self.patch_size)
        new_puzzle.bag_of_pieces = copy(self.bag_of_pieces)
        new_puzzle.board = deepcopy(self.board)
        return new_puzzle