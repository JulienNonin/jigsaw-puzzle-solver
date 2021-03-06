# Here, we propose to implement a very stupid solver which is solving the puzzle just by shuffling randomly the pieces.

def random_solver(puzzle,plotsteps=True):
    '''
    Solve a puzzle randomly
    @plotsteps: set up if it will plot the process step by step
    '''

    # Random solver
    np.random.shuffle(puzzle.bag_of_pieces)

    k = 0
    # Simulate solver step by step
    for i in range(puzzle.shape[0]):
        for j in range(puzzle.shape[1]):
            if isinstance(puzzle.board[i,j],Slot): ## If location empty
                puzzle.board[i,j] = puzzle.bag_of_pieces[k]
                #puzzle.bag_of_pieces = puzzle.bag_of_pieces[1:] If bag of pieces only contains non placed pieces

                k += 1
                if plotsteps == True : # Plot puzzle at step
                    puzzle.display()

    return